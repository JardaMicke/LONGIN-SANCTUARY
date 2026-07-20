"""Network / cluster management routes."""
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from core.network.device_discovery import NetworkDiscovery
from core.network.join_manager import JoinManager
from models.network import ClusterStatus, JoinRequest, JoinApproval, NodeInfo

router = APIRouter()


@router.get("/status", response_model=ClusterStatus)
async def cluster_status():
    """Get current cluster status — all discovered nodes."""
    discovery = NetworkDiscovery()
    return await discovery.get_cluster_status()


@router.get("/nodes", response_model=list[NodeInfo])
async def list_nodes():
    """List all known cluster nodes."""
    discovery = NetworkDiscovery()
    return await discovery.get_nodes()


@router.get("/join-requests", response_model=list[JoinRequest])
async def list_join_requests():
    """List pending cluster join requests from new devices."""
    manager = JoinManager()
    return await manager.get_pending_requests()


@router.post("/join-requests/{request_id}/approve")
async def approve_join(request_id: UUID, approval: JoinApproval):
    """
    Approve a cluster join request.
    Triggers auto-install on the requesting device.
    """
    manager = JoinManager()
    return await manager.approve_join(
        request_id=request_id,
        install_path=approval.install_path,
        install_comfyui=approval.install_comfyui,
        install_ollama=approval.install_ollama,
    )


@router.post("/join-requests/{request_id}/reject", status_code=204)
async def reject_join(request_id: UUID):
    """Reject a cluster join request."""
    manager = JoinManager()
    await manager.reject_join(request_id)


@router.websocket("/ws")
async def cluster_ws(websocket: WebSocket):
    """
    WebSocket for real-time cluster updates:
    - Node online/offline events
    - Join request notifications
    - GPU/VRAM utilization updates
    - Generation job progress
    """
    await websocket.accept()
    discovery = NetworkDiscovery()

    try:
        async for event in discovery.stream_events():
            await websocket.send_json(event)
    except WebSocketDisconnect:
        logger.info("Cluster WS client disconnected")
    except Exception as e:
        logger.error(f"Cluster WS error: {e}")
