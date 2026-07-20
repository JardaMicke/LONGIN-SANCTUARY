"""
Face Embedding Pipeline — InsightFace + IP-Adapter FaceID.

Extracts face embeddings from reference images and stores them
for use in ComfyUI IP-Adapter FaceID nodes.

Phase 2 core: character visual consistency foundation.
"""

import io
import pickle
from pathlib import Path
from typing import Optional
from uuid import UUID

import numpy as np
from loguru import logger
from PIL import Image

from config.settings import settings


class FaceEmbeddingPipeline:
    """
    Extracts 512-dim face embeddings using InsightFace (buffalo_l model).
    Embeddings are stored as .pkl files and referenced in character.visual.
    """

    def __init__(self):
        self._app = None  # Lazy-loaded InsightFace app
        self._embed_dir = Path(settings.MODELS_PATH) / "face_embeddings"
        self._embed_dir.mkdir(parents=True, exist_ok=True)

    def _get_app(self):
        """Lazy-load InsightFace to avoid startup delay."""
        if self._app is None:
            try:
                import insightface
                from insightface.app import FaceAnalysis
                self._app = FaceAnalysis(
                    name="buffalo_l",
                    root=str(Path(settings.MODELS_PATH) / "insightface"),
                    providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
                )
                self._app.prepare(ctx_id=0, det_size=(640, 640))
                logger.info("InsightFace loaded: buffalo_l")
            except ImportError:
                logger.error("insightface not installed. Run: pip install insightface onnxruntime")
                raise
        return self._app

    def extract_from_image(self, image: Image.Image) -> Optional[np.ndarray]:
        """
        Extract face embedding from a PIL Image.
        Returns 512-dim numpy array or None if no face detected.
        """
        app = self._get_app()
        img_array = np.array(image.convert("RGB"))
        faces = app.get(img_array)

        if not faces:
            logger.warning("No face detected in image")
            return None

        # Use the largest face (highest bounding box area)
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        return face.normed_embedding  # 512-dim normalized embedding

    def extract_from_multiple(
        self, images: list[Image.Image]
    ) -> Optional[np.ndarray]:
        """
        Extract face embeddings from multiple images and average them.
        This produces a more robust embedding than a single image.
        Returns averaged 512-dim embedding or None.
        """
        embeddings = []
        for i, img in enumerate(images):
            emb = self.extract_from_image(img)
            if emb is not None:
                embeddings.append(emb)
            else:
                logger.warning(f"No face in image {i+1}/{len(images)}, skipping")

        if not embeddings:
            logger.error("No faces found in any of the reference images")
            return None

        logger.info(f"Extracted {len(embeddings)}/{len(images)} face embeddings")
        avg_embedding = np.mean(embeddings, axis=0)
        # Re-normalize after averaging
        avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)
        return avg_embedding

    def save_embedding(self, character_id: UUID, embedding: np.ndarray) -> str:
        """Save embedding to disk, return relative path."""
        path = self._embed_dir / f"{character_id}.pkl"
        with open(path, "wb") as f:
            pickle.dump(embedding, f)
        logger.info(f"Face embedding saved: {path}")
        return str(path)

    def load_embedding(self, embedding_path: str) -> Optional[np.ndarray]:
        """Load embedding from disk."""
        path = Path(embedding_path)
        if not path.exists():
            logger.error(f"Embedding not found: {path}")
            return None
        with open(path, "rb") as f:
            return pickle.load(f)

    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings (0-1)."""
        return float(np.dot(emb1, emb2))

    def check_consistency_score(
        self,
        reference_embedding: np.ndarray,
        generated_image: Image.Image,
    ) -> float:
        """
        Check how consistent a generated image's face is with the reference.
        Returns cosine similarity score (0-1, higher = more consistent).
        Used in quality control pipeline.
        """
        gen_embedding = self.extract_from_image(generated_image)
        if gen_embedding is None:
            return 0.0
        return self.cosine_similarity(reference_embedding, gen_embedding)
