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


from fastapi import HTTPException, status
from models.network import ModelLoadRequest
from services.ollama_client import OllamaClient
from services.lmstudio_client import LMStudioClient

@router.get("/nodes/{node_id}/models")
async def get_node_models(node_id: str, service: str):
    """Get available models for a specific service on a specific node."""
    discovery = NetworkDiscovery()
    nodes = await discovery.get_nodes()
    node = next((n for n in nodes if n.id == node_id), None)
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
        
    if service not in node.services:
        raise HTTPException(status_code=400, detail=f"Service {service} not active on node {node_id}")
        
    if service == "ollama":
        client = OllamaClient(f"http://{node.ip}:11434")
        models = await client.list_models()
        return [{"name": m.get("name"), "details": m.get("details", {})} for m in models]
        
    elif service == "lmstudio":
        client = LMStudioClient(f"http://{node.ip}:1234")
        models = await client.list_models()
        return models
        
    raise HTTPException(status_code=400, detail="Unsupported service")


@router.post("/nodes/{node_id}/models/load")
async def load_node_model(node_id: str, payload: ModelLoadRequest):
    """Load a model into memory on a specific node's service."""
    discovery = NetworkDiscovery()
    nodes = await discovery.get_nodes()
    node = next((n for n in nodes if n.id == node_id), None)
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
        
    if payload.service not in node.services:
        raise HTTPException(status_code=400, detail=f"Service {payload.service} not active on node {node_id}")
        
    success = False
    if payload.service == "ollama":
        client = OllamaClient(f"http://{node.ip}:11434")
        success = await client.load_model(payload.model)
    elif payload.service == "lmstudio":
        # LMStudio models from our list_models return "lmstudio/model-name", but the API expects "model-name"
        model_name = payload.model.replace("lmstudio/", "") if payload.model.startswith("lmstudio/") else payload.model
        client = LMStudioClient(f"http://{node.ip}:1234")
        success = await client.load_model(model_name)
    else:
        raise HTTPException(status_code=400, detail="Unsupported service")
        
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to load model {payload.model} on {payload.service}")
        
    return {"status": "success", "message": f"Model {payload.model} loaded successfully"}
