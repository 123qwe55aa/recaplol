"""Riot platform status API endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.services.riot_api_client import RiotAPIClient, RiotAPIError, get_riot_client

router = APIRouter(prefix="/riot/status", tags=["riot-status"])


def get_riot_client_dependency() -> RiotAPIClient:
    return get_riot_client()


@router.get("/{platform}")
async def get_platform_status(
    platform: str,
    riot_client: RiotAPIClient = Depends(get_riot_client_dependency),
):
    """Get Riot LoL service status for a platform routing value."""
    try:
        async with riot_client:
            status = await riot_client.get_lol_status(platform)
    except RiotAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    if not status:
        raise HTTPException(status_code=404, detail=f"Riot platform {platform} not found")

    return status
