"""
STM Manager — Short-Term Memory using Redis.
Full implementation in Phase 3.
"""

import json
from datetime import datetime
from uuid import UUID

import redis.asyncio as aioredis

from config.redis_client import get_redis
from config.settings import settings


class STMManager:
    """Manages short-term conversation memory per character/session in Redis."""

    KEY_PREFIX = "stm"
    MAX_MESSAGES = 200  # Hard cap before LTM summarization

    def _key(self, character_id: UUID, session_id: str) -> str:
        return f"{self.KEY_PREFIX}:{character_id}:{session_id}"

    async def add_message(
        self,
        character_id: UUID,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """Append message to conversation history in Redis."""
        redis: aioredis.Redis = await get_redis()
        key = self._key(character_id, session_id)
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await redis.rpush(key, json.dumps(message))
        await redis.ltrim(key, -self.MAX_MESSAGES, -1)
        await redis.expire(key, 86400 * 7)  # 7 days TTL

    async def get_history(
        self,
        character_id: UUID,
        session_id: str,
        limit: int = 50,
    ) -> list[dict]:
        """Get last N messages from Redis."""
        redis: aioredis.Redis = await get_redis()
        key = self._key(character_id, session_id)
        raw = await redis.lrange(key, -limit, -1)
        return [json.loads(m) for m in raw]

    async def get_context_window(
        self,
        character_id: UUID,
        session_id: str,
        max_tokens: int | None = None,
        model_name: str = "llama3.1",
        system_prompt: str = "",
    ) -> list[dict]:
        """Get messages that fit within the token budget using TokenizerManager."""
        from core.context.tokenizer_manager import TokenizerManager
        max_tokens = max_tokens or settings.STM_MAX_TOKENS
        messages = await self.get_history(character_id, session_id, limit=self.MAX_MESSAGES)
        return TokenizerManager.trim_history(
            messages=messages,
            max_tokens=max_tokens,
            model_name=model_name,
            system_prompt=system_prompt,
        )

    async def clear(self, character_id: UUID, session_id: str) -> None:
        redis: aioredis.Redis = await get_redis()
        await redis.delete(self._key(character_id, session_id))
