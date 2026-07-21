"""Unified Settings routes — all components in one view."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_session
from config.settings import settings
from models.settings import (
    UnifiedSettings, LLMSettings, ImageSettings,
    VideoSettings, MemorySettings, NetworkSettings,
)
from services.ollama_client import OllamaClient

router = APIRouter()


@router.get("/", response_model=UnifiedSettings)
async def get_all_settings():
    """Get all settings — LLM, Image, Video, Memory, Network, ComfyUI."""
    return UnifiedSettings(
        llm=LLMSettings(
            default_model=settings.DEFAULT_LLM_MODEL,
            temperature=settings.DEFAULT_TEMPERATURE,
            max_tokens=settings.DEFAULT_MAX_TOKENS,
            context_length=settings.DEFAULT_CONTEXT_LENGTH,
            ollama_url=settings.OLLAMA_PRIMARY_URL,
            exo_enabled=settings.EXO_ENABLED,
            exo_url=settings.EXO_API_URL,
            lmstudio_enabled=settings.LMSTUDIO_ENABLED,
            lmstudio_url=settings.LMSTUDIO_PRIMARY_URL,
        ),
        image=ImageSettings(
            default_model=settings.DEFAULT_IMAGE_MODEL,
            steps=settings.DEFAULT_IMAGE_STEPS,
            cfg=settings.DEFAULT_IMAGE_CFG,
            width=settings.DEFAULT_IMAGE_WIDTH,
            height=settings.DEFAULT_IMAGE_HEIGHT,
            ip_adapter_strength=settings.IP_ADAPTER_STRENGTH,
            face_consistency_threshold=settings.FACE_CONSISTENCY_THRESHOLD,
        ),
        video=VideoSettings(
            default_model=settings.DEFAULT_VIDEO_MODEL,
            frames=settings.DEFAULT_VIDEO_FRAMES,
            fps=settings.DEFAULT_VIDEO_FPS,
            width=settings.DEFAULT_VIDEO_WIDTH,
            height=settings.DEFAULT_VIDEO_HEIGHT,
        ),
        memory=MemorySettings(
            stm_max_tokens=settings.STM_MAX_TOKENS,
            ltm_summarize_threshold=settings.LTM_SUMMARIZE_THRESHOLD,
            rag_top_k=settings.RAG_TOP_K,
            rag_similarity_threshold=settings.RAG_SIMILARITY_THRESHOLD,
            embedding_model=settings.EMBEDDING_MODEL,
        ),
        network=NetworkSettings(
            node_name=settings.NODE_NAME,
            node_role=settings.NODE_ROLE,
            cluster_discovery_enabled=settings.CLUSTER_DISCOVERY_ENABLED,
            nsfw_enabled=settings.NSFW_ENABLED,
            age_check_enabled=settings.AGE_CHECK_ENABLED,
            content_filter_level=settings.CONTENT_FILTER_LEVEL,
        ),
    )


@router.get("/models/available")
async def get_available_models():
    """List all LLM models available across all nodes."""
    from core.inference.model_manager import ModelManager
    manager = ModelManager()
    all_models = await manager.list_network_models()
    return {"models": all_models, "source": "cluster"}
