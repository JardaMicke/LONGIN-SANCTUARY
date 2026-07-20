"""Scenarios routes."""
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_session
from models.scenario import Scenario, ScenarioCreate, ScenarioRead
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
