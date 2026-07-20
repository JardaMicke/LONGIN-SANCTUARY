"""
Model Manager — handles listing, fetching, and switching LLM models in Ollama/exo.
Manages SFW ↔ NSFW model registry rules.
"""

from loguru import logger
import httpx

from config.settings import settings
from services.ollama_client import OllamaClient


class ModelManager:
    """Manages available models across the network cluster."""

    def __init__(self):
        self.primary_client = OllamaClient(settings.OLLAMA_PRIMARY_URL)

    async def list_available_models(self) -> list[dict]:
        """List all models currently installed on the primary node."""
        return await self.primary_client.list_models()

    async def list_network_models(self) -> list[dict]:
        """List models available across all nodes in the cluster (including exo)."""
        models = []
        
        # Primary local Ollama models
        local = await self.list_available_models()
        for m in local:
            m["node"] = settings.NODE_NAME
            models.append(m)

        # Secondary nodes
        for url in settings.OLLAMA_EXTRA_URLS:
            try:
                client = OllamaClient(url)
                remote = await client.list_models()
                for m in remote:
                    m["node"] = url
                    models.append(m)
            except Exception:
                pass
                
        return models

    async def pull_model(self, model_name: str, node_url: str | None = None) -> bool:
        """Trigger pulling a model from registry (Ollama/HF)."""
        target_url = node_url or settings.OLLAMA_PRIMARY_URL
        client = OllamaClient(target_url)
        
        logger.info(f"Triggering model pull for '{model_name}' on {target_url}")
        try:
            async for progress in client.pull_model(model_name):
                # We could log or stream progress to WS
                pass
            return True
        except Exception as e:
            logger.error(f"Failed to pull model '{model_name}': {e}")
            return False

    def get_allowed_model(self, model_name: str, is_nsfw_session: bool) -> str:
        """
        Ensures a requested model is permitted based on the safety context.
        If NSFW is requested but age gate not passed, falls back to SFW model.
        """
        # Simple safety rule mapping
        # If session is SFW, but model is explicit, fallback
        if not is_nsfw_session and "nsfw" in model_name.lower():
            logger.warning(f"SFW session requested NSFW model {model_name}. Falling back to default model.")
            return settings.DEFAULT_LLM_MODEL
            
        return model_name
