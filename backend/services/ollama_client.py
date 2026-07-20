"""Ollama HTTP API client."""
import httpx
from loguru import logger


class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def list_models(self) -> list[dict]:
        """List available models from this Ollama instance."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                return resp.json().get("models", [])
        except Exception as e:
            logger.warning(f"Ollama list_models failed ({self.base_url}): {e}")
            return []

    async def pull_model(self, model_name: str):
        """Pull a model from Ollama registry."""
        async with httpx.AsyncClient(timeout=3600) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json={"name": model_name, "stream": True},
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        yield line

    async def is_healthy(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{self.base_url}/")
                return resp.status_code == 200
        except Exception:
            return False
