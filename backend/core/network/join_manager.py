"""
Join Manager — handles cluster join requests from new devices.
Full implementation in Phase 6.
"""

from uuid import UUID
import uuid
from loguru import logger

from models.network import JoinRequest


class JoinManager:
    """Manages incoming cluster join requests and auto-install flow."""

    _pending: dict[UUID, JoinRequest] = {}

    async def get_pending_requests(self) -> list[JoinRequest]:
        return [r for r in self._pending.values() if r.status == "pending"]

    async def receive_request(self, hostname: str, ip: str, hardware_info: dict) -> JoinRequest:
        """Called when a new device sends a join request."""
        request = JoinRequest(
            id=uuid.uuid4(),
            hostname=hostname,
            ip=ip,
            hardware_info=hardware_info,
        )
        self._pending[request.id] = request
        logger.info(f"📡 Join request from {hostname} ({ip})")
        # Phase 6: Push notification to UI via Redis pub/sub
        return request

    async def approve_join(
        self,
        request_id: UUID,
        install_path: str,
        install_comfyui: bool,
        install_ollama: bool,
    ) -> dict:
        """Approve join and trigger remote auto-install."""
        request = self._pending.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        request.status = "approved"
        logger.info(f"✅ Approved join from {request.hostname}")

        # Phase 6: Send install package to requesting device
        # - cluster_agent.py download URL
        # - install_path
        # - list of packages to install
        # - model sync configuration
        return {
            "status": "approved",
            "message": f"Auto-install initiated on {request.hostname}",
            "install_path": install_path,
        }

    async def reject_join(self, request_id: UUID):
        request = self._pending.get(request_id)
        if request:
            request.status = "rejected"
            logger.info(f"❌ Rejected join from {request.hostname}")
