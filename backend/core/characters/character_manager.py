"""
Character Manager — CRUD + embedding pipeline.
Full implementation in Phase 2.
"""

from uuid import UUID
from fastapi import UploadFile, BackgroundTasks
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
        self,
        character_id: UUID,
        files: list[UploadFile],
        background_tasks: BackgroundTasks,
    ) -> str:
        """
        Phase 2: Save uploaded reference images, extract face embeddings in background,
        and update the character's visual profile. Triggers LoRA training if 20+ images.
        """
        import os
        from pathlib import Path
        import uuid
        from config.settings import settings
        from core.generation.orchestrator import GenerationOrchestrator

        # 1. Create upload directory
        upload_dir = Path(settings.OUTPUT_PATH) / "uploads" / str(character_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # 2. Save files to disk immediately (so they don't get disposed)
        image_paths = []
        for file in files:
            if not file.filename:
                continue
            # sanitize filename
            safe_name = os.path.basename(file.filename)
            dest_path = upload_dir / safe_name
            with open(dest_path, "wb") as buffer:
                buffer.write(await file.read())
            image_paths.append(str(dest_path))

        if not image_paths:
            raise ValueError("No valid files uploaded")

        # 3. Create a generation job to track progress
        orchestrator = GenerationOrchestrator()
        job = await orchestrator.create_job(
            job_type="lora_train" if len(image_paths) >= 20 else "text_to_image",
            params={"character_id": str(character_id), "image_count": len(image_paths)},
        )

        # 4. Enqueue background task
        background_tasks.add_task(
            _bg_process_reference_images,
            character_id=character_id,
            image_paths=image_paths,
            job_id=job.id,
        )

        return str(job.id)


async def _bg_process_reference_images(
    character_id: UUID,
    image_paths: list[str],
    job_id: UUID,
):
    """Background task to extract face embedding and update character DB."""
    from loguru import logger
    from PIL import Image
    from config.database import AsyncSessionLocal
    from core.characters.face_embedding import FaceEmbeddingPipeline
    from core.generation.orchestrator import GenerationOrchestrator
    from core.characters.character_manager import CharacterManager

    orchestrator = GenerationOrchestrator()
    job = await orchestrator.get_job(job_id)
    if job:
        job.status = "running"
        job.progress = 10

    try:
        # Load PIL Images
        images = []
        for path in image_paths:
            try:
                img = Image.open(path)
                img.verify()
                # Reopen since verify() closes the file pointer
                img = Image.open(path)
                images.append(img)
            except Exception as e:
                logger.warning(f"Invalid reference image {path}: {e}")

        if not images:
            raise ValueError("No valid images could be loaded")

        if job:
            job.progress = 30

        import asyncio
        # Extract face embeddings in a background thread to prevent blocking the event loop
        pipeline = FaceEmbeddingPipeline()
        avg_embedding = await asyncio.to_thread(pipeline.extract_from_multiple, images)

        if avg_embedding is None:
            raise ValueError("No faces detected in any uploaded images")

        if job:
            job.progress = 60

        # Save embedding in a background thread
        emb_path = await asyncio.to_thread(pipeline.save_embedding, character_id, avg_embedding)

        if job:
            job.progress = 80

        # Update character in database
        async with AsyncSessionLocal() as db:
            manager = CharacterManager(db)
            character = await manager.get(character_id)
            if character:
                visual = dict(character.visual or {})
                visual["reference_images"] = image_paths
                visual["face_embedding_path"] = emb_path
                character.visual = visual
                db.add(character)
                await db.commit()
                logger.info(f"Updated character {character_id} face embedding path: {emb_path}")

        if job:
            job.status = "done"
            job.progress = 100
            job.result_path = emb_path

    except Exception as e:
        logger.exception(f"Error processing reference images for character {character_id}")
        if job:
            job.status = "failed"
            job.error = str(e)
