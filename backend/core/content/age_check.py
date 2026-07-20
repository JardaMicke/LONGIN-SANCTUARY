"""
Age Check & NSFW Content Management.
Handles session-based verification and filters outputs/models based on age gate.
"""

from uuid import UUID
from fastapi import Request, HTTPException, status
from jose import jwt, JWTError
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from core.characters.character_manager import CharacterManager

# Simple in-memory or cookie JWT signature settings
JWT_ALGORITHM = "HS256"


class AgeVerifier:
    """Manages session verification for NSFW contents."""

    @staticmethod
    def create_verification_token(user_ip: str) -> str:
        """Create a short-lived JWT token verifying the user has passed the age gate."""
        import datetime
        payload = {
            "verified": True,
            "ip": user_ip,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24) # Valid for 24h
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def is_verified(request: Request) -> bool:
        """Check if request contains valid age verification in headers or cookies."""
        if not settings.AGE_CHECK_ENABLED:
            return True

        # Try to find token in headers or cookies
        token = request.headers.get("X-Age-Verification") or request.cookies.get("age_verified_token")
        if not token:
            return False

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
            if payload.get("verified") is True:
                # Optional: verify IP address matches
                # client_ip = request.client.host if request.client else ""
                # if payload.get("ip") == client_ip:
                return True
        except JWTError:
            pass

        return False

    @classmethod
    async def verify_nsfw_access(
        cls,
        character_id: UUID,
        request: Request,
        db: AsyncSession
    ) -> bool:
        """
        Verify if the request is permitted to access the character.
        If character is NSFW, user must have passed the age check.
        """
        char_manager = CharacterManager(db)
        character = await char_manager.get(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # If character is not NSFW, everyone has access
        if not character.nsfw_enabled:
            return True

        # If globally NSFW is disabled but character is NSFW, deny access
        if not settings.NSFW_ENABLED:
            logger.warning(f"Blocked access to character {character_id}: NSFW content is globally disabled")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="NSFW content is disabled on this server."
            )

        # Check if age gate has been verified
        if not cls.is_verified(request):
            logger.info(f"Blocked access to NSFW character {character_id}: Age verification required")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Age verification required to access this content."
            )

        return True
