"""Generation routes — T2I, T2V, I2V, etc."""
from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_session
from models.generation import (
    TextToImageRequest, TextToVideoRequest,
    ImageToVideoRequest, GenerationJob,
)
from core.generation.orchestrator import GenerationOrchestrator

router = APIRouter()


@router.post("/text-to-image", response_model=GenerationJob, status_code=202)
async def text_to_image(
    request: TextToImageRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
):
    """Generate image from text prompt, with optional character consistency."""
    orchestrator = GenerationOrchestrator()
    job = await orchestrator.create_job("text_to_image", request.model_dump())
    background_tasks.add_task(orchestrator.run_text_to_image, job.id, request, db)
    return job


@router.post("/text-to-video", response_model=GenerationJob, status_code=202)
async def text_to_video(
    request: TextToVideoRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
):
    """Generate video from text prompt."""
    orchestrator = GenerationOrchestrator()
    job = await orchestrator.create_job("text_to_video", request.model_dump())
    background_tasks.add_task(orchestrator.run_text_to_video, job.id, request, db)
    return job


@router.post("/image-to-video", response_model=GenerationJob, status_code=202)
async def image_to_video(
    request: ImageToVideoRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
):
    """Generate video from start (and optionally end) image."""
    orchestrator = GenerationOrchestrator()
    job = await orchestrator.create_job("image_to_video", request.model_dump())
    background_tasks.add_task(orchestrator.run_image_to_video, job.id, request, db)
    return job


@router.get("/jobs/{job_id}", response_model=GenerationJob)
async def get_job_status(job_id: UUID):
    """Get generation job status and result."""
    orchestrator = GenerationOrchestrator()
    return await orchestrator.get_job(job_id)


@router.delete("/jobs/{job_id}", status_code=204)
async def cancel_job(job_id: UUID):
    """Cancel a pending or running generation job."""
    orchestrator = GenerationOrchestrator()
    await orchestrator.cancel_job(job_id)
