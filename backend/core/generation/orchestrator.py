"""
Generation Orchestrator — routes generation jobs to ComfyUI.
Full implementation in Phase 4.
"""

import uuid
from uuid import UUID

from loguru import logger

from models.generation import (
    GenerationJob, TextToImageRequest,
    TextToVideoRequest, ImageToVideoRequest,
)


# In-memory job store (Phase 4: move to Redis)
_jobs: dict[UUID, GenerationJob] = {}


class GenerationOrchestrator:

    async def create_job(self, job_type: str, params: dict) -> GenerationJob:
        job = GenerationJob(
            id=uuid.uuid4(),
            type=job_type,
            status="queued",
            params=params,
        )
        _jobs[job.id] = job
        return job

    async def get_job(self, job_id: UUID) -> GenerationJob | None:
        return _jobs.get(job_id)

    async def cancel_job(self, job_id: UUID):
        job = _jobs.get(job_id)
        if job and job.status in ("queued", "running"):
            job.status = "cancelled"

    async def run_text_to_image(self, job_id: UUID, request: TextToImageRequest, db):
        """Phase 4: Send to ComfyUI, apply IP-Adapter if character_id set."""
        job = _jobs.get(job_id)
        if not job:
            return
        job.status = "running"
        job.progress = 0
        try:
            # TODO Phase 4: build ComfyUI workflow, send, poll progress
            logger.info(f"T2I job {job_id} started (Phase 4 TODO)")
            job.status = "done"
            job.progress = 100
        except Exception as e:
            job.status = "failed"
            job.error = str(e)

    async def run_text_to_video(self, job_id: UUID, request: TextToVideoRequest, db):
        """Phase 4: WanVideo / CogVideoX via ComfyUI."""
        job = _jobs.get(job_id)
        if not job:
            return
        job.status = "running"
        try:
            logger.info(f"T2V job {job_id} started (Phase 4 TODO)")
            job.status = "done"
        except Exception as e:
            job.status = "failed"
            job.error = str(e)

    async def run_image_to_video(self, job_id: UUID, request: ImageToVideoRequest, db):
        """Phase 4: SVD or FILM interpolation via ComfyUI."""
        job = _jobs.get(job_id)
        if not job:
            return
        job.status = "running"
        try:
            logger.info(f"I2V job {job_id} started (Phase 4 TODO)")
            job.status = "done"
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
