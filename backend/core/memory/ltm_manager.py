"""
LTM Manager — Long-Term Memory (PostgreSQL facts and session summaries).
Consolidates STM messages into high-level summaries and factual knowledge.
"""

from datetime import datetime
from uuid import UUID, uuid4
from loguru import logger
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from config.settings import settings
from models.memory import FactualMemory, SessionSummary
from core.context.tokenizer_manager import TokenizerManager


class LTMManager:
    """Manages factual and summarized long-term memory stored in PostgreSQL."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_fact(self, character_id: UUID, category: str, fact: str) -> FactualMemory:
        """Add a factual memory for a character."""
        factual = FactualMemory(
            id=uuid4(),
            character_id=character_id,
            category=category,
            fact=fact,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(factual)
        await self.db.flush()
        logger.info(f"Factual memory added for character {character_id}: {fact[:50]}...")
        return factual

    async def get_facts(self, character_id: UUID, category: str | None = None) -> list[FactualMemory]:
        """Retrieve facts for a character, optionally filtered by category."""
        query = select(FactualMemory).where(FactualMemory.character_id == character_id)
        if category:
            query = query.where(FactualMemory.category == category)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def save_summary(self, character_id: UUID, session_id: str, summary: str) -> SessionSummary:
        """Save a new session summary to the database."""
        sess_summary = SessionSummary(
            id=uuid4(),
            character_id=character_id,
            session_id=session_id,
            summary=summary,
            created_at=datetime.utcnow(),
        )
        self.db.add(sess_summary)
        await self.db.flush()
        logger.info(f"Session summary saved for {character_id} / {session_id}")
        return sess_summary

    async def get_summaries(self, character_id: UUID, session_id: str) -> list[SessionSummary]:
        """Get all summaries for a specific character session."""
        query = select(SessionSummary).where(
            SessionSummary.character_id == character_id,
            SessionSummary.session_id == session_id
        ).order_by(SessionSummary.created_at.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def consolidate_memory_if_needed(self, character_id: UUID, session_id: str, model_name: str):
        """
        Check if STM token count exceeds LTM_SUMMARIZE_THRESHOLD.
        If yes, trigger background memory consolidation:
        1. Extract oldest block of messages.
        2. Call LLM to summarize them.
        3. Save summary to LTM (PostgreSQL) and Vector DB (Qdrant).
        4. Trim those messages from STM (Redis).
        """
        from core.memory.stm_manager import STMManager
        stm = STMManager()
        history = await stm.get_history(character_id, session_id, limit=200)
        
        # Calculate total tokens
        total_text = " ".join([m.get("content", "") for m in history])
        total_tokens = TokenizerManager.count_tokens(total_text, model_name)

        if total_tokens < settings.LTM_SUMMARIZE_THRESHOLD:
            return

        logger.info(f"Memory consolidation triggered for {character_id}: STM is {total_tokens} tokens")

        # Take the oldest 50% of the messages to summarize
        consolidate_count = len(history) // 2
        if consolidate_count < 4:
            return

        to_summarize = history[:consolidate_count]

        # Generate summary
        summary = await self._generate_summary_via_llm(to_summarize, model_name)
        if not summary:
            logger.error("Failed to generate memory summary, skipping consolidation")
            return

        # 1. Save summary to Postgres
        await self.save_summary(character_id, session_id, summary)

        # 2. Save summary to Vector DB (RAG)
        from core.memory.rag_engine import RAGEngine
        rag = RAGEngine()
        # We pass metadata so we can filter by character_id
        await rag.store_memory(
            character_id=character_id,
            text=f"Summary of past events: {summary}",
            metadata={"session_id": session_id, "type": "summary"}
        )

        # 3. Try to extract facts from the block and store them too
        facts = await self._extract_facts_via_llm(to_summarize, model_name)
        for fact in facts:
            await self.add_fact(character_id, "general", fact)
            await rag.store_memory(
                character_id=character_id,
                text=f"Fact: {fact}",
                metadata={"session_id": session_id, "type": "fact"}
            )

        # 4. Remove summarized messages from Redis (using Redis ltrim)
        import redis.asyncio as aioredis
        from config.redis_client import get_redis
        redis_client: aioredis.Redis = await get_redis()
        key = stm._key(character_id, session_id)
        # Keep everything after consolidated count
        await redis_client.ltrim(key, consolidate_count, -1)
        logger.info(f"Consolidated and trimmed {consolidate_count} messages from Redis STM")

    async def _generate_summary_via_llm(self, messages: list[dict], model_name: str) -> str | None:
        """Call Ollama/exo to summarize conversation block."""
        conv_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
        prompt = (
            "Summarize the following conversation block between the User and the AI character. "
            "Be extremely concise, capture key events, facts, decisions, and relationship changes. "
            "Write the summary in the third person.\n\n"
            f"Conversation:\n{conv_text}\n\n"
            "Summary:"
        )

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{settings.OLLAMA_PRIMARY_URL}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3}
                    }
                )
                if resp.status_code == 200:
                    return resp.json().get("response", "").strip()
        except Exception as e:
            logger.warning(f"Error calling LLM for summarization: {e}")
        return None

    async def _extract_facts_via_llm(self, messages: list[dict], model_name: str) -> list[str]:
        """Call LLM to extract clean list of key factual bullet points."""
        conv_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
        prompt = (
            "Analyze the conversation below and extract new key factual details about the User, "
            "the Character, or the World that are likely to be important for future interactions. "
            "Examples: User's name, user's job, user's hobbies, character's secrets, world state. "
            "Only return bullet points starting with '- '. Do not return conversational filler. "
            "If no key facts are found, return nothing.\n\n"
            f"Conversation:\n{conv_text}\n\n"
            "Facts:"
        )

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{settings.OLLAMA_PRIMARY_URL}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1}
                    }
                )
                if resp.status_code == 200:
                    response_text = resp.json().get("response", "")
                    facts = []
                    for line in response_text.strip().split("\n"):
                        clean_line = line.strip().lstrip("- ").strip()
                        if clean_line:
                            facts.append(clean_line)
                    return facts
        except Exception as e:
            logger.warning(f"Error calling LLM for fact extraction: {e}")
        return []
