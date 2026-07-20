"""Scenarios routes."""
from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_session
from models.scenario import Scenario, ScenarioCreate, ScenarioRead
from models.chat import ChatRequest
from core.scenarios.scenario_manager import ScenarioManager

router = APIRouter()


@router.get("/", response_model=list[ScenarioRead])
async def list_scenarios(db: AsyncSession = Depends(get_session)):
    return await ScenarioManager(db).list_all()


@router.post("/", response_model=ScenarioRead, status_code=201)
async def create_scenario(data: ScenarioCreate, db: AsyncSession = Depends(get_session)):
    return await ScenarioManager(db).create(data)


@router.get("/{scenario_id}", response_model=ScenarioRead)
async def get_scenario(scenario_id: UUID, db: AsyncSession = Depends(get_session)):
    return await ScenarioManager(db).get(scenario_id)


@router.post("/{scenario_id}/start")
async def start_scenario(scenario_id: UUID, db: AsyncSession = Depends(get_session)):
    """Start a scenario session — initializes all character contexts."""
    return await ScenarioManager(db).start(scenario_id)


@router.post("/{scenario_id}/message")
async def send_scenario_message(
    scenario_id: UUID,
    request: ChatRequest,
    db: AsyncSession = Depends(get_session),
):
    """Send a message to a scenario and get a multi-character streaming response."""
    from core.scenarios.roleplay_engine import RoleplayEngine
    import json
    
    rp_engine = RoleplayEngine()

    async def stream_rp():
        async for event in rp_engine.run_roleplay_step(
            scenario_id=scenario_id,
            session_id=request.session_id,
            user_message=request.message,
            db=db,
        ):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_rp(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
