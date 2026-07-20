"""
Generation Orchestrator — manages and executes AI generation jobs.
Loads workflow templates, populates parameters, routes to the best available
ComfyUI server, and runs the triple-check quality control pipeline.
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from loguru import logger
from PIL import Image

from config.settings import settings
from services.comfyui_client import ComfyUIRouter, ComfyUIClient
from core.generation.quality_checker import QualityChecker
from core.characters.character_manager import CharacterManager
from core.characters.face_embedding import FaceEmbeddingPipeline
from models.generation import (
    GenerationJob, TextToImageRequest,
    TextToVideoRequest, ImageToVideoRequest,
)

# In-memory job store (Phase 4: move to Redis / database)
_jobs: dict[UUID, GenerationJob] = {}


class GenerationOrchestrator:

    def __init__(self):
        self.router = ComfyUIRouter()
        self.quality_checker = QualityChecker()

    async def create_job(self, job_type: str, params: dict) -> GenerationJob:
        job = GenerationJob(
            id=uuid.uuid4(),
            type=job_type,
            status="queued",
            params=params,
            created_at=datetime.utcnow(),
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
        """
        Execute Text-to-Image generation.
        Applies IP-Adapter and/or ControlNet if a character is specified.
        Implements triple-check quality validation.
        """
        job = _jobs.get(job_id)
        if not job:
            return

        job.status = "running"
        job.progress = 5

        try:
            # 1. Fetch best ComfyUI server
            server_url = await self.router.get_best_server()
            job.node = server_url
            comfy_client = ComfyUIClient(server_url)

            # 2. Load workflow template
            workflow_path = Path("comfyui_workflows/text_to_image_character.json")
            if not workflow_path.exists():
                raise FileNotFoundError(f"Workflow template not found at {workflow_path}")
            
            with open(workflow_path, "r", encoding="utf-8") as f:
                workflow = json.load(f)

            # 3. Populate workflow placeholders
            workflow["2"]["inputs"]["text"] = request.prompt
            workflow["3"]["inputs"]["text"] = request.negative_prompt
            workflow["4"]["inputs"]["width"] = request.width
            workflow["4"]["inputs"]["height"] = request.height
            workflow["10"]["inputs"]["steps"] = request.steps
            workflow["10"]["inputs"]["cfg"] = request.cfg

            if request.seed != -1:
                workflow["10"]["inputs"]["seed"] = request.seed
            else:
                import random
                workflow["10"]["inputs"]["seed"] = random.randint(1, 1000000000)

            # Retrieve character visual context (IP-Adapter face embeddings & LoRA)
            ref_embedding = None
            if request.character_id:
                char_manager = CharacterManager(db)
                character = await char_manager.get(request.character_id)
                if character and character.visual:
                    visual = character.visual
                    
                    # Setup IP-Adapter if face embedding is available
                    face_emb_path = visual.get("face_embedding_path")
                    if face_emb_path:
                        face_pipeline = FaceEmbeddingPipeline()
                        ref_embedding = face_pipeline.load_embedding(face_emb_path)
                        # We can upload the embedding or reference photo to ComfyUI input folder
                        # For simulation, we assume IPAdapter takes a reference image path or loaded embedding.
                        # Since ComfyUI expects reference images in its 'input' directory:
                        ref_images = visual.get("reference_images", [])
                        if ref_images:
                            # Use the first reference image
                            ref_img_name = os.path.basename(ref_images[0])
                            # Copy reference image to ComfyUI input directory if running locally
                            # or pass it as a file/placeholder
                            workflow["5"]["inputs"]["image"] = ref_img_name
                    
                    # Setup LoRA if available
                    lora_path = visual.get("lora_path")
                    if lora_path:
                        workflow["9"]["inputs"]["lora_name"] = os.path.basename(lora_path)
                    else:
                        # If no LoRA, bypass LoRA loader node by linking input model directly
                        workflow["10"]["inputs"]["model"] = workflow["9"]["inputs"]["model"]

            # If no character consistency, bypass IP-Adapter node and link directly
            if not request.character_id or not ref_embedding:
                workflow["9"]["inputs"]["model"] = workflow["1"]["outputs"]["MODEL"]
                # Bypass ControlNet as well if no pose reference
                workflow["10"]["inputs"]["positive"] = workflow["2"]["outputs"]["CONDITIONING"]
                workflow["10"]["inputs"]["negative"] = workflow["3"]["outputs"]["CONDITIONING"]

            job.progress = 20

            # 4. Submit prompt
            prompt_id = await comfy_client.queue_prompt(workflow)
            
            # 5. Poll for completion
            async for event in comfy_client.wait_for_completion(prompt_id):
                if event["type"] == "progress":
                    job.progress = 20 + int(event["value"] * 0.6)  # Scale to 20-80%
                elif event["type"] == "error":
                    raise RuntimeError(event["message"])
                elif event["type"] == "done":
                    output_files = event["output"]["files"]
                    
                    # 6. Download generated images
                    downloaded_images = []
                    output_dir = Path(settings.OUTPUT_PATH) / "generations" / str(job_id)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    for idx, file_info in enumerate(output_files):
                        file_data = await comfy_client.download_output(
                            filename=file_info["filename"],
                            subfolder=file_info["subfolder"],
                            output_type=file_info["type"],
                        )
                        dest_path = output_dir / f"frame_{idx}.png"
                        with open(dest_path, "wb") as f:
                            f.write(file_data)
                        
                        # Load as PIL Image for scoring
                        img = Image.open(dest_path)
                        downloaded_images.append((img, str(dest_path)))

                    job.progress = 85

                    # 7. Quality control triple-check validation
                    if downloaded_images:
                        pil_images = [x[0] for x in downloaded_images]
                        best_img, best_score = self.quality_checker.pick_best(
                            pil_images,
                            reference_embedding=ref_embedding,
                            prompt=request.prompt
                        )
                        
                        # Find the path of the best image
                        best_idx = pil_images.index(best_img)
                        best_path = downloaded_images[best_idx][1]
                        
                        job.status = "done"
                        job.progress = 100
                        job.result_path = best_path
                        job.completed_at = datetime.utcnow()
                        logger.info(f"T2I job {job_id} completed successfully. Best score: {best_score}")
                    else:
                        raise ValueError("No images generated by ComfyUI")
                    break

        except Exception as e:
            logger.exception(f"T2I job {job_id} failed")
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.utcnow()

    async def run_text_to_video(self, job_id: UUID, request: TextToVideoRequest, db):
        """
        Execute Text-to-Video generation using WanVideo 2.1 or CogVideoX.
        """
        job = _jobs.get(job_id)
        if not job:
            return

        job.status = "running"
        job.progress = 10

        try:
            # 1. Fetch best ComfyUI server
            server_url = await self.router.get_best_server()
            job.node = server_url
            comfy_client = ComfyUIClient(server_url)

            # 2. Load workflow template
            workflow_path = Path("comfyui_workflows/text_to_video_character.json")
            if not workflow_path.exists():
                raise FileNotFoundError(f"Workflow template not found at {workflow_path}")
            
            with open(workflow_path, "r", encoding="utf-8") as f:
                workflow = json.load(f)

            # 3. Populate prompt & settings
            workflow["2"]["inputs"]["positive_prompt"] = request.prompt
            workflow["3"]["inputs"]["width"] = request.width
            workflow["3"]["inputs"]["height"] = request.height
            workflow["3"]["inputs"]["num_frames"] = request.frames
            workflow["5"]["inputs"]["fps"] = request.fps

            if request.seed != -1:
                workflow["5"]["inputs"]["seed"] = request.seed
            else:
                import random
                workflow["5"]["inputs"]["seed"] = random.randint(1, 1000000000)

            # Setup character face image on first frame if character is provided
            if request.character_id:
                char_manager = CharacterManager(db)
                character = await char_manager.get(request.character_id)
                if character and character.visual:
                    ref_images = character.visual.get("reference_images", [])
                    if ref_images:
                        workflow["4"]["inputs"]["image"] = os.path.basename(ref_images[0])
            else:
                # Bypass first frame face lock node
                workflow["5"]["inputs"]["model"] = workflow["1"]["outputs"]["MODEL"]

            job.progress = 20

            # 4. Submit prompt
            prompt_id = await comfy_client.queue_prompt(workflow)

            # 5. Poll for completion
            async for event in comfy_client.wait_for_completion(prompt_id):
                if event["type"] == "progress":
                    job.progress = 20 + int(event["value"] * 0.7)
                elif event["type"] == "error":
                    raise RuntimeError(event["message"])
                elif event["type"] == "done":
                    output_files = event["output"]["files"]
                    if not output_files:
                        raise ValueError("No video generated by ComfyUI")
                    
                    # 6. Download video file
                    video_info = output_files[0]
                    file_data = await comfy_client.download_output(
                        filename=video_info["filename"],
                        subfolder=video_info["subfolder"],
                        output_type=video_info["type"],
                    )
                    
                    output_dir = Path(settings.OUTPUT_PATH) / "generations" / str(job_id)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    dest_path = output_dir / f"video.mp4"
                    with open(dest_path, "wb") as f:
                        f.write(file_data)

                    job.status = "done"
                    job.progress = 100
                    job.result_path = str(dest_path)
                    job.completed_at = datetime.utcnow()
                    logger.info(f"T2V job {job_id} completed successfully: {dest_path}")
                    break

        except Exception as e:
            logger.exception(f"T2V job {job_id} failed")
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.utcnow()

    async def run_image_to_video(self, job_id: UUID, request: ImageToVideoRequest, db):
        """
        Execute Image-to-Video generation using SVD or FILM interpolation.
        Supports:
        - Image to video (SVD)
        - Start frame + End frame to video (FILM interpolation)
        """
        job = _jobs.get(job_id)
        if not job:
            return

        job.status = "running"
        job.progress = 10

        try:
            # 1. Fetch best ComfyUI server
            server_url = await self.router.get_best_server()
            job.node = server_url
            comfy_client = ComfyUIClient(server_url)

            # Determine workflow (FILM interpolation vs SVD img2vid)
            is_interpolation = bool(request.end_image_path)
            
            if is_interpolation:
                workflow_path = Path("comfyui_workflows/start_end_to_video.json")
            else:
                workflow_path = Path("comfyui_workflows/image_to_video.json")

            if not workflow_path.exists():
                raise FileNotFoundError(f"Workflow template not found at {workflow_path}")
            
            with open(workflow_path, "r", encoding="utf-8") as f:
                workflow = json.load(f)

            # Populate images
            # Note: reference images should be uploaded/copied to ComfyUI input folder
            if is_interpolation:
                workflow["1"]["inputs"]["image"] = os.path.basename(request.start_image_path)
                workflow["2"]["inputs"]["image"] = os.path.basename(request.end_image_path)
                workflow["4"]["inputs"]["frame_rate"] = request.fps
            else:
                workflow["2"]["inputs"]["image"] = os.path.basename(request.start_image_path)
                workflow["3"]["inputs"]["video_frames"] = request.frames
                workflow["3"]["inputs"]["fps"] = request.fps

            job.progress = 25

            # Submit prompt
            prompt_id = await comfy_client.queue_prompt(workflow)

            # Poll for completion
            async for event in comfy_client.wait_for_completion(prompt_id):
                if event["type"] == "progress":
                    job.progress = 25 + int(event["value"] * 0.7)
                elif event["type"] == "error":
                    raise RuntimeError(event["message"])
                elif event["type"] == "done":
                    output_files = event["output"]["files"]
                    if not output_files:
                        raise ValueError("No video generated by ComfyUI")
                    
                    # Download video file
                    video_info = output_files[0]
                    file_data = await comfy_client.download_output(
                        filename=video_info["filename"],
                        subfolder=video_info["subfolder"],
                        output_type=video_info["type"],
                    )
                    
                    output_dir = Path(settings.OUTPUT_PATH) / "generations" / str(job_id)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    dest_path = output_dir / f"video.mp4"
                    with open(dest_path, "wb") as f:
                        f.write(file_data)

                    job.status = "done"
                    job.progress = 100
                    job.result_path = str(dest_path)
                    job.completed_at = datetime.utcnow()
                    logger.info(f"I2V job {job_id} completed successfully: {dest_path}")
                    break

        except Exception as e:
            logger.exception(f"I2V job {job_id} failed")
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.utcnow()
