"""Chat routes — streaming SSE responses."""
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_session
from models.chat import ChatRequest, ChatMessage
from core.inference.llm_engine import LLMEngine
from core.memory.stm_manager import STMManager

router = APIRouter()


@router.post("/{character_id}/message")
async def send_message(
    character_id: UUID,
    request: ChatRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Send a message to a character and get a streaming response.
    Returns Server-Sent Events (SSE) stream.
    """
    engine = LLMEngine()
    stm = STMManager()

    async def stream_response():
        full_response = ""
        async for chunk in engine.stream_response(
            character_id=character_id,
            user_message=request.message,
            session_id=request.session_id,
            db=db,
        ):
            full_response += chunk
            yield f"data: {chunk}\n\n"

        # Save full response to STM after streaming
        await stm.add_message(
            character_id=character_id,
            session_id=request.session_id,
            role="assistant",
            content=full_response,
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
