"""
Quality Checker — validates generated images/video frames for:
1. Face consistency (FaceNet/InsightFace cosine similarity)
2. Anatomical pose score (placeholder for Phase 4 ControlNet validation)
3. CLIP prompt adherence score

Used in the triple-check pipeline:
  Generate 3x → score each → pick best → if all fail threshold → regenerate
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import UUID

import numpy as np
from loguru import logger
from PIL import Image

from config.settings import settings
from core.characters.face_embedding import FaceEmbeddingPipeline


@dataclass
class QualityScore:
    face_similarity: float      # 0-1 (cosine sim vs reference embedding)
    pose_score: float           # 0-1 (anatomical plausibility)
    clip_score: float           # 0-1 (prompt adherence)
    overall: float              # weighted average

    @property
    def passes_threshold(self) -> bool:
        return self.face_similarity >= settings.FACE_CONSISTENCY_THRESHOLD

    def __str__(self) -> str:
        return (
            f"Face:{self.face_similarity:.3f} "
            f"Pose:{self.pose_score:.3f} "
            f"CLIP:{self.clip_score:.3f} "
            f"Overall:{self.overall:.3f}"
        )


class QualityChecker:
    """
    Validates generated images against character consistency requirements.
    Priority order (as per spec):
      1. Face consistency
      2. Anatomical / pose accuracy
      3. Prompt adherence (CLIP)
      4. Speed (last priority — we regenerate up to 3x)
    """

    def __init__(self):
        self.face_pipeline = FaceEmbeddingPipeline()
        self._clip_model = None

    def _get_clip(self):
        """Lazy-load CLIP for prompt adherence scoring."""
        if self._clip_model is None:
            try:
                import torch
                import clip
                device = "cuda" if torch.cuda.is_available() else "cpu"
                self._clip_model = clip.load("ViT-B/32", device=device)
                logger.info(f"CLIP loaded on {device}")
            except ImportError:
                logger.warning("clip package not installed, CLIP scoring disabled")
        return self._clip_model

    def score_image(
        self,
        image: Image.Image,
        reference_embedding: Optional[np.ndarray] = None,
        prompt: Optional[str] = None,
    ) -> QualityScore:
        """
        Score a single generated image.
        - reference_embedding: character's face embedding (None if no character)
        - prompt: text prompt used for generation (for CLIP score)
        """
        # 1. Face consistency
        face_score = 0.5  # Neutral default if no character reference
        if reference_embedding is not None:
            face_score = self.face_pipeline.check_consistency_score(
                reference_embedding, image
            )
            logger.debug(f"Face consistency: {face_score:.3f}")

        # 2. Pose / anatomical score
        # Phase 4: integrate ControlNet OpenPose estimation
        pose_score = self._estimate_pose_score(image)

        # 3. CLIP prompt adherence
        clip_score = 0.5  # Default if CLIP not available
        if prompt:
            clip_score = self._clip_score(image, prompt)

        # Weighted overall (face consistency has highest weight per spec)
        overall = (
            face_score * 0.55 +
            pose_score * 0.25 +
            clip_score * 0.20
        )

        return QualityScore(
            face_similarity=face_score,
            pose_score=pose_score,
            clip_score=clip_score,
            overall=overall,
        )

    def pick_best(
        self,
        images: list[Image.Image],
        reference_embedding: Optional[np.ndarray] = None,
        prompt: Optional[str] = None,
    ) -> tuple[Image.Image, QualityScore]:
        """
        Score multiple generated images and return the best one.
        Implements the triple-check pipeline.
        """
        if not images:
            raise ValueError("No images to evaluate")

        scored = []
        for i, img in enumerate(images):
            score = self.score_image(img, reference_embedding, prompt)
            scored.append((img, score))
            logger.info(f"Image {i+1}/{len(images)}: {score}")

        # Sort by face consistency first (priority 1), then overall
        scored.sort(key=lambda x: (x[1].face_similarity, x[1].overall), reverse=True)
        best_img, best_score = scored[0]
        logger.info(f"Best image selected: {best_score}")
        return best_img, best_score

    def _estimate_pose_score(self, image: Image.Image) -> float:
        """
        Basic anatomical plausibility check.
        Phase 4: replace with proper OpenPose estimation.
        Currently: check image has reasonable proportions and content.
        """
        w, h = image.size
        # Very basic: reject extreme aspect ratios
        ratio = w / h
        if ratio < 0.3 or ratio > 3.0:
            return 0.3
        return 0.7  # Placeholder until Phase 4

    def _clip_score(self, image: Image.Image, prompt: str) -> float:
        """Compute CLIP similarity between image and prompt."""
        try:
            import torch
            clip_pack = self._get_clip()
            if clip_pack is None:
                return 0.5

            model, preprocess = clip_pack
            device = next(model.parameters()).device

            image_input = preprocess(image).unsqueeze(0).to(device)
            text_input = torch.tensor(
                __import__("clip").tokenize([prompt[:77]])
            ).to(device)

            with torch.no_grad():
                image_features = model.encode_image(image_input)
                text_features = model.encode_text(text_input)
                image_features /= image_features.norm(dim=-1, keepdim=True)
                text_features /= text_features.norm(dim=-1, keepdim=True)
                similarity = (image_features @ text_features.T).item()

            # Normalize from [-1,1] to [0,1]
            return (similarity + 1) / 2
        except Exception as e:
            logger.warning(f"CLIP scoring failed: {e}")
            return 0.5
