"""System / health routes."""
from fastapi import APIRouter
from config.settings import settings

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok", "node": settings.NODE_NAME, "version": "0.1.0"}

@router.get("/info")
async def info():
    return {
        "node_name": settings.NODE_NAME,
        "node_role": settings.NODE_ROLE,
        "nsfw_enabled": settings.NSFW_ENABLED,
        "cluster_discovery": settings.CLUSTER_DISCOVERY_ENABLED,
    }
