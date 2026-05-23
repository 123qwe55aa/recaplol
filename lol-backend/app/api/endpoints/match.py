"""Match API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.database import get_db
from app.repositories.match import MatchRepository, MatchParticipantRepository
from app.repositories.match import MatchTimelineRepository
from app.repositories.player import PlayerRepository
from app.schemas.match import (
    MatchResponse,
    MatchListResponse,
    MatchSummaryResponse,
    MatchListWithDetailsResponse,
    MatchRecapResponse,
    MatchRecapParticipant,
    MatchTimelineResponse,
    ParticipantStats,
    MatchTeamInfo,
    TeamBans,
)
from app.services.riot_api_client import RiotAPIClient, RiotAPIError, get_riot_client
from app.services.match_timeline_analyzer import build_match_recap
from app.models.match import Match

router = APIRouter(prefix="/matches", tags=["matches"])


def get_match_timeline_repository(
    db: AsyncSession = Depends(get_db),
) -> MatchTimelineRepository:
    return MatchTimelineRepository(db)


def get_riot_client_dependency() -> RiotAPIClient:
    return get_riot_client()


# Map match_id platform prefix to regional base URL
MATCH_REGION_MAP = {
    "TW1": "https://sea.api.riotgames.com",
    "TW2": "https://sea.api.riotgames.com",
    "KR1": "https://asia.api.riotgames.com",
    "JP1": "https://asia.api.riotgames.com",
    "SG2": "https://sea.api.riotgames.com",
    "TH2": "https://sea.api.riotgames.com",
    "PH2": "https://sea.api.riotgames.com",
    "VN2": "https://sea.api.riotgames.com",
    "MY2": "https://sea.api.riotgames.com",
    "ID2": "https://sea.api.riotgames.com",
    "EUW1": "https://europe.api.riotgames.com",
    "EUNE1": "https://europe.api.riotgames.com",
    "TR1": "https://europe.api.riotgames.com",
    "RU": "https://europe.api.riotgames.com",
    "NA1": "https://americas.api.riotgames.com",
    "BR1": "https://americas.api.riotgames.com",
    "LA1": "https://americas.api.riotgames.com",
    "LA2": "https://americas.api.riotgames.com",
}


def _get_match_region_base_url(match_id: str) -> str:
    """Get the regional base URL for a match ID."""
    prefix = match_id.split("_")[0] if "_" in match_id else match_id[:3]
    return MATCH_REGION_MAP.get(prefix, "https://americas.api.riotgames.com")


def _build_team_info(match, team_id: int) -> MatchTeamInfo:
    """Build team info from match data."""
    is_blue = team_id == 100
    outcome = _team_outcome(match, team_id)
    win = True if outcome == "WIN" else False if outcome == "LOSS" else None
    bans = match.blue_team_bans if is_blue else match.red_team_bans
    ban_list = []
    if bans:
        for b in bans:
            ban_list.append(TeamBans(
                champion_id=b.get("championId"),
                pick_turn=b.get("pickTurn"),
            ))
    return MatchTeamInfo(team_id=team_id, win=win, outcome=outcome, bans=ban_list)


def _is_remake_match(match) -> bool:
    return bool((getattr(match, "game_duration", None) or 0) > 0 and match.game_duration <= 300)


def _team_outcome(match, team_id: Optional[int]) -> str:
    if _is_remake_match(match):
        return "REMAKE"
    if getattr(match, "blue_team_win", None) is None or team_id is None:
        return "UNKNOWN"
    blue_win = bool(match.blue_team_win)
    team_win = blue_win if team_id == 100 else not blue_win
    return "WIN" if team_win else "LOSS"


def _participant_outcome(match, participant) -> str:
    return _team_outcome(match, getattr(participant, "team_id", None))


def _is_remake_payload(info: dict, participants_info: List[dict]) -> bool:
    if any(p.get("gameEndedInEarlySurrender") for p in participants_info):
        return True
    game_duration = info.get("gameDuration") or 0
    return bool(game_duration > 0 and game_duration <= 300)


SEA_TAG_LINES = {"tw1", "tw2", "sg2", "th2", "ph2", "vn2", "my2", "id2"}


def _is_decrypt_error(exc: RiotAPIError) -> bool:
    return exc.status_code == 400 and "Exception decrypting" in exc.message


@router.get("/{puuid}", response_model=MatchListResponse)
async def get_matches(
    puuid: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a list of match IDs for a player.

    - **puuid**: Player's PUUID
    - **limit**: Maximum number of matches to return (1-100)
    - **offset**: Number of matches to skip
    """
    repo = MatchRepository(db)
    matches = await repo.get_recent_matches(puuid, limit=limit, offset=offset)
    total = await repo.get_match_count(puuid)

    return MatchListResponse(
        matches=matches,
        start_index=offset,
        total_count=total,
        puuid=puuid,
    )


