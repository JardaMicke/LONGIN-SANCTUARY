"""
Character Manager — CRUD + embedding pipeline.
Full implementation in Phase 2.
"""

from uuid import UUID
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from models.character import Character, CharacterCreate, CharacterUpdate


class CharacterManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self, skip: int = 0, limit: int = 50) -> list[Character]:
        result = await self.db.execute(
            select(Character).where(Character.is_active == True).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get(self, character_id: UUID) -> Character | None:
        result = await self.db.execute(
            select(Character).where(Character.id == character_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: CharacterCreate) -> Character:
        character = Character(**data.model_dump())
        self.db.add(character)
        await self.db.flush()
        await self.db.refresh(character)
        return character

    async def update(self, character_id: UUID, data: CharacterUpdate) -> Character | None:
        character = await self.get(character_id)
        if not character:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(character, key, value)
        await self.db.flush()
        await self.db.refresh(character)
        return character

    async def delete(self, character_id: UUID):
        character = await self.get(character_id)
        if character:
            character.is_active = False  # Soft delete
            await self.db.flush()

    async def process_reference_images(
        self, character_id: UUID, files: list[UploadFile]
    ) -> str:
        """
        Phase 2: Process reference images for face embedding + LoRA prep.
        Returns job ID.
        """
        # TODO Phase 2: InsightFace embedding extraction
        # TODO Phase 2: IP-Adapter face embedding storage
        # TODO Phase 2: Trigger LoRA training if 20+ images
        raise NotImplementedError("Phase 2: reference image processing")
