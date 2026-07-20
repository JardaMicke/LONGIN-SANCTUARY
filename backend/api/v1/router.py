"""Main API v1 router — aggregates all route modules."""

from fastapi import APIRouter

from api.v1.routes import characters, chat, generation, network, scenarios, settings, system

api_router = APIRouter()

api_router.include_router(system.router, prefix="/system", tags=["System"])
api_router.include_router(characters.router, prefix="/characters", tags=["Characters"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(scenarios.router, prefix="/scenarios", tags=["Scenarios"])
api_router.include_router(generation.router, prefix="/generation", tags=["Generation"])
api_router.include_router(network.router, prefix="/network", tags=["Network"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
