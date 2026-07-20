"""
LONGIN SANCTUARY — Core API Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger

from config.settings import settings
from api.v1.router import api_router
from core.network.device_discovery import NetworkDiscovery


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info(f"🌟 Starting LONGIN SANCTUARY v{settings.APP_VERSION}")
    logger.info(f"   Node: {settings.NODE_NAME} | Role: {settings.NODE_ROLE}")

    # Start network discovery if enabled
    if settings.CLUSTER_DISCOVERY_ENABLED:
        discovery = NetworkDiscovery()
        await discovery.start()
        logger.info("🌐 Cluster discovery started")

    yield

    logger.info("👋 LONGIN SANCTUARY shutting down...")


app = FastAPI(
    title="LONGIN SANCTUARY API",
    description="AI Character Platform — Local, Private, Distributed",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ───────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "ok",
        "node": settings.NODE_NAME,
        "role": settings.NODE_ROLE,
        "version": "0.1.0",
    }
