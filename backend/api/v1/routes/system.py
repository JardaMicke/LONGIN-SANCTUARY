"""System / health routes."""
from fastapi import APIRouter, Request
from config.settings import settings

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok", "node": settings.NODE_NAME, "version": "0.1.0"}

@router.get("/info")
async def info():
    return {
        "node_name": settings.NODE_NAME,
        "node_role": settings.NODE_ROLE,
        "nsfw_enabled": settings.NSFW_ENABLED,
        "cluster_discovery": settings.CLUSTER_DISCOVERY_ENABLED,
    }


@router.post("/age-verify")
async def age_verify(request: Request):
    """
    Submits age verification.
    Generates a JWT cookie/token valid for 24 hours.
    """
    from core.content.age_check import AgeVerifier
    client_ip = request.client.host if request.client else "127.0.0.1"
    token = AgeVerifier.create_verification_token(client_ip)
    
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"status": "verified", "token": token})
    # Set httponly cookie for safety
    response.set_cookie(
        key="age_verified_token",
        value=token,
        max_age=86400, # 24 hours
        httponly=True,
        samesite="lax"
    )
    return response


@router.get("/age-status")
async def age_status(request: Request):
    """Check if the user session has been verified (18+)."""
    from core.content.age_check import AgeVerifier
    is_verified = AgeVerifier.is_verified(request)
    return {"verified": is_verified}
