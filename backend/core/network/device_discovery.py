"""
Network Discovery — mDNS / Zeroconf discovery of Sanctuary cluster nodes.
Falls back to direct network IP probing if multicast is blocked on the router/OS.
"""

import asyncio
import socket
from typing import AsyncGenerator
import psutil
from loguru import logger

from config.settings import settings
from models.network import ClusterStatus, NodeInfo

# Service type for LONGIN SANCTUARY
SERVICE_TYPE = "_sanctuary._tcp.local."


class SanctuaryServiceListener:
    """Listener called by Zeroconf browser when services are discovered/removed."""

    def __init__(self, discovery_instance):
        self.discovery = discovery_instance

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            asyncio.create_task(self.discovery.register_discovered_service(info))

    def remove_service(self, zc, type_, name):
        asyncio.create_task(self.discovery.unregister_discovered_service(name))

    def update_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            asyncio.create_task(self.discovery.register_discovered_service(info))


class NetworkDiscovery:
    """Manages mDNS service registration and discovery of cluster nodes."""

    _nodes: dict[str, NodeInfo] = {}
    _running: bool = False
    _zeroconf = None
    _browser = None
    _service_info = None

    async def start(self):
        """Start mDNS registration and browsing."""
        self._running = True
        
        # 1. Register self
        await self._register_self()

        # 2. Start Zeroconf
        try:
            from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser
            self._zeroconf = Zeroconf()
            
            # Register this node as a service
            local_ip = self._get_local_ip()
            hostname = socket.gethostname()
            
            self._service_info = ServiceInfo(
                type_=SERVICE_TYPE,
                name=f"{settings.NODE_NAME}.{SERVICE_TYPE}",
                addresses=[socket.inet_aton(local_ip)],
                port=settings.API_PORT,
                properties={
                    "role": settings.NODE_ROLE,
                    "node_name": settings.NODE_NAME,
                    "hostname": hostname
                }
            )
            self._zeroconf.register_service(self._service_info)
            
            # Start browsing for other Sanctuary nodes
            listener = SanctuaryServiceListener(self)
            self._browser = ServiceBrowser(self._zeroconf, SERVICE_TYPE, listener)
            logger.info(f"mDNS registered service: {settings.NODE_NAME}.{SERVICE_TYPE}")
        except Exception as e:
            logger.warning(f"Zeroconf mDNS failed to initialize, falling back to static IP scanning: {e}")

        # 3. Start background monitoring & fallback scan loop
        asyncio.create_task(self._discovery_loop())

    async def stop(self):
        self._running = False
        if self._zeroconf:
            try:
                self._zeroconf.unregister_service(self._service_info)
                self._zeroconf.close()
            except Exception:
                pass

    async def register_discovered_service(self, info):
        """Called when Zeroconf detects a node."""
        try:
            role = info.properties.get(b"role", b"worker").decode("utf-8")
            node_name = info.properties.get(b"node_name", b"Unknown").decode("utf-8")
            hostname = info.properties.get(b"hostname", b"").decode("utf-8")
            
            # Extract IP address
            addresses = info.parsed_addresses()
            if not addresses:
                return
            ip = addresses[0]

            if ip == self._get_local_ip():
                return  # Skip self

            # Probe the node to load full specifications
            await self._probe_node(ip)
            logger.info(f"Discovered cluster node via mDNS: {node_name} at {ip}")
        except Exception as e:
            logger.warning(f"Failed to process discovered service info: {e}")

    async def unregister_discovered_service(self, name):
        """Called when a service goes offline."""
        node_name = name.split(".")[0]
        for ip, node in list(self._nodes.items()):
            if node.name == node_name:
                node.status = "offline"
                logger.info(f"Node {node_name} went offline")

    async def _discovery_loop(self):
        """Periodically scan known static IPs as fallback and refresh metrics."""
        while self._running:
            # Always refresh local node metrics
            await self._register_self()

            # Static fallback ping scan in case mDNS/Multicast is blocked
            known_ips = ["192.168.1.15", "192.168.1.18"]
            for ip in known_ips:
                if ip != self._get_local_ip():
                    await self._probe_node(ip)

            await asyncio.sleep(20)

    async def _register_self(self):
        """Get and store local node statistics."""
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
            services=["ollama", "comfyui"] if settings.NODE_ROLE in ("master", "both") else ["ollama"],
        )
        self._nodes[local_ip] = node

    async def _probe_node(self, ip: str):
        """Probe remote node's REST API health endpoint."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"http://{ip}:{settings.API_PORT}/api/v1/system/info")
                if resp.status_code == 200:
                    data = resp.json()
                    node_name = data.get("node_name", ip)
                    role = data.get("node_role", "worker")
                    
                    # Fetch system stats if possible
                    stat_resp = await client.get(f"http://{ip}:{settings.API_PORT}/api/v1/settings/")
                    
                    gpu_name = None
                    vram_total = 0
                    vram_free = 0
                    
                    # Merge information
                    if ip not in self._nodes:
                        self._nodes[ip] = NodeInfo(
                            id=node_name,
                            name=node_name,
                            ip=ip,
                            role=role,
                            status="online",
                            gpu_name=gpu_name,
                            gpu_vram_total_mb=vram_total,
                            gpu_vram_free_mb=vram_free,
                        )
                    else:
                        self._nodes[ip].status = "online"
                        self._nodes[ip].role = role
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
        total_vram = sum(n.gpu_vram_total_mb for n in nodes if n.status == "online")
        free_vram = sum(n.gpu_vram_free_mb for n in nodes if n.status == "online")
        
        # Count pending join requests
        from core.network.join_manager import JoinManager
        jm = JoinManager()
        pending = len(await jm.get_pending_requests())

        return ClusterStatus(
            master_node=settings.NODE_NAME,
            total_vram_mb=total_vram,
            free_vram_mb=free_vram,
            nodes=nodes,
            active_jobs=0,
            pending_join_requests=pending,
        )

    async def stream_events(self) -> AsyncGenerator[dict, None]:
        while True:
            await asyncio.sleep(5)
            status = await self.get_cluster_status()
            yield {"type": "cluster_status", "data": status.model_dump()}
