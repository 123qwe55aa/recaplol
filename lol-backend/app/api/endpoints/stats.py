"""Stats API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict
from collections import defaultdict

from app.db.database import get_db
from app.repositories.player import PlayerRepository
from app.repositories.match import MatchRepository, MatchParticipantRepository
from app.schemas.stats import (
    CareerStats,
    ChampionStats,
    RoleStats,
    PlayerStatsResponse,
)

router = APIRouter(prefix="/stats", tags=["stats"])


def _participant_won(participant) -> bool:
    """Return the match outcome attached by endpoint loaders."""
    return bool(getattr(participant, "win", False))


def _participant_counted(participant) -> bool:
    return getattr(participant, "outcome", "UNKNOWN") != "REMAKE"


def _attach_win_result(participant, match) -> None:
    if match and (match.game_duration or 0) > 0 and match.game_duration <= 300:
        participant.win = None
        participant.outcome = "REMAKE"
        return
    if not participant or not match or match.blue_team_win is None or participant.team_id is None:
        participant.win = None
        participant.outcome = "UNKNOWN"
        return

    blue_win = bool(match.blue_team_win)
    participant.win = blue_win if participant.team_id == 100 else not blue_win
    participant.outcome = "WIN" if participant.win else "LOSS"


def _calculate_career_stats(
    participants: list,
    puuid: str,
    summoner_name: str,
) -> CareerStats:
    """Calculate career statistics from participant records."""
    participants = [p for p in participants if _participant_counted(p)]
    total_matches = len(participants)
    if total_matches == 0:
        return CareerStats(puuid=puuid, summoner_name=summoner_name)

    total_kills = sum(p.kills for p in participants)
    total_deaths = sum(p.deaths for p in participants)
    total_assists = sum(p.assists for p in participants)

    total_cs = sum(
        (p.total_minions_killed or 0) + (p.neutral_minions_killed or 0)
        for p in participants
    )
    total_vision = sum(p.vision_score or 0 for p in participants)
    total_gold = sum(p.gold_earned or 0 for p in participants)

    total_double = sum(p.double_kills or 0 for p in participants)
    total_triple = sum(p.triple_kills or 0 for p in participants)
    total_quadra = sum(p.quadra_kills or 0 for p in participants)
    total_penta = sum(p.pentakills or 0 for p in participants)

    wins = sum(1 for p in participants if _participant_won(p))

    win_rate = (wins / total_matches * 100) if total_matches > 0 else 0.0
    overall_kda = (total_kills + total_assists) / total_deaths if total_deaths > 0 else 0.0

    return CareerStats(
        puuid=puuid,
        summoner_name=summoner_name,
        total_matches=total_matches,
        total_wins=wins,
        total_losses=total_matches - wins,
        win_rate=round(win_rate, 2),
        total_kills=total_kills,
        total_deaths=total_deaths,
        total_assists=total_assists,
        overall_kda=round(overall_kda, 2),
        avg_kills=round(total_kills / total_matches, 2),
        avg_deaths=round(total_deaths / total_matches, 2),
        avg_assists=round(total_assists / total_matches, 2),
        avg_cs_per_minute=round(total_cs / total_matches / 30, 2),  # Assume 30 min avg
        avg_vision_score=round(total_vision / total_matches, 2),
        avg_gold_earned=round(total_gold / total_matches, 2),
        total_double_kills=total_double,
        total_triple_kills=total_triple,
        total_quadra_kills=total_quadra,
        total_pentakills=total_penta,
    )


def _calculate_champion_stats(
    participants: list,
    champion_id: int,
) -> ChampionStats:
    """Calculate champion-specific statistics."""
    champ_participants = [
        p for p in participants
        if p.champion_id == champion_id and _participant_counted(p)
    ]
    games_played = len(champ_participants)

    if games_played == 0:
        return ChampionStats(champion_id=champion_id)

    kills = sum(p.kills for p in champ_participants)
    deaths = sum(p.deaths for p in champ_participants)
    assists = sum(p.assists for p in champ_participants)
    cs = sum(
        (p.total_minions_killed or 0) + (p.neutral_minions_killed or 0)
        for p in champ_participants
    )

    wins = sum(1 for p in champ_participants if _participant_won(p))
    kda = (kills + assists) / deaths if deaths > 0 else 0.0

    return ChampionStats(
        champion_id=champion_id,
        champion_name=champ_participants[0].champion_name if champ_participants else None,
        games_played=games_played,
        wins=wins,
        losses=games_played - wins,
        win_rate=round(wins / games_played * 100, 2),
        kills=kills,
        deaths=deaths,
        assists=assists,
        kda=round(kda, 2),
        avg_cs_per_minute=round(cs / games_played / 30, 2),
    )


def _calculate_role_stats(participants: list) -> List[RoleStats]:
    """Calculate role-based statistics."""
    role_data: Dict[str, dict] = defaultdict(lambda: {
        "games": 0,
        "kills": 0,
        "deaths": 0,
        "assists": 0,
        "cs": 0,
        "wins": 0,
    })

    for p in participants:
        if not _participant_counted(p):
            continue
        role = p.team_position or "UNKNOWN"
        role_data[role]["games"] += 1
        role_data[role]["kills"] += p.kills
        role_data[role]["deaths"] += p.deaths
        role_data[role]["assists"] += p.assists
        role_data[role]["cs"] += (p.total_minions_killed or 0) + (p.neutral_minions_killed or 0)
        if _participant_won(p):
            role_data[role]["wins"] += 1

    role_stats = []
    for role, data in role_data.items():
        games = data["games"]
        if games == 0:
            continue
        avg_kda = (data["kills"] + data["assists"]) / data["deaths"] if data["deaths"] > 0 else 0.0
        role_stats.append(RoleStats(
            role=role,
            games_played=games,
            win_rate=round(data["wins"] / games * 100, 2),
            avg_kda=round(avg_kda, 2),
            avg_cs_per_minute=round(data["cs"] / games / 30, 2),
        ))

    return role_stats


@router.get("/players/{puuid}/overview", response_model=PlayerStatsResponse)
async def get_player_overview(
    puuid: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    Get player career overview statistics.

    - **puuid**: Player's PUUID (encrypted account ID)
    - **limit**: Number of recent matches to analyze (1-500)
    """
    player_repo = PlayerRepository(db)
    player = await player_repo.get_by_puuid(puuid)

    if not player:
        raise HTTPException(status_code=404, detail=f"Player {puuid} not found")

    match_repo = MatchRepository(db)
    participant_repo = MatchParticipantRepository(db)

    match_ids = await match_repo.get_recent_matches(puuid, limit=limit)

    participants = []
    for match_id in match_ids:
        match = await match_repo.get_by_match_id(match_id)
        participant = await participant_repo.get_participant(match_id, puuid)
        if participant:
            _attach_win_result(participant, match)
            participants.append(participant)

    career = _calculate_career_stats(participants, puuid, player.summoner_name)

    # Calculate champion stats for top champions
    champion_data: Dict[int, list] = defaultdict(list)
    for p in participants:
        champion_data[p.champion_id].append(p)

    top_champions = sorted(
        champion_data.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:10]

    champion_stats = [
        _calculate_champion_stats(data, champ_id)
        for champ_id, data in top_champions
    ]

    role_stats = _calculate_role_stats(participants)

    return PlayerStatsResponse(
        puuid=puuid,
        summoner_name=player.summoner_name,
        career=career,
        champion_stats=champion_stats,
        role_stats=role_stats,
    )


