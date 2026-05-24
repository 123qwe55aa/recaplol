"""Health and diagnostics endpoints."""
from fastapi import APIRouter

from app.core.config import settings
from app.services.riot_api_client import RiotAPIError, get_riot_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/riot")
async def riot_health_check():
    """Check Riot API connectivity with current runtime key."""
    key = settings.riot_api_key or ""
    masked_key = f"{key[:8]}..." if key else ""

    if not key:
        return {
            "ok": False,
            "reason": "missing_riot_api_key",
            "key_prefix": masked_key,
        }

    riot_client = get_riot_client()
    try:
        async with riot_client:
            # Minimal account-v1 probe. This may return 404 for fake user, which still
            # proves authentication succeeded.
            await riot_client.get_puuid_by_riot_id("healthcheck", "NA1")
        return {
            "ok": True,
            "reason": "connected",
            "key_prefix": masked_key,
        }
    except RiotAPIError as exc:
        if exc.status_code == 404:
            return {
                "ok": True,
                "reason": "connected_not_found_probe",
                "upstream_status": 404,
                "key_prefix": masked_key,
            }
        return {
            "ok": False,
            "reason": "riot_api_error",
            "upstream_status": exc.status_code,
            "message": exc.message,
            "key_prefix": masked_key,
        }