def _build_match_summary(match, participants_data: List) -> "MatchSummaryResponse":
    """Build match summary from match + participants."""
    blue_win = bool(match.blue_team_win) if match.blue_team_win is not None else None
    participant_stats = []
    for p in participants_data:
        items = [p.item0, p.item1, p.item2, p.item3, p.item4, p.item5, p.item6]
        items = [i for i in items if i is not None]

        outcome = _participant_outcome(match, p)
        team_win = True if outcome == "WIN" else False if outcome == "LOSS" else None

        participant_stats.append(ParticipantStats(
            puuid=p.puuid,
            summoner_name=p.summoner_name,
            team_id=p.team_id,
            team_position=p.team_position,
            champion_id=p.champion_id,
            champion_name=p.champion_name,
            champion_level=p.champion_level,
            kills=p.kills or 0,
            deaths=p.deaths or 0,
            assists=p.assists or 0,
            kda=float(p.kda) / 100 if p.kda else 0.0,
            total_damage_dealt=p.total_damage_dealt or 0,
            total_damage_dealt_to_champions=p.total_damage_dealt_to_champions or 0,
            total_damage_taken=p.total_damage_taken or 0,
            neutral_minions_killed=p.neutral_minions_killed or 0,
            total_minions_killed=p.total_minions_killed or 0,
            cs_per_minute=float(p.cs_per_minute) / 100 if p.cs_per_minute else 0.0,
            vision_score=p.vision_score or 0,
            wards_placed=p.wards_placed or 0,
            wards_destroyed=p.wards_destroyed or 0,
            gold_earned=p.gold_earned or 0,
            items=items,
            double_kills=p.double_kills or 0,
            triple_kills=p.triple_kills or 0,
            quadra_kills=p.quadra_kills or 0,
            pentakills=p.pentakills or 0,
            win=team_win,
            outcome=outcome,
        ))

    return MatchSummaryResponse(
        match_id=match.match_id,
        game_mode=match.game_mode,
        game_type=match.game_type,
        game_version=match.game_version,
        game_duration=match.game_duration or 0,
        game_start_timestamp=match.game_start_timestamp,
        game_end_timestamp=match.game_end_timestamp,
        blue_team_win=blue_win,
        participants=participant_stats,
    )


def _participant_id_for_puuid(timeline_json: dict, puuid: str) -> Optional[int]:
    info = timeline_json.get("info") or {}
    for participant in info.get("participants") or []:
        if participant.get("puuid") == puuid:
            participant_id = participant.get("participantId")
            return int(participant_id) if participant_id is not None else None

    metadata_participants = (timeline_json.get("metadata") or {}).get("participants") or []
    for index, participant_puuid in enumerate(metadata_participants, start=1):
        if participant_puuid == puuid:
            return index
    return None


