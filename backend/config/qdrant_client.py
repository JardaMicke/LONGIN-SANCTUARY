"""Qdrant vector DB client (singleton)."""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from config.settings import settings

_client: AsyncQdrantClient | None = None

# Collection names
COLLECTION_MEMORY = "character_memory"
COLLECTION_SCENARIOS = "scenario_context"

# Embedding dimension (nomic-embed-text = 768, all-MiniLM = 384)
EMBEDDING_DIM = 768


async def get_qdrant() -> AsyncQdrantClient:
    """FastAPI dependency — returns shared Qdrant client."""
    global _client
    if _client is None:
        _client = AsyncQdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY or None,
        )
        await _ensure_collections(_client)
    return _client


async def _ensure_collections(client: AsyncQdrantClient):
    """Create required collections if they don't exist."""
    existing = {c.name for c in (await client.get_collections()).collections}

    for name in [COLLECTION_MEMORY, COLLECTION_SCENARIOS]:
        if name not in existing:
            await client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
            )
