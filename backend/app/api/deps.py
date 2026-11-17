"""
API Dependencies Module
Provides authentication, authorization, client tier evaluation, and security checks.
"""

from fastapi import Request

from app.core.config import settings


async def get_api_client_tier(request: Request) -> str:
    """
    Evaluates caller's authorization tier based on the X-API-Key request header.
    Returns 'vip' if a valid pre-shared key is present, otherwise 'public'.
    """
    x_api_key: str | None = request.headers.get("X-API-Key")
    if x_api_key and x_api_key.strip() in settings.AUTHORIZED_API_KEYS:
        return "vip"
    return "public"