@router.get("/players/{puuid}/champions/{champion_id}", response_model=ChampionStats)
async def get_player_champion_stats(
    puuid: str,
    champion_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    Get player statistics for a specific champion.

    - **puuid**: Player's PUUID (encrypted account ID)
    - **champion_id**: Champion ID
    - **limit**: Number of recent matches to analyze (1-500)
    """
    player_repo = PlayerRepository(db)
    player = await player_repo.get_by_puuid(puuid)

    if not player:
        raise HTTPException(status_code=404, detail=f"Player {puuid} not found")

    match_repo = MatchRepository(db)
    participant_repo = MatchParticipantRepository(db)
    participants = await participant_repo.get_participant_stats(
        puuid=puuid,
        champion_id=champion_id,
        limit=limit,
    )

    if not participants:
        raise HTTPException(
            status_code=404,
            detail=f"No matches found for champion {champion_id}"
        )

    for participant in participants:
        match = await match_repo.get_by_match_id(participant.match_id)
        _attach_win_result(participant, match)

    return _calculate_champion_stats(participants, champion_id)


@router.get("/players/{puuid}/recent", response_model=PlayerStatsResponse)
async def get_player_recent_stats(
    puuid: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get player statistics for recent N games.

    - **puuid**: Player's PUUID (encrypted account ID)
    - **limit**: Number of recent matches to analyze (1-100)
    """
    player_repo = PlayerRepository(db)
    player = await player_repo.get_by_puuid(puuid)

    if not player:
        raise HTTPException(status_code=404, detail=f"Player {puuid} not found")

    match_repo = MatchRepository(db)
    participant_repo = MatchParticipantRepository(db)

    match_ids = await match_repo.get_recent_matches(puuid, limit=limit)

    participants = []
    for match_id in match_ids:
        match = await match_repo.get_by_match_id(match_id)
        participant = await participant_repo.get_participant(match_id, puuid)
        if participant:
            _attach_win_result(participant, match)
            participants.append(participant)

    career = _calculate_career_stats(participants, puuid, player.summoner_name)

    # For recent stats, show only champions played
    champion_data: Dict[int, list] = defaultdict(list)
    for p in participants:
        champion_data[p.champion_id].append(p)

    top_champions = sorted(
        champion_data.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:5]

    champion_stats = [
        _calculate_champion_stats(data, champ_id)
        for champ_id, data in top_champions
    ]

    role_stats = _calculate_role_stats(participants)

    return PlayerStatsResponse(
        puuid=puuid,
        summoner_name=player.summoner_name,
        career=career,
        champion_stats=champion_stats,
        role_stats=role_stats,
    )