@router.post("/timeline/fetch/{match_id}", response_model=MatchTimelineResponse)
async def fetch_match_timeline(
    match_id: str,
    repo: MatchTimelineRepository = Depends(get_match_timeline_repository),
    riot_client: RiotAPIClient = Depends(get_riot_client_dependency),
):
    """
    Fetch and store a Riot Match V5 timeline for later deep recap analysis.

    - **match_id**: Riot match ID, e.g. NA1_1234567890
    """
    region_base = _get_match_region_base_url(match_id)
    async with riot_client:
        timeline_data = await riot_client.get_match_timeline_with_region(match_id, region_base)

    if not timeline_data:
        raise HTTPException(status_code=404, detail=f"Timeline {match_id} not found")

    info = timeline_data.get("info", {})
    timeline = await repo.upsert_timeline(
        match_id=match_id,
        timeline_json=timeline_data,
        frame_interval=info.get("frameInterval"),
        fetched_region=region_base,
    )
    return MatchTimelineResponse(
        match_id=timeline.match_id,
        frame_interval=timeline.frame_interval or 0,
        frames=list(info.get("frames") or []),
    )


@router.get("/{match_id}/recap/{puuid}", response_model=MatchRecapResponse)
async def get_match_recap(
    match_id: str,
    puuid: str,
    db: AsyncSession = Depends(get_db),
    timeline_repo: MatchTimelineRepository = Depends(get_match_timeline_repository),
):
    """
    Build a player-focused deep recap from stored Match V5 timeline data.

    Fetch the match and timeline first, then call this endpoint with the player PUUID.
    """
    match_repo = MatchRepository(db)
    participant_repo = MatchParticipantRepository(db)
    match = await match_repo.get_by_match_id(match_id)
    if not match:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    participant = await participant_repo.get_participant(match_id, puuid)
    if not participant:
        raise HTTPException(status_code=404, detail=f"Participant {puuid} not found")

    timeline = await timeline_repo.get_by_match_id(match_id)
    if not timeline:
        raise HTTPException(status_code=404, detail=f"Timeline {match_id} not found")

    participant_id = _participant_id_for_puuid(timeline.timeline_json, puuid)
    if participant_id is None:
        raise HTTPException(status_code=404, detail=f"Timeline participant {puuid} not found")

    recap = build_match_recap(
        timeline=timeline.timeline_json,
        participant_id=participant_id,
        participant_team_id=participant.team_id,
        game_duration=match.game_duration,
        team_position=participant.team_position,
        individual_position=getattr(participant, "individual_position", None),
    )
    return MatchRecapResponse(
        match_id=match_id,
        participant=MatchRecapParticipant(
            puuid=puuid,
            participant_id=participant_id,
            team_id=participant.team_id,
            champion_name=participant.champion_name,
            team_position=participant.team_position,
        ),
        timeline_stats=recap["timeline_stats"],
        match_phase_summary=recap["match_phase_summary"],
        resource_windows=recap["resource_windows"],
        key_events=recap["key_events"],
        insights=recap["insights"],
    )


