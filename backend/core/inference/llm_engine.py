"""
LLM Engine — streaming inference via Ollama / exo.
Full implementation in Phase 5.
"""

from typing import AsyncGenerator
from uuid import UUID

import httpx
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from core.characters.character_manager import CharacterManager
from core.memory.stm_manager import STMManager


class LLMEngine:
    """Routes LLM requests to Ollama (local) or exo (distributed)."""

    def _build_system_prompt(
        self,
        character,
        recent_messages: list[dict],
        relevant_memories: list[str] = None
    ) -> str:
        """Assemble full system prompt from character persona and relevant memories."""
        persona = character.persona or {}
        name = character.name
        backstory = persona.get("backstory", "")
        personality = persona.get("personality", "")
        speech_style = persona.get("speech_style", "")
        override = character.system_prompt_override or ""

        base = (
            f"You are {name}. "
            f"{backstory} "
            f"Personality: {personality}. "
            f"Speech style: {speech_style}. "
        )
        if override:
            base += f"\n\n{override}"

        if relevant_memories:
            base += "\n\nRelevant context from your memory:\n"
            for mem in relevant_memories:
                base += f"- {mem}\n"

        return base.strip()

    async def stream_response(
        self,
        character_id: UUID,
        user_message: str,
        session_id: str,
        db: AsyncSession,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens from LLM for a character."""
        # 1. Load character
        char_manager = CharacterManager(db)
        character = await char_manager.get(character_id)
        if not character:
            yield f"[Error: Character {character_id} not found]"
            return

        model = character.llm_model or settings.DEFAULT_LLM_MODEL
        system_prompt = self._build_system_prompt(character, [])

        # 2. Load conversation history
        stm = STMManager()
        history = await stm.get_context_window(
            character_id=character_id,
            session_id=session_id,
            model_name=model,
            system_prompt=system_prompt,
        )

        # 3. Retrieve relevant memories from RAG (Vector DB)
        relevant_memories = []
        try:
            from core.memory.rag_engine import RAGEngine
            rag = RAGEngine()
            relevant_memories = await rag.search_relevant_memories(
                character_id=character_id,
                query=user_message,
                top_k=settings.RAG_TOP_K
            )
        except Exception as e:
            logger.warning(f"Failed to fetch memories from RAG: {e}")

        # 4. Save user message to STM
        await stm.add_message(character_id, session_id, "user", user_message)

        # 5. Build messages list for Ollama
        system_prompt = self._build_system_prompt(character, history, relevant_memories)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        # 5. Stream from LM Studio or Ollama
        if model.startswith("lmstudio/"):
            real_model = model.replace("lmstudio/", "")
            lmstudio_url = settings.LMSTUDIO_PRIMARY_URL
            payload = {
                "model": real_model,
                "messages": messages,
                "stream": True,
                "temperature": settings.DEFAULT_TEMPERATURE,
                "max_tokens": settings.DEFAULT_MAX_TOKENS,
            }
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream(
                    "POST",
                    f"{lmstudio_url}/v1/chat/completions",
                    json=payload,
                ) as response:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                import json
                                chunk_data = json.loads(data_str)
                                chunk = chunk_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if chunk:
                                    yield chunk
                            except Exception as e:
                                logger.warning(f"LM Studio stream parse error: {e}")
            return

        ollama_url = settings.OLLAMA_PRIMARY_URL
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": settings.DEFAULT_TEMPERATURE,
                "num_ctx": settings.DEFAULT_CONTEXT_LENGTH,
            },
        }

        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"{ollama_url}/api/chat",
                json=payload,
            ) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        import json
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            yield chunk
                        if data.get("done"):
                            break
                    except Exception as e:
                        logger.warning(f"LLM stream parse error: {e}")
