"""LM Studio HTTP API client."""
import httpx
from loguru import logger


class LMStudioClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def list_models(self) -> list[dict]:
        """List available models from this LM Studio instance."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/v1/models")
                if resp.status_code != 200:
                    return []
                data = resp.json()
                models = []
                for item in data.get("data", []):
                    model_id = item.get("id")
                    models.append({
                        "name": f"lmstudio/{model_id}",
                        "model": model_id,
                        "provider": "lmstudio",
                        "size": 0,
                        "details": {
                            "format": "gguf",
                            "family": "lmstudio",
                            "parameter_size": "unknown",
                            "quantization_level": "unknown"
                        }
                    })
                return models
        except Exception as e:
            logger.warning(f"LM Studio list_models failed ({self.base_url}): {e}")
            return []

    async def is_healthy(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{self.base_url}/v1/models")
                return resp.status_code == 200
        except Exception:
            return False

    async def load_model(self, model_name: str) -> bool:
        """Load a model by triggering a dummy completion request."""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": "hello"}],
                        "max_tokens": 1
                    }
                )
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"LM Studio load_model failed ({self.base_url}): {e}")
            return False
