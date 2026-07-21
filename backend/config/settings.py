"""
LONGIN SANCTUARY — Application Settings
Loaded from environment variables / .env file
"""

from functools import lru_cache
from typing import Literal, Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────
    APP_NAME: str = "LONGIN_SANCTUARY"
    APP_VERSION: str = "0.1.0"
    APP_ENV: Literal["development", "production", "test"] = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-to-a-random-secret-key"

    # ── API ─────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    ALLOWED_ORIGINS: Any = [
        "http://localhost:3000",
        "http://192.168.1.15:3000",
        "http://192.168.1.18:3000",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v

    # ── PostgreSQL ──────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "longin_sanctuary"
    POSTGRES_USER: str = "sanctuary"
    POSTGRES_PASSWORD: str = "changeme"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ── Redis ───────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # ── Qdrant ──────────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""

    # ── ComfyUI ─────────────────────────────────────────────
    COMFYUI_PRIMARY_URL: str = "http://192.168.1.15:8188"
    COMFYUI_EXTRA_URLS: Any = []

    @field_validator("COMFYUI_EXTRA_URLS", mode="before")
    @classmethod
    def parse_comfyui_urls(cls, v):
        if isinstance(v, str) and v:
            return [u.strip() for u in v.split(",")]
        return v or []

    # ── Ollama ──────────────────────────────────────────────
    OLLAMA_PRIMARY_URL: str = "http://192.168.1.15:11434"
    OLLAMA_EXTRA_URLS: Any = []

    @field_validator("OLLAMA_EXTRA_URLS", mode="before")
    @classmethod
    def parse_ollama_urls(cls, v):
        if isinstance(v, str) and v:
            return [u.strip() for u in v.split(",")]
        return v or []

    # ── exo (Distributed LLM) ───────────────────────────────
    EXO_ENABLED: bool = True
    EXO_PORT: int = 5678
    EXO_API_URL: str = "http://localhost:52415"

    # ── LLM Settings ────────────────────────────────────────
    DEFAULT_LLM_MODEL: str = "llama3.1:8b"
    DEFAULT_TEMPERATURE: float = 0.8
    DEFAULT_MAX_TOKENS: int = 4096
    DEFAULT_CONTEXT_LENGTH: int = 8192

    # ── Memory Settings ─────────────────────────────────────
    STM_MAX_TOKENS: int = 4096
    LTM_SUMMARIZE_THRESHOLD: int = 8000
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.75
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # ── Image Generation ────────────────────────────────────
    DEFAULT_IMAGE_MODEL: str = "flux_dev"
    DEFAULT_IMAGE_STEPS: int = 30
    DEFAULT_IMAGE_CFG: float = 7.0
    DEFAULT_IMAGE_WIDTH: int = 1024
    DEFAULT_IMAGE_HEIGHT: int = 1024
    IP_ADAPTER_STRENGTH: float = 0.8
    FACE_CONSISTENCY_THRESHOLD: float = 0.85

    # ── Video Generation ────────────────────────────────────
    DEFAULT_VIDEO_MODEL: str = "wanvideo"
    DEFAULT_VIDEO_FRAMES: int = 24
    DEFAULT_VIDEO_FPS: int = 8
    DEFAULT_VIDEO_WIDTH: int = 832
    DEFAULT_VIDEO_HEIGHT: int = 480

    # ── Content & Safety ────────────────────────────────────
    NSFW_ENABLED: bool = False
    AGE_CHECK_ENABLED: bool = True
    AGE_CHECK_MIN_AGE: int = 18
    CONTENT_FILTER_LEVEL: Literal["strict", "moderate", "permissive"] = "moderate"

    # ── Network Cluster ─────────────────────────────────────
    CLUSTER_DISCOVERY_ENABLED: bool = True
    CLUSTER_DISCOVERY_PORT: int = 9999
    CLUSTER_SECRET: str = "change-this-cluster-secret"
    NODE_ROLE: Literal["master", "worker", "both"] = "both"
    NODE_NAME: str = "CORE-DT"

    # ── Paths ───────────────────────────────────────────────
    MODELS_PATH: str = "./model_weights"
    OUTPUT_PATH: str = "./output"
    COMFYUI_PATH: str = "./comfyui"
    LORA_PATH: str = "./model_weights/loras"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
