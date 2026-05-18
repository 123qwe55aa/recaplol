"""Player API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.database import get_db
from app.repositories.player import PlayerRepository, ChampionMasteryRepository
from app.schemas.player import (
    PlayerResponse,
    RankInfo,
    ChampionMasteryResponse,
    PlayerChampionMasteryResponse,
)
from app.services.riot_api_client import RiotAPIClient, get_riot_client

router = APIRouter(prefix="/players", tags=["players"])


def _build_player_response(player) -> PlayerResponse:
    ranked_stats = None
    if player.ranked_solo_tier:
        ranked_stats = RankInfo(
            tier=player.ranked_solo_tier,
            rank=player.ranked_solo_rank or "I",
            league_points=player.ranked_solo_league_points,
            wins=player.ranked_solo_wins,
            losses=player.ranked_solo_losses,
            queue_type="RANKED_SOLO_5x5",
        )

    return PlayerResponse(
        puuid=player.puuid,
        summoner_name=player.summoner_name,
        tag_line=player.tag_line,
        summoner_id=player.summoner_id,
        profile_icon_id=player.profile_icon_id,
        summoner_level=player.summoner_level,
        revision_date=player.revision_date,
        ranked_stats=ranked_stats,
        created_at=player.created_at,
        updated_at=player.updated_at,
    )


@router.get("/{puuid}", response_model=PlayerResponse)
async def get_player(
    puuid: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get player basic information by PUUID.

    - **puuid**: Player's PUUID (encrypted account ID)
    """
    repo = PlayerRepository(db)
    player = await repo.get_by_puuid(puuid)

    if not player:
        raise HTTPException(status_code=404, detail=f"Player {puuid} not found")

    return _build_player_response(player)


