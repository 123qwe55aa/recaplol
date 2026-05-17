"""OP.GG data API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.schemas.build import ChampionBuildResponse
from app.services.opgg_scraper import (
    get_opgg_scraper,
    OPGGError,
    OPGGRateLimitError,
    OPGGNotFoundError,
    OPGGParseError,
)
from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/opgg", tags=["opgg"])


# Champion name to slug mapping helper
CHAMPION_SLUGS: Dict[str, str] = {
    # This would typically come from a data file or API
    # Using common champions as examples
    "ahri": "ahri",
    "akali": "akali",
    "ekko": "ekko",
    "fizz": "fizz",
    "ahri": "ahri",
    # Add more as needed - could fetch from ddragon
}


def get_champion_slug(champ_name: str) -> str:
    """Convert champion name to URL-friendly slug."""
    # Handle known mappings first
    slug = CHAMPION_SLUGS.get(champ_name.lower())
    if slug:
        return slug

    # Default: lowercase and remove spaces/special chars
    import re
    slug = champ_name.lower().strip()
    slug = re.sub(r"[^a-z0-9]", "", slug)
    return slug


@router.get("/champions/{champ_name}/build", response_model=ChampionBuildResponse)
async def get_champion_build(
    champ_name: str,
    region: str = Query(default="kr", description="Server region (kr, na, euw, etc.)"),
    queue: str = Query(default="RANKED_SOLO_5x5", description="Queue type"),
    tier: str = Query(default="overall", description="Rank tier filter"),
    version: Optional[str] = Query(default=None, description="Patch version"),
    counters_count: int = Query(default=5, ge=1, le=10, description="Number of counter champions to return"),
    role: str = Query(default="", description="Role filter (top, jungle, mid, adc, support)"),
):
    """
    Get champion build data from OP.GG including:
    - Win rate
    - Recommended item builds (start, core, final)
    - Skill order
    - Runes
    - Counter matchups

    **Note:** This endpoint scrapes OP.GG and is rate-limited.
    Responses are cached for up to 6 hours.
    """
    # Check feature flag
    if not settings.opgg_enabled:
        raise HTTPException(
            status_code=503,
            detail="OP.GG feature is currently disabled",
        )

    champ_slug = get_champion_slug(champ_name)

    filters = {
        "champ_name": champ_name,
        "region": region,
        "queue": queue,
        "tier": tier,
        "version": version,
        "role": role,
    }

    logger.info(
        "opgg_build_request",
        champ_name=champ_name,
        champ_slug=champ_slug,
        region=region,
        queue=queue,
        tier=tier,
    )

    scraper = get_opgg_scraper()
    retries = 0
    last_error: Optional[OPGGError] = None

    while retries <= settings.opgg_max_retries:
        try:
            data = await scraper.get_champion_build(
                champ_slug=champ_slug,
                region=region,
                queue=queue,
                tier=tier,
                version=version,
                role=role,
                use_cache=True,
            )

            # Truncate matchups to requested count
            if "matchups" in data:
                if len(data["matchups"].get("counters", [])) > counters_count:
                    data["matchups"]["counters"] = data["matchups"]["counters"][:counters_count]
                if len(data["matchups"].get("countered_by", [])) > counters_count:
                    data["matchups"]["countered_by"] = data["matchups"]["countered_by"][:counters_count]

            # Build response
            return ChampionBuildResponse(
                success=True,
                data=data,
                cached=data.get("cached", False),
            )

        except OPGGRateLimitError as e:
            last_error = e
            if retries < settings.opgg_max_retries:
                retries += 1
                import asyncio
                wait_time = 2 ** retries  # Exponential backoff
                logger.warning(
                    "opgg_rate_limited_retry",
                    champ_name=champ_name,
                    attempt=retries,
                    wait_seconds=wait_time,
                )
                await asyncio.sleep(wait_time)
                continue
            else:
                logger.error(
                    "opgg_max_retries_exceeded",
                    champ_name=champ_name,
                    error=str(e),
                )
                raise HTTPException(
                    status_code=429,
                    detail="OP.GG rate limit exceeded. Please try again later.",
                )

        except OPGGNotFoundError as e:
            logger.warning("opgg_champion_not_found", champ_name=champ_name)
            raise HTTPException(
                status_code=404,
                detail=f"Champion '{champ_name}' not found on OP.GG",
            )

        except OPGGParseError as e:
            logger.error(
                "opgg_parse_error",
                champ_name=champ_name,
                error=str(e),
                filters=filters,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to parse OP.GG data. The page structure may have changed.",
            )

        except OPGGError as e:
            logger.error(
                "opgg_unknown_error",
                champ_name=champ_name,
                error=str(e),
                filters=filters,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch OP.GG data: {str(e)}",
            )
        except Exception as e:
            logger.exception(
                "opgg_unhandled_exception",
                champ_name=champ_name,
                error=str(e),
                filters=filters,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Unhandled OP.GG endpoint error: {str(e)}",
            )

    # Should not reach here, but safety net
    raise HTTPException(
        status_code=500,
        detail="Unexpected error fetching OP.GG data",
    )


@router.get("/champions", response_model=List[str])
async def list_supported_champions():
    """
    List champion slugs that can be used with the OP.GG endpoint.

    This is a convenience endpoint returning known champion names.
    Unknown champions will still be attempted with slug conversion.
    """
    return list(CHAMPION_SLUGS.keys())


@router.get("/regions")
async def list_supported_regions():
    """List supported OP.GG regions."""
    return {
        "regions": [
            {"code": "kr", "name": "Korea"},
            {"code": "na", "name": "North America"},
            {"code": "euw", "name": "EU West"},
            {"code": "eune", "name": "EU Nordic & East"},
            {"code": "jp", "name": "Japan"},
            {"code": "oce", "name": "Oceania"},
            {"code": "ru", "name": "Russia"},
            {"code": "br", "name": "Brazil"},
            {"code": "las", "name": "Latin America South"},
            {"code": "lan", "name": "Latin America North"},
            {"code": "tr", "name": "Turkey"},
            {"code": "sg", "name": "Singapore"},
            {"code": "my", "name": "Malaysia"},
            {"code": "ph", "name": "Philippines"},
            {"code": "th", "name": "Thailand"},
            {"code": "tw", "name": "Taiwan"},
            {"code": "vn", "name": "Vietnam"},
        ]
    }


@router.get("/metrics")
async def get_opgg_metrics():
    """Get OP.GG scraper metrics for observability."""
    scraper = get_opgg_scraper()
    return {
        **scraper.get_metrics(),
        "feature_enabled": settings.opgg_enabled,
        "cache_ttl_seconds": settings.opgg_cache_ttl,
        "rate_limit_per_second": settings.opgg_rate_limit_per_second,
    }
