"""Scenario Manager skeleton."""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from models.scenario import Scenario, ScenarioCreate


class ScenarioManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> list[Scenario]:
        result = await self.db.execute(select(Scenario).where(Scenario.is_active == True))
        return result.scalars().all()

    async def get(self, scenario_id: UUID) -> Scenario | None:
        result = await self.db.execute(select(Scenario).where(Scenario.id == scenario_id))
        return result.scalar_one_or_none()

    async def create(self, data: ScenarioCreate) -> Scenario:
        scenario = Scenario(**data.model_dump())
        self.db.add(scenario)
        await self.db.flush()
        await self.db.refresh(scenario)
        return scenario

    async def start(self, scenario_id: UUID) -> dict:
        """Phase 5: Initialize all character contexts for scenario."""
        scenario = await self.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")
        # TODO Phase 5: Initialize STM for each character, inject scene context
        return {"scenario_id": str(scenario_id), "status": "started"}
