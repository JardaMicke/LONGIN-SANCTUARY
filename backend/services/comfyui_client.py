"""
ComfyUI API Client — submits workflows and polls for results.

Supports:
- Single ComfyUI server (primary)
- Multiple servers for load balancing
- WebSocket progress tracking
- Automatic retry on failure
"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import AsyncGenerator, Optional

import httpx
import websockets
from loguru import logger

from config.settings import settings


class ComfyUIClient:
    """Async client for ComfyUI REST + WebSocket API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client_id = str(uuid.uuid4())

    # ── Job submission ───────────────────────────────────────

    async def queue_prompt(self, workflow: dict) -> str:
        """
        Submit a workflow to ComfyUI queue.
        Returns prompt_id for tracking.
        """
        payload = {
            "prompt": workflow,
            "client_id": self.client_id,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/prompt",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            prompt_id = data["prompt_id"]
            logger.info(f"ComfyUI job queued: {prompt_id}")
            return prompt_id

    async def get_history(self, prompt_id: str) -> dict:
        """Get execution history for a prompt."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/history/{prompt_id}")
            resp.raise_for_status()
            return resp.json()

    async def wait_for_completion(
        self,
        prompt_id: str,
        timeout: int = 3600,
    ) -> dict:
        """
        Wait for a job to complete via WebSocket progress events.
        Returns output data when done.
        """
        ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws?clientId={self.client_id}"

        try:
            async with websockets.connect(ws_url) as ws:
                async for message in ws:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "progress":
                        value = data["data"]["value"]
                        max_val = data["data"]["max"]
                        pct = int(value / max_val * 100)
                        logger.debug(f"ComfyUI progress: {pct}%")
                        yield {"type": "progress", "value": pct}

                    elif msg_type == "executing":
                        node = data["data"].get("node")
                        if node is None:
                            # Execution complete
                            history = await self.get_history(prompt_id)
                            output = self._extract_output(history, prompt_id)
                            yield {"type": "done", "output": output}
                            return

                    elif msg_type == "execution_error":
                        error = data["data"].get("exception_message", "Unknown error")
                        logger.error(f"ComfyUI error: {error}")
                        yield {"type": "error", "message": error}
                        return

        except Exception as e:
            logger.error(f"ComfyUI WebSocket error: {e}")
            # Fallback: poll HTTP history
            yield await self._poll_history(prompt_id, timeout)

    async def _poll_history(self, prompt_id: str, timeout: int) -> dict:
        """Fallback polling when WebSocket fails."""
        elapsed = 0
        while elapsed < timeout:
            await asyncio.sleep(5)
            elapsed += 5
            history = await self.get_history(prompt_id)
            if prompt_id in history:
                output = self._extract_output(history, prompt_id)
                if output:
                    return {"type": "done", "output": output}
        return {"type": "error", "message": "Timeout waiting for ComfyUI"}

    def _extract_output(self, history: dict, prompt_id: str) -> dict:
        """Extract output file paths from history."""
        result = history.get(prompt_id, {})
        outputs = result.get("outputs", {})
        files = []
        for node_output in outputs.values():
            for key in ["images", "videos", "gifs"]:
                for item in node_output.get(key, []):
                    files.append({
                        "filename": item["filename"],
                        "subfolder": item.get("subfolder", ""),
                        "type": item.get("type", "output"),
                        "url": f"{self.base_url}/view?filename={item['filename']}&subfolder={item.get('subfolder', '')}&type={item.get('type', 'output')}",
                    })
        return {"files": files}

    async def download_output(self, filename: str, subfolder: str = "", output_type: str = "output") -> bytes:
        """Download generated file from ComfyUI."""
        params = {"filename": filename, "subfolder": subfolder, "type": output_type}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(f"{self.base_url}/view", params=params)
            resp.raise_for_status()
            return resp.content

    async def is_healthy(self) -> bool:
        """Check if ComfyUI server is running."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/system_stats")
                return resp.status_code == 200
        except Exception:
            return False

    async def get_system_stats(self) -> dict:
        """Get GPU memory, queue size, etc."""
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{self.base_url}/system_stats")
            return resp.json()


class ComfyUIRouter:
    """
    Routes generation jobs to the best available ComfyUI server.
    Considers: VRAM availability, queue length, server health.
    """

    def __init__(self):
        self.servers = [settings.COMFYUI_PRIMARY_URL] + settings.COMFYUI_EXTRA_URLS

    async def get_best_server(self, required_vram_gb: float = 0) -> str:
        """Return URL of the best available ComfyUI server."""
        candidates = []
        for url in self.servers:
            client = ComfyUIClient(url)
            if await client.is_healthy():
                try:
                    stats = await client.get_system_stats()
                    vram_free = stats.get("system", {}).get("vram_free", 0)
                    queue_size = stats.get("queue", {}).get("queue_running", 0)
                    candidates.append((url, vram_free, queue_size))
                except Exception:
                    candidates.append((url, 0, 999))

        if not candidates:
            raise RuntimeError("No ComfyUI servers available")

        # Sort by: enough VRAM first, then smallest queue
        candidates.sort(key=lambda x: (-x[1], x[2]))
        best_url = candidates[0][0]
        logger.info(f"Routing to ComfyUI server: {best_url}")
        return best_url
