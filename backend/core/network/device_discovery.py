"""
Network Discovery — mDNS-based cluster node discovery.
Full implementation in Phase 6.
"""

import asyncio
import socket
from typing import AsyncGenerator

import psutil
from loguru import logger

from config.settings import settings
from models.network import ClusterStatus, NodeInfo


class NetworkDiscovery:
    """Discovers Sanctuary nodes on the local network via mDNS / ping scan."""

    _nodes: dict[str, NodeInfo] = {}
    _running: bool = False

    async def start(self):
        """Start background discovery loop."""
        self._running = True
        asyncio.create_task(self._discovery_loop())
        logger.info("Network discovery started")

    async def stop(self):
        self._running = False

    async def _discovery_loop(self):
        """Periodically scan for nodes. Phase 6: replace with proper mDNS."""
        # Phase 6: Use zeroconf for proper mDNS discovery
        # For now: register self and known static IPs
        await self._register_self()

        # Static known nodes from config (to be replaced by mDNS)
        known_ips = ["192.168.1.15", "192.168.1.18"]
        for ip in known_ips:
            await self._probe_node(ip)

        while self._running:
            await asyncio.sleep(30)
            for ip in list(self._nodes.keys()):
                await self._probe_node(ip)

    async def _register_self(self):
        """Register this node."""
        hostname = socket.gethostname()
        local_ip = self._get_local_ip()
        gpu_info = self._get_gpu_info()

        node = NodeInfo(
            id=hostname,
            name=settings.NODE_NAME,
            ip=local_ip,
            role=settings.NODE_ROLE,
            status="online",
            gpu_name=gpu_info.get("name"),
            gpu_vram_total_mb=gpu_info.get("vram_total_mb", 0),
            gpu_vram_free_mb=gpu_info.get("vram_free_mb", 0),
            cpu_cores=psutil.cpu_count(logical=False) or 0,
            ram_total_mb=int(psutil.virtual_memory().total / 1024 / 1024),
            ram_free_mb=int(psutil.virtual_memory().available / 1024 / 1024),
            services=["ollama", "comfyui"],
        )
        self._nodes[local_ip] = node

    async def _probe_node(self, ip: str):
        """Check if a Sanctuary node is online at given IP."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"http://{ip}:8000/health")
                if resp.status_code == 200:
                    data = resp.json()
                    if ip not in self._nodes:
                        self._nodes[ip] = NodeInfo(
                            id=data.get("node", ip),
                            name=data.get("node", ip),
                            ip=ip,
                            role="worker",
                            status="online",
                        )
                    else:
                        self._nodes[ip].status = "online"
        except Exception:
            if ip in self._nodes:
                self._nodes[ip].status = "offline"

    def _get_local_ip(self) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def _get_gpu_info(self) -> dict:
        """Get GPU info. Phase 6: use nvidia-smi / nvml properly."""
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(", ")
                return {
                    "name": parts[0],
                    "vram_total_mb": int(parts[1]),
                    "vram_free_mb": int(parts[2]),
                }
        except Exception:
            pass
        return {}

    async def get_nodes(self) -> list[NodeInfo]:
        return list(self._nodes.values())

    async def get_cluster_status(self) -> ClusterStatus:
        nodes = list(self._nodes.values())
        total_vram = sum(n.gpu_vram_total_mb for n in nodes)
        free_vram = sum(n.gpu_vram_free_mb for n in nodes)
        return ClusterStatus(
            master_node=settings.NODE_NAME,
            total_vram_mb=total_vram,
            free_vram_mb=free_vram,
            nodes=nodes,
            active_jobs=0,  # Phase 6: track from job queue
            pending_join_requests=0,
        )

    async def stream_events(self) -> AsyncGenerator[dict, None]:
        """Phase 6: Stream real-time cluster events via WebSocket."""
        # TODO Phase 6: event bus (Redis pub/sub)
        while True:
            await asyncio.sleep(5)
            status = await self.get_cluster_status()
            yield {"type": "cluster_status", "data": status.model_dump()}
