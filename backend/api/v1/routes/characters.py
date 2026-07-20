"""Character CRUD routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_session
from models.character import Character, CharacterCreate, CharacterUpdate, CharacterRead
from core.characters.character_manager import CharacterManager

router = APIRouter()



@router.get("/", response_model=list[CharacterRead])
async def list_characters(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """List all characters."""
    return await CharacterManager(db).list_all(skip=skip, limit=limit)


@router.post("/", response_model=CharacterRead, status_code=201)
async def create_character(
    data: CharacterCreate,
    db: AsyncSession = Depends(get_session),
):
    """Create a new character."""
    return await CharacterManager(db).create(data)


@router.get("/{character_id}", response_model=CharacterRead)
async def get_character(
    character_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """Get character by ID."""
    char = await CharacterManager(db).get(character_id)
    if not char:
        raise HTTPException(404, "Character not found")
    return char


@router.patch("/{character_id}", response_model=CharacterRead)
async def update_character(
    character_id: UUID,
    data: CharacterUpdate,
    db: AsyncSession = Depends(get_session),
):
    """Update character."""
    char = await CharacterManager(db).update(character_id, data)
    if not char:
        raise HTTPException(404, "Character not found")
    return char


@router.delete("/{character_id}", status_code=204)
async def delete_character(
    character_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """Delete character."""
    await CharacterManager(db).delete(character_id)


@router.post("/{character_id}/reference-images", status_code=202)
async def upload_reference_images(
    character_id: UUID,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_session),
):
    """Upload reference images for face embedding and LoRA training."""
    manager = CharacterManager(db)
    result = await manager.process_reference_images(character_id, files, background_tasks)
    return {"message": f"Processing {len(files)} images", "job_id": result}
