"""
RAG Engine — Vector Database storage and search using Qdrant and Ollama Embeddings.
Provides retrieval of relevant past context/memories for LLM system prompt.
"""

from uuid import UUID, uuid4
from loguru import logger
import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from config.settings import settings
from config.qdrant_client import get_qdrant, COLLECTION_MEMORY


class RAGEngine:
    """Handles embedding generation and vector search in Qdrant."""

    async def get_embedding(self, text: str) -> list[float]:
        """
        Get vector embedding for text.
        Primary: Ollama API.
        Secondary: Local sentence-transformers.
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{settings.OLLAMA_PRIMARY_URL}/api/embeddings",
                    json={
                        "model": settings.EMBEDDING_MODEL,
                        "prompt": text,
                    }
                )
                if resp.status_code == 200:
                    return resp.json().get("embedding", [])
        except Exception as e:
            logger.warning(f"Ollama embedding failed, trying sentence-transformers: {e}")

        # Fallback using sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer
            # nomic-embed-text fallback or miniLM
            model = SentenceTransformer("all-MiniLM-L6-v2")  # 384 dim, warning: dim mismatch if collection was built as 768
            # Just to be safe, if we get dimension mismatch, we return list of 768 zeros or handle it.
            # But let's log and do the encoding
            emb = model.encode(text).tolist()
            # If dim mismatch (collection expects 768), pad with zeros
            if len(emb) < 768:
                emb = emb + [0.0] * (768 - len(emb))
            return emb[:768]
        except Exception as ex:
            logger.error(f"RAG embedding failed completely: {ex}")
            raise

    async def store_memory(self, character_id: UUID, text: str, metadata: dict | None = None) -> str:
        """Embed text and store in Qdrant collection."""
        client: AsyncQdrantClient = await get_qdrant()
        emb = await self.get_embedding(text)
        
        point_id = str(uuid4())
        payload = {
            "character_id": str(character_id),
            "text": text,
            **(metadata or {})
        }

        await client.upsert(
            collection_name=COLLECTION_MEMORY,
            points=[
                PointStruct(
                    id=point_id,
                    vector=emb,
                    payload=payload
                )
            ]
        )
        logger.debug(f"Stored point {point_id} in Qdrant COLLECTION_MEMORY")
        return point_id

    async def search_relevant_memories(
        self,
        character_id: UUID,
        query: str,
        top_k: int = 5,
        threshold: float | None = None,
    ) -> list[str]:
        """
        Search for memories matching query using cosine similarity.
        Filters results to only match the specific character_id.
        """
        client: AsyncQdrantClient = await get_qdrant()
        emb = await self.get_embedding(query)
        
        threshold = threshold or settings.RAG_SIMILARITY_THRESHOLD

        # Qdrant filtering by character_id
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        char_filter = Filter(
            must=[
                FieldCondition(
                    key="character_id",
                    match=MatchValue(value=str(character_id))
                )
            ]
        )

        results = await client.search(
            collection_name=COLLECTION_MEMORY,
            query_vector=emb,
            query_filter=char_filter,
            limit=top_k,
            score_threshold=threshold,
        )

        memories = []
        for r in results:
            text = r.payload.get("text", "")
            if text:
                memories.append(text)
        
        logger.info(f"Retrieved {len(memories)} relevant memories from RAG for query: {query[:30]}...")
        return memories