@router.get("/{puuid}/ranked", response_model=RankInfo)
async def get_player_ranked(
    puuid: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get player ranked information by PUUID.

    - **puuid**: Player's PUUID (encrypted account ID)
    """
    repo = PlayerRepository(db)
    player = await repo.get_by_puuid(puuid)

    if not player:
        raise HTTPException(status_code=404, detail=f"Player {puuid} not found")

    if not player.ranked_solo_tier:
        raise HTTPException(status_code=404, detail=f"No ranked data found for player {puuid}")

    return RankInfo(
        tier=player.ranked_solo_tier,
        rank=player.ranked_solo_rank or "I",
        league_points=player.ranked_solo_league_points,
        wins=player.ranked_solo_wins,
        losses=player.ranked_solo_losses,
        queue_type="RANKED_SOLO_5x5",
    )


@router.get("/{puuid}/mastery", response_model=PlayerChampionMasteryResponse)
async def get_player_mastery(
    puuid: str,
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get player champion mastery (top champions).

    - **puuid**: Player's PUUID (encrypted account ID)
    - **limit**: Maximum number of champions to return (1-100)
    """
    player_repo = PlayerRepository(db)
    player = await player_repo.get_by_puuid(puuid)

    if not player:
        raise HTTPException(status_code=404, detail=f"Player {puuid} not found")

    mastery_repo = ChampionMasteryRepository(db)
    masteries = await mastery_repo.get_by_puuid(puuid)

    # Apply limit
    masteries = masteries[:limit]

    total_champion_levels = sum(m.champion_level for m in masteries)
    total_champion_points = sum(m.champion_points for m in masteries)

    champion_masteries = [
        ChampionMasteryResponse(
            champion_id=m.champion_id,
            champion_level=m.champion_level,
            champion_points=m.champion_points,
            champion_points_since_last_level=m.champion_points_since_last_level,
            champion_points_until_next_level=m.champion_points_until_next_level,
            chest_granted=bool(m.chest_granted),
            last_played_time=m.last_played_time,
            tokens_earned=m.tokens_earned,
        )
        for m in masteries
    ]

    return PlayerChampionMasteryResponse(
        puuid=puuid,
        summoner_name=player.summoner_name,
        total_champion_levels=total_champion_levels,
        total_champion_points=total_champion_points,
        champion_masteries=champion_masteries,
    )


@router.get("/by-summoner/{summoner_name}", response_model=PlayerResponse)
async def get_player_by_summoner(
    summoner_name: str,
    tag_line: str = Query(..., description="Tag line (e.g., NA1, EUW1)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get player by summoner name and tag line.

    - **summoner_name**: The player's summoner name (e.g., "Faker")
    - **tag_line**: The player's tag line (e.g., "NA1", "KR1")
    """
    repo = PlayerRepository(db)
    player = await repo.get_by_summoner_name(summoner_name, tag_line)

    # If not in DB, fetch from Riot API and upsert
    if not player:
        riot_client: RiotAPIClient = get_riot_client()
        async with riot_client:
            # Get PUUID by Riot ID
            account_data = await riot_client.get_puuid_by_riot_id(summoner_name, tag_line)
            if not account_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Player {summoner_name}#{tag_line} not found"
                )
            puuid = account_data["puuid"]

            # Get summoner data by PUUID (correct platform for this tag line)
            summoner_data = await riot_client.get_summoner_by_puuid(puuid, tag_line=tag_line)
            if not summoner_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Summoner data not found for {summoner_name}#{tag_line}"
                )

            # Get ranked stats
            ranked_data = await riot_client.get_player_ranked_stats(summoner_data["id"], tag_line=tag_line) if "id" in summoner_data else None
            solo_rank = None
            if ranked_data:
                for entry in ranked_data:
                    if entry.get("queueType") == "RANKED_SOLO_5x5":
                        solo_rank = entry
                        break

            # Upsert player
            player = await repo.upsert_player(
                puuid=puuid,
                summoner_name=summoner_data.get("name", summoner_name),
                tag_line=tag_line,
                summoner_id=summoner_data.get("id", ""),
                profile_icon_id=summoner_data.get("profileIconId", 0),
                summoner_level=summoner_data.get("summonerLevel", 0),
                revision_date=summoner_data.get("revisionDate", 0),
                ranked_solo_tier=solo_rank.get("tier") if solo_rank else None,
                ranked_solo_rank=solo_rank.get("rank") if solo_rank else None,
                ranked_solo_league_points=solo_rank.get("leaguePoints") if solo_rank else 0,
                ranked_solo_wins=solo_rank.get("wins", 0) if solo_rank else 0,
                ranked_solo_losses=solo_rank.get("losses", 0) if solo_rank else 0,
            )
            await db.commit()

    return _build_player_response(player)


@router.post("/{puuid}/refresh", response_model=PlayerResponse)
async def refresh_player_by_puuid(
    puuid: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Force refresh player profile/ranked data by PUUID.

    This bypasses Riot ID lookup and uses the stored player record's
    tag line for platform routing.
    """
    repo = PlayerRepository(db)
    player = await repo.get_by_puuid(puuid)
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {puuid} not found")

    riot_client: RiotAPIClient = get_riot_client()
    async with riot_client:
        summoner_data = await riot_client.get_summoner_by_puuid(puuid, tag_line=player.tag_line)
        if not summoner_data:
            raise HTTPException(
                status_code=404,
                detail=f"Summoner data not found for PUUID {puuid}"
            )

        ranked_data = await riot_client.get_player_ranked_stats(
            summoner_data["id"],
            tag_line=player.tag_line,
        ) if "id" in summoner_data else None

        solo_rank = None
        if ranked_data:
            for entry in ranked_data:
                if entry.get("queueType") == "RANKED_SOLO_5x5":
                    solo_rank = entry
                    break

        player = await repo.upsert_player(
            puuid=puuid,
            summoner_name=summoner_data.get("name", player.summoner_name),
            tag_line=player.tag_line,
            summoner_id=summoner_data.get("id", player.summoner_id or ""),
            profile_icon_id=summoner_data.get("profileIconId", player.profile_icon_id or 0),
            summoner_level=summoner_data.get("summonerLevel", player.summoner_level),
            revision_date=summoner_data.get("revisionDate", player.revision_date),
            ranked_solo_tier=solo_rank.get("tier") if solo_rank else None,
            ranked_solo_rank=solo_rank.get("rank") if solo_rank else None,
            ranked_solo_league_points=solo_rank.get("leaguePoints") if solo_rank else 0,
            ranked_solo_wins=solo_rank.get("wins", 0) if solo_rank else 0,
            ranked_solo_losses=solo_rank.get("losses", 0) if solo_rank else 0,
        )
        await db.commit()

    return _build_player_response(player)