@router.get("/{puuid}/details", response_model=MatchListWithDetailsResponse)
async def get_matches_with_details(
    puuid: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get match list with full details for each match.

    - **puuid**: Player's PUUID
    - **limit**: Maximum number of matches to return (1-100)
    - **offset**: Number of matches to skip
    """
    match_repo = MatchRepository(db)
    participant_repo = MatchParticipantRepository(db)

    match_ids = await match_repo.get_recent_matches(puuid, limit=limit, offset=offset)
    total = await match_repo.get_match_count(puuid)

    match_summaries = []
    for match_id in match_ids:
        match = await match_repo.get_by_match_id(match_id)
        if match:
            participants = await participant_repo.get_participants_by_match(match_id)
            match_summaries.append(_build_match_summary(match, participants))

    return MatchListWithDetailsResponse(
        matches=match_summaries,
        start_index=offset,
        total_count=total,
        puuid=puuid,
    )


@router.post("/fetch/{puuid}")
async def fetch_player_matches(
    puuid: str,
    limit: int = Query(default=10, ge=1, le=100),
    region: str = Query(default="americas", description="Region: americas, europe, asia, sea"),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch recent matches for a player from Riot API and store in database.

    - **puuid**: Player's PUUID
    - **limit**: Number of matches to fetch (1-100)
    - **region**: Riot regional routing (americas, europe, asia, sea)
    """
    riot_client: RiotAPIClient = get_riot_client()

    match_repo = MatchRepository(db)
    participant_repo = MatchParticipantRepository(db)
    player_repo = PlayerRepository(db)
    fetched = 0
    updated = 0
    errors = []
    effective_puuid = puuid
    effective_region = region

    async with riot_client:
        player = await player_repo.get_by_puuid(puuid)
        if player and (player.tag_line or "").lower() in SEA_TAG_LINES:
            effective_region = "sea"

        # Get match IDs from Riot API, with SEA + PUUID self-healing fallback.
        try:
            match_ids: List[str] = await riot_client.get_match_ids_by_puuid(
                effective_puuid, start=0, count=limit, region=effective_region
            )
        except RiotAPIError as exc:
            if not _is_decrypt_error(exc):
                raise

            # Retry on SEA first if initial region wasn't SEA.
            if effective_region != "sea":
                try:
                    effective_region = "sea"
                    match_ids = await riot_client.get_match_ids_by_puuid(
                        effective_puuid, start=0, count=limit, region=effective_region
                    )
                except RiotAPIError as sea_exc:
                    if not _is_decrypt_error(sea_exc):
                        raise
                    match_ids = []
            else:
                match_ids = []

            # If still failing, re-resolve latest PUUID from Riot ID and retry on SEA.
            if not match_ids and player:
                account_data = await riot_client.get_puuid_by_riot_id(
                    player.summoner_name,
                    player.tag_line,
                )
                if account_data and account_data.get("puuid"):
                    effective_puuid = account_data["puuid"]
                    effective_region = "sea" if (player.tag_line or "").lower() in SEA_TAG_LINES else effective_region
                    if effective_puuid != puuid:
                        await player_repo.upsert_player(
                            puuid=effective_puuid,
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
                    match_ids = await riot_client.get_match_ids_by_puuid(
                        effective_puuid, start=0, count=limit, region=effective_region
                    )

        if not match_ids:
            return {"fetched": 0, "message": "No matches found on Riot API"}

        # Fetch each match detail and store
        for match_id in match_ids:
            try:
                # Use the correct regional URL for this match
                region_base = _get_match_region_base_url(match_id)
                match_data = await riot_client.get_match_with_region(match_id, region_base)

                if not match_data:
                    errors.append(f"{match_id}: no data returned")
                    continue

                # Check if match already exists
                existing = await match_repo.get_by_match_id(match_id)

            # Parse and store match info
                info = match_data.get("info", {})
                metadata = match_data.get("metadata", {})

                game_duration = info.get("gameDuration", 0)
                game_start = info.get("gameStartTimestamp", 0)
                game_end = info.get("gameEndTimestamp", 0)

                # Parse teams
                teams_data = info.get("teams", [])
                blue_bans = []
                red_bans = []
                blue_win = None
                is_remake = False
                blue_team_id = None
                red_team_id = None

                participants_info = info.get("participants", [])
                is_remake = _is_remake_payload(info, participants_info)

                for team in teams_data:
                    team_id = team.get("teamId")
                    if team_id == 100:
                        blue_team_id = 100
                        blue_win = None if is_remake else 1 if team.get("win", False) else 0
                        bans = team.get("bans", [])
                        for ban in bans:
                            blue_bans.append({
                                "championId": ban.get("championId"),
                                "pickTurn": ban.get("pickTurn"),
                            })
                    else:
                        red_team_id = 200
                        bans = team.get("bans", [])
                        for ban in bans:
                            red_bans.append({
                                "championId": ban.get("championId"),
                                "pickTurn": ban.get("pickTurn"),
                            })

                if existing:
                    # Update existing match
                    existing.game_mode = info.get("gameMode", "")
                    existing.game_type = info.get("gameType", "")
                    existing.game_version = info.get("gameVersion", "")
                    existing.game_duration = game_duration
                    existing.game_start_timestamp = game_start
                    existing.game_end_timestamp = game_end
                    existing.blue_team_id = blue_team_id
                    existing.red_team_id = red_team_id
                    existing.blue_team_win = blue_win
                    existing.blue_team_bans = blue_bans
                    existing.red_team_bans = red_bans
                    updated += 1
                else:
                    # Create new match
                    new_match = Match(
                        match_id=match_id,
                        game_mode=info.get("gameMode", ""),
                        game_type=info.get("gameType", ""),
                        game_version=info.get("gameVersion", ""),
                        game_duration=game_duration,
                        game_start_timestamp=game_start,
                        game_end_timestamp=game_end,
                        blue_team_id=blue_team_id,
                        red_team_id=red_team_id,
                        blue_team_win=blue_win,
                        blue_team_bans=blue_bans,
                        red_team_bans=red_bans,
                    )
                    db.add(new_match)
                    fetched += 1

                # Parse participants
                participants_data = metadata.get("participants", [])
                for i, participant_data in enumerate(participants_info):
                    p_puuid = participants_data[i] if i < len(participants_data) else None
                    if not p_puuid:
                        continue

                    # Riot Match V5 API: all fields are flat on participant object, not inside "stats"
                    kills = participant_data.get("kills", 0) or 0
                    deaths = participant_data.get("deaths", 0) or 0
                    assists = participant_data.get("assists", 0) or 0
                    kda = (kills + assists) / deaths if deaths > 0 else (kills + assists)

                    # Calculate CS per minute
                    total_cs = (participant_data.get("totalMinionsKilled", 0) or 0) + (participant_data.get("neutralMinionsKilled", 0) or 0)
                    cs_per_minute = total_cs / (game_duration / 60) if game_duration > 0 else 0

                    participant_record = {
                        "puuid": p_puuid,
                        "summoner_name": participant_data.get("summonerName", "") or "",
                        "summoner_id": participant_data.get("summonerId", "") or "",
                        "team_id": participant_data.get("teamId", 0) or 0,
                        "team_position": participant_data.get("teamPosition", "") or "",
                        "individual_position": participant_data.get("individualPosition", "") or "",
                        "champion_id": participant_data.get("championId", 0) or 0,
                        "champion_name": participant_data.get("championName", "") or "",
                        "champion_level": participant_data.get("championLevel", 0) or 0,
                        "kills": kills,
                        "deaths": deaths,
                        "assists": assists,
                        "kda": int(kda * 100),
                        "double_kills": participant_data.get("doubleKills", 0) or 0,
                        "triple_kills": participant_data.get("tripleKills", 0) or 0,
                        "quadra_kills": participant_data.get("quadraKills", 0) or 0,
                        "pentakills": participant_data.get("pentaKills", 0) or 0,
                        "total_damage_dealt": participant_data.get("totalDamageDealt", 0) or 0,
                        "total_damage_dealt_to_champions": participant_data.get("totalDamageDealtToChampions", 0) or 0,
                        "total_damage_taken": participant_data.get("totalDamageTaken", 0) or 0,
                        "damage_dealt_to_objectives": participant_data.get("damageDealtToObjectives", 0) or 0,
                        "damage_dealt_to_turrets": participant_data.get("damageDealtToTurrets", 0) or 0,
                        "neutral_minions_killed": participant_data.get("neutralMinionsKilled", 0) or 0,
                        "total_minions_killed": participant_data.get("totalMinionsKilled", 0) or 0,
                        "cs_per_minute": int(cs_per_minute * 100),
                        "vision_score": participant_data.get("visionScore", 0) or 0,
                        "wards_placed": participant_data.get("wardsPlaced", 0) or 0,
                        "wards_destroyed": participant_data.get("wardsDestroyed", 0) or 0,
                        "vision_wards_bought_in_game": participant_data.get("visionWardsBoughtInGame", 0) or 0,
                        "gold_earned": participant_data.get("goldEarned", 0) or 0,
                        "gold_spent": participant_data.get("goldSpent", 0) or 0,
                        "item0": participant_data.get("item0"),
                        "item1": participant_data.get("item1"),
                        "item2": participant_data.get("item2"),
                        "item3": participant_data.get("item3"),
                        "item4": participant_data.get("item4"),
                        "item5": participant_data.get("item5"),
                        "item6": participant_data.get("item6"),
                        "perks": participant_data.get("perks"),
                        "summoner1_id": participant_data.get("summoner1Id"),
                        "summoner2_id": participant_data.get("summoner2Id"),
                        "time_played": participant_data.get("timePlayed", 0) or 0,
                    }

                    await participant_repo.upsert_participants(match_id, [participant_record])

            except Exception as e:
                errors.append(f"{match_id}: {str(e)}")

    await db.commit()

    return {
        "fetched": fetched,
        "updated": updated,
        "puuid": effective_puuid,
        "region": effective_region,
        "match_count": len(match_ids),
        "errors": errors if errors else None,
    }


@router.get("/detail/{match_id}", response_model=MatchResponse)
async def get_match_detail(
    match_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific match.

    - **match_id**: The unique match identifier
    """
    match_repo = MatchRepository(db)
    match = await match_repo.get_by_match_id(match_id)

    if not match:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    participant_repo = MatchParticipantRepository(db)
    participants = await participant_repo.get_participants_by_match(match_id)

    # Build participant stats
    blue_win = bool(match.blue_team_win) if match.blue_team_win is not None else None
    participant_stats = []
    for p in participants:
        items = [p.item0, p.item1, p.item2, p.item3, p.item4, p.item5, p.item6]
        items = [i for i in items if i is not None]

        outcome = _participant_outcome(match, p)
        team_win = True if outcome == "WIN" else False if outcome == "LOSS" else None

        participant_stats.append(ParticipantStats(
            puuid=p.puuid,
            summoner_name=p.summoner_name,
            team_id=p.team_id,
            team_position=p.team_position,
            champion_id=p.champion_id,
            champion_name=p.champion_name,
            champion_level=p.champion_level,
            kills=p.kills or 0,
            deaths=p.deaths or 0,
            assists=p.assists or 0,
            kda=float(p.kda) / 100 if p.kda else 0.0,
            total_damage_dealt=p.total_damage_dealt or 0,
            total_damage_dealt_to_champions=p.total_damage_dealt_to_champions or 0,
            total_damage_taken=p.total_damage_taken or 0,
            neutral_minions_killed=p.neutral_minions_killed or 0,
            total_minions_killed=p.total_minions_killed or 0,
            cs_per_minute=float(p.cs_per_minute) / 100 if p.cs_per_minute else 0.0,
            vision_score=p.vision_score or 0,
            wards_placed=p.wards_placed or 0,
            wards_destroyed=p.wards_destroyed or 0,
            gold_earned=p.gold_earned or 0,
            items=items,
            double_kills=p.double_kills or 0,
            triple_kills=p.triple_kills or 0,
            quadra_kills=p.quadra_kills or 0,
            pentakills=p.pentakills or 0,
            win=team_win,
            outcome=outcome,
        ))

    # Build team info
    blue_team = _build_team_info(match, 100) if match.blue_team_id else None
    red_team = _build_team_info(match, 200) if match.red_team_id else None

    return MatchResponse(
        match_id=match.match_id,
        game_mode=match.game_mode,
        game_type=match.game_type,
        game_version=match.game_version,
        game_duration=match.game_duration or 0,
        game_start_timestamp=match.game_start_timestamp,
        game_end_timestamp=match.game_end_timestamp,
        blue_team=blue_team,
        red_team=red_team,
        participants=participant_stats,
    )
