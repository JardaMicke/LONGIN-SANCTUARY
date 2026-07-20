"""Chat routes — streaming SSE responses."""
from uuid import UUID
from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_session, AsyncSessionLocal
from models.chat import ChatRequest, ChatMessage
from core.inference.llm_engine import LLMEngine
from core.memory.stm_manager import STMManager
from core.memory.ltm_manager import LTMManager

router = APIRouter()


async def _run_memory_consolidation(character_id: UUID, session_id: str, model_name: str):
    """Background helper to run memory consolidation with a clean DB session."""
    async with AsyncSessionLocal() as db:
        ltm = LTMManager(db)
        await ltm.consolidate_memory_if_needed(character_id, session_id, model_name)


@router.post("/{character_id}/message")
async def send_message(
    character_id: UUID,
    chat_request: ChatRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """
    Send a message to a character and get a streaming response.
    Returns Server-Sent Events (SSE) stream.
    """
    # Enforce NSFW age gate check
    from core.content.age_check import AgeVerifier
    await AgeVerifier.verify_nsfw_access(character_id, request, db)

    engine = LLMEngine()
    stm = STMManager()

    async def stream_response():
        full_response = ""
        # Fetch the character's active model for consolidation
        from core.characters.character_manager import CharacterManager
        from config.settings import settings
        char = await CharacterManager(db).get(character_id)
        model_name = char.llm_model if char and char.llm_model else settings.DEFAULT_LLM_MODEL

        async for chunk in engine.stream_response(
            character_id=character_id,
            user_message=chat_request.message,
            session_id=chat_request.session_id,
            db=db,
        ):
            full_response += chunk
            yield f"data: {chunk}\n\n"

        # Save full response to STM after streaming
        await stm.add_message(
            character_id=character_id,
            session_id=chat_request.session_id,
            role="assistant",
            content=full_response,
        )

        # Consolidate memory in background if threshold is met
        background_tasks.add_task(
            _run_memory_consolidation,
            character_id=character_id,
            session_id=chat_request.session_id,
            model_name=model_name
        )

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{character_id}/history")
async def get_history(
    character_id: UUID,
    session_id: str,
    limit: int = 50,
):
    """Get conversation history for a character session."""
    stm = STMManager()
    return await stm.get_history(character_id, session_id, limit=limit)


@router.delete("/{character_id}/history")
async def clear_history(
    character_id: UUID,
    session_id: str,
):
    """Clear conversation history."""
    stm = STMManager()
    await stm.clear(character_id, session_id)
    return {"message": "History cleared"}
