"""Player API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
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
from app.services.riot_api_client import RiotAPIClient, RiotAPIError, get_riot_client

router = APIRouter(prefix="/players", tags=["players"])

SEA_TAG_LINES = {"tw2", "sg2", "ph2", "th2", "vn2", "my2", "id2"}


def _should_ignore_ranked_decrypt_error(exc: RiotAPIError) -> bool:
    return exc.status_code == 400 and "Exception decrypting" in exc.message


def _is_decrypt_error(exc: RiotAPIError) -> bool:
    return exc.status_code == 400 and "Exception decrypting" in exc.message


def _should_resolve_latest_puuid(player, tag_line: str) -> bool:
    if not player:
        return True
    return tag_line.lower() in SEA_TAG_LINES


def _build_player_response(
    player,
    ranked_status: Optional[str] = None,
    ranked_flex_stats: Optional[RankInfo] = None,
) -> PlayerResponse:
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
        ranked_flex_stats=ranked_flex_stats,
        ranked_status=ranked_status,
        created_at=player.created_at,
        updated_at=player.updated_at,
    )


async def _sync_masteries_for_player(
    player,
    player_repo: PlayerRepository,
    mastery_repo: ChampionMasteryRepository,
    db: AsyncSession,
) -> None:
    if not player:
        return

    riot_client: RiotAPIClient = get_riot_client()
    try:
        async with riot_client:
            if not player.summoner_id:
                summoner_data = await riot_client.get_summoner_by_puuid(
                    player.puuid,
                    tag_line=player.tag_line or "na1",
                )
                if not summoner_data or not summoner_data.get("id"):
                    return
                player = await player_repo.upsert_player(
                    puuid=player.puuid,
                    summoner_name=summoner_data.get("name", player.summoner_name),
                    tag_line=player.tag_line,
                    summoner_id=summoner_data.get("id"),
                    profile_icon_id=summoner_data.get("profileIconId", player.profile_icon_id or 0),
                    summoner_level=summoner_data.get("summonerLevel", player.summoner_level or 0),
                    revision_date=summoner_data.get("revisionDate", player.revision_date),
                    ranked_solo_tier=player.ranked_solo_tier,
                    ranked_solo_rank=player.ranked_solo_rank,
                    ranked_solo_league_points=player.ranked_solo_league_points or 0,
                    ranked_solo_wins=player.ranked_solo_wins or 0,
                    ranked_solo_losses=player.ranked_solo_losses or 0,
                )
                await db.commit()

            masteries = await riot_client.get_champion_masteries(
                player.summoner_id,
                tag_line=player.tag_line or "na1",
            )
    except RiotAPIError:
        return
    if not masteries:
        return

    await mastery_repo.upsert_masteries(player.puuid, player.summoner_id, masteries)
    await db.commit()


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
    if not masteries:
        await _sync_masteries_for_player(player, player_repo, mastery_repo, db)
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
    ranked_status = "ranked_from_cache"

    # SEA accounts can rotate from legacy/stale PUUIDs. Re-resolve by Riot ID
    # before returning cached rows so downstream match history uses the current PUUID.
    if _should_resolve_latest_puuid(player, tag_line):
        riot_client: RiotAPIClient = get_riot_client()
        async with riot_client:
            # Get PUUID by Riot ID
            account_data = await riot_client.get_puuid_by_riot_id(summoner_name, tag_line)
            if not account_data:
                if player:
                    return _build_player_response(player)
                raise HTTPException(
                    status_code=404,
                    detail=f"Player {summoner_name}#{tag_line} not found"
                )
            puuid = account_data["puuid"]

            # Get summoner data by PUUID (correct platform for this tag line)
            try:
                summoner_data = await riot_client.get_summoner_by_puuid(puuid, tag_line=tag_line)
            except RiotAPIError as exc:
                if not _is_decrypt_error(exc):
                    raise
                summoner_data = None
            if not summoner_data:
                if not player:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Summoner data not found for {summoner_name}#{tag_line}"
                    )
                player = await repo.upsert_player(
                    puuid=puuid,
                    summoner_name=player.summoner_name,
                    tag_line=player.tag_line,
                    summoner_id=player.summoner_id,
                    profile_icon_id=player.profile_icon_id or 0,
                    summoner_level=player.summoner_level or 1,
                    revision_date=player.revision_date,
                    ranked_solo_tier=player.ranked_solo_tier,
                    ranked_solo_rank=player.ranked_solo_rank,
                    ranked_solo_league_points=player.ranked_solo_league_points or 0,
                    ranked_solo_wins=player.ranked_solo_wins or 0,
                    ranked_solo_losses=player.ranked_solo_losses or 0,
                )
                await db.commit()
                return _build_player_response(player)

            # Get ranked stats
            ranked_data = None
            if "id" in summoner_data:
                try:
                    ranked_data = await riot_client.get_player_ranked_stats(summoner_data["id"], tag_line=tag_line)
                except RiotAPIError as exc:
                    if not _should_ignore_ranked_decrypt_error(exc):
                        raise
                    ranked_status = "ranked_fetch_failed_fallback"
            solo_rank = None
            flex_rank = None
            if ranked_data:
                for entry in ranked_data:
                    if entry.get("queueType") == "RANKED_SOLO_5x5":
                        solo_rank = entry
                    elif entry.get("queueType") == "RANKED_FLEX_SR":
                        flex_rank = entry
            if ranked_status != "ranked_fetch_failed_fallback":
                ranked_status = "ranked_from_riot" if solo_rank else "ranked_empty_from_riot"

            # Upsert player
            try:
                player = await repo.upsert_player(
                    puuid=puuid,
                    summoner_name=summoner_data.get("name", summoner_name),
                    tag_line=tag_line,
                    summoner_id=summoner_data.get("id"),
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
            except IntegrityError:
                await db.rollback()
                # Concurrent syncs or legacy rows can race here; return existing row if present.
                player = await repo.get_by_puuid(puuid) or await repo.get_by_summoner_name(
                    summoner_data.get("name", summoner_name), tag_line
                )
                if not player:
                    raise

    ranked_flex_stats = None
    if _should_resolve_latest_puuid(player, tag_line) and 'flex_rank' in locals() and flex_rank:
        ranked_flex_stats = RankInfo(
            tier=flex_rank.get("tier"),
            rank=flex_rank.get("rank") or "I",
            league_points=flex_rank.get("leaguePoints") or 0,
            wins=flex_rank.get("wins", 0),
            losses=flex_rank.get("losses", 0),
            queue_type="RANKED_FLEX_SR",
        )

    return _build_player_response(
        player,
        ranked_status=ranked_status,
        ranked_flex_stats=ranked_flex_stats,
    )


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
        try:
            summoner_data = await riot_client.get_summoner_by_puuid(puuid, tag_line=player.tag_line)
        except RiotAPIError as exc:
            # Some Riot shards intermittently reject legacy/stale puuids with a decrypt error.
            # Keep the workflow unblocked by returning stored profile data instead of 502.
            if _is_decrypt_error(exc):
                return _build_player_response(player)
            raise
        if not summoner_data:
            raise HTTPException(
                status_code=404,
                detail=f"Summoner data not found for PUUID {puuid}"
            )

        ranked_data = None
        if "id" in summoner_data:
            try:
                ranked_data = await riot_client.get_player_ranked_stats(
                    summoner_data["id"],
                    tag_line=player.tag_line,
                )
            except RiotAPIError as exc:
                if not _should_ignore_ranked_decrypt_error(exc):
                    raise

        solo_rank = None
        flex_rank = None
        if ranked_data:
            for entry in ranked_data:
                if entry.get("queueType") == "RANKED_SOLO_5x5":
                    solo_rank = entry
                elif entry.get("queueType") == "RANKED_FLEX_SR":
                    flex_rank = entry

        player = await repo.upsert_player(
            puuid=puuid,
            summoner_name=summoner_data.get("name", player.summoner_name),
            tag_line=player.tag_line,
            summoner_id=summoner_data.get("id", player.summoner_id),
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

    ranked_flex_stats = None
    if flex_rank:
        ranked_flex_stats = RankInfo(
            tier=flex_rank.get("tier"),
            rank=flex_rank.get("rank") or "I",
            league_points=flex_rank.get("leaguePoints") or 0,
            wins=flex_rank.get("wins", 0),
            losses=flex_rank.get("losses", 0),
            queue_type="RANKED_FLEX_SR",
        )

    return _build_player_response(player, ranked_flex_stats=ranked_flex_stats)
