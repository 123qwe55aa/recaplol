"""Analysis API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

from app.db.database import get_db
from app.repositories.player import PlayerRepository
from app.repositories.match import MatchRepository, MatchParticipantRepository
from app.schemas.stats import (
    CareerStats,
    ChampionStats,
    RoleStats,
    KDAEvolution,
    RankProgress,
    TrendAnalysis,
    ProgressAnalysis,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _participant_won(participant) -> bool:
    return bool(getattr(participant, "win", False))


def _attach_win_result(participant, match) -> None:
    if not participant or not match or match.blue_team_win is None or participant.team_id is None:
        participant.win = False
        return

    blue_win = bool(match.blue_team_win)
    participant.win = blue_win if participant.team_id == 100 else not blue_win


def _analyze_kda_trends(
    participants: list,
    window_days: int = 7,
) -> List[KDAEvolution]:
    """Analyze KDA trends over time windows."""
    if not participants:
        return []

    now = datetime.utcnow()

    # Group participants by time window
    windows = {
        "7 days": now - timedelta(days=7),
        "14 days": now - timedelta(days=14),
        "30 days": now - timedelta(days=30),
    }

    # For simplicity, assume participants are ordered by recency
    # and divide them into approximate time windows
    results = []
    total = len(participants)

    for window_name, cutoff in windows.items():
        # In a real implementation, you'd filter by match timestamp
        # For now, we'll use a simplified approach
        window_size = total // 3 if total >= 3 else total
        if window_size == 0:
            continue

        window_participants = participants[:window_size]

        kills = sum(p.kills for p in window_participants)
        deaths = sum(p.deaths for p in window_participants)
        assists = sum(p.assists for p in window_participants)
        games = len(window_participants)

        avg_kills = kills / games if games > 0 else 0.0
        avg_deaths = deaths / games if games > 0 else 0.0
        avg_assists = assists / games if games > 0 else 0.0
        avg_kda = (kills + assists) / deaths if deaths > 0 else 0.0

        results.append(KDAEvolution(
            timestamp=now,
            window=window_name,
            avg_kills=round(avg_kills, 2),
            avg_deaths=round(avg_deaths, 2),
            avg_assists=round(avg_assists, 2),
            avg_kda=round(avg_kda, 2),
            games_played=games,
        ))

    return results


def _identify_strengths_and_weaknesses(
    champion_stats: List[ChampionStats],
    role_stats: List[RoleStats],
    career: CareerStats,
) -> tuple[List[str], List[str]]:
    """Identify player strengths and areas for improvement."""
    strengths = []
    improvements = []

    # Analyze KDA
    if career.overall_kda > 4.0:
        strengths.append("Exceptional overall KDA ratio")
    elif career.overall_kda < 2.0:
        improvements.append("Work on reducing deaths and increasing assists")

    # Analyze CS
    if career.avg_cs_per_minute > 8.0:
        strengths.append("Excellent laning phase CS performance")
    elif career.avg_cs_per_minute < 5.0:
        improvements.append("Improve CS per minute in laning phase")

    # Analyze Vision
    if career.avg_vision_score > 30:
        strengths.append("Strong vision control")
    elif career.avg_vision_score < 15:
        improvements.append("Buy more wards and track enemy movement")

    # Multi-kill performance
    total_multikills = (
        career.total_double_kills +
        career.total_triple_kills +
        career.total_quadra_kills +
        career.total_pentakills
    )
    if career.total_matches > 0:
        multikill_rate = total_multikills / career.total_matches
        if multikill_rate > 0.2:
            strengths.append("Strong multi-kill performance")

    # Champion diversity
    if len(champion_stats) > 5:
        strengths.append("Wide champion pool")
    elif len(champion_stats) <= 2 and career.total_matches > 20:
        improvements.append("Expand champion pool for better team synergy")

    # Role flexibility
    if len(role_stats) >= 3:
        strengths.append("Flexible across multiple roles")
    elif len(role_stats) == 1:
        improvements.append("Consider learning additional roles")

    return strengths[:3], improvements[:3]


@router.get("/players/{puuid}/trends", response_model=TrendAnalysis)
async def get_player_trends(
    puuid: str,
    limit: int = Query(default=100, ge=10, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    Get KDA and win rate trend analysis for a player.

    - **puuid**: Player's PUUID (encrypted account ID)
    - **limit**: Number of recent matches to analyze (10-500)
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

    if not participants:
        return TrendAnalysis(
            puuid=puuid,
            summoner_name=player.summoner_name,
        )

    # Calculate career stats for insights
    total = len(participants)
    wins = sum(1 for p in participants if _participant_won(p))
    recent_win_rate = (wins / total * 100) if total > 0 else 0.0

    # Calculate kda evolution
    kda_evolution = _analyze_kda_trends(participants)

    # Calculate champion stats for best champion
    champion_data: dict = defaultdict(list)
    for p in participants:
        champion_data[p.champion_id].append(p)

    top_champions = sorted(
        champion_data.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:5]

    champ_stats = []
    for champ_id, data in top_champions:
        games = len(data)
        kills = sum(p.kills for p in data)
        deaths = sum(p.deaths for p in data)
        assists = sum(p.assists for p in data)
        champ_wins = sum(1 for p in data if _participant_won(p))

        champ_stats.append(ChampionStats(
            champion_id=champ_id,
            champion_name=data[0].champion_name,
            games_played=games,
            wins=champ_wins,
            losses=games - champ_wins,
            win_rate=round(champ_wins / games * 100, 2) if games > 0 else 0.0,
            kills=kills,
            deaths=deaths,
            assists=assists,
            kda=round((kills + assists) / deaths, 2) if deaths > 0 else 0.0,
        ))

    best_champion = champ_stats[0] if champ_stats else None

    # Calculate role stats
    role_data: dict = defaultdict(lambda: {"games": 0, "kills": 0, "deaths": 0, "assists": 0, "wins": 0})
    for p in participants:
        role = p.team_position or "UNKNOWN"
        role_data[role]["games"] += 1
        role_data[role]["kills"] += p.kills
        role_data[role]["deaths"] += p.deaths
        role_data[role]["assists"] += p.assists
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
            avg_cs_per_minute=0.0,
        ))

    most_played_role = max(role_stats, key=lambda x: x.games_played) if role_stats else None

    # Get insights
    career = CareerStats(
        puuid=puuid,
        summoner_name=player.summoner_name,
        total_matches=total,
        total_wins=wins,
        total_losses=total - wins,
        win_rate=round(recent_win_rate, 2),
        overall_kda=0.0,
    )
    strengths, improvements = _identify_strengths_and_weaknesses(
        champ_stats, role_stats, career
    )

    return TrendAnalysis(
        puuid=puuid,
        summoner_name=player.summoner_name,
        rank_history=[],  # Would need historical rank data
        kda_evolution=kda_evolution,
        recent_win_rate=round(recent_win_rate, 2),
        win_rate_change=0.0,  # Would need comparison to previous period
        best_champion=best_champion,
        most_played_role=most_played_role,
        strengths=strengths,
        improvement_areas=improvements,
    )


@router.get("/players/{puuid}/progress", response_model=ProgressAnalysis)
async def get_player_progress(
    puuid: str,
    limit: int = Query(default=50, ge=10, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Get player rank progression analysis.

    - **puuid**: Player's PUUID (encrypted account ID)
    - **limit**: Number of recent matches to analyze (10-200)
    """
    player_repo = PlayerRepository(db)
    player = await player_repo.get_by_puuid(puuid)

    if not player:
        raise HTTPException(status_code=404, detail=f"Player {puuid} not found")

    if not player.ranked_solo_tier:
        raise HTTPException(
            status_code=404,
            detail=f"No ranked data found for player {puuid}"
        )

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

    total_games = len(participants)
    wins = sum(1 for p in participants if _participant_won(p))
    losses = total_games - wins
    win_rate = (wins / total_games * 100) if total_games > 0 else 0.0

    # Calculate streak
    streak = 0
    streak_type = "none"
    if participants:
        # Check last few games for streak
        last_result = _participant_won(participants[0]) if participants else None
        streak = 1
        for p in participants[1:min(5, len(participants))]:
            current_result = _participant_won(p)
            if current_result == last_result:
                streak += 1
            else:
                break

        if last_result:
            streak_type = "win"
        else:
            streak_type = "loss"

    # Estimate games to promotion (rough calculation)
    # This depends on LP gains which vary by tier
    tier_order = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
    current_tier_idx = tier_order.index(player.ranked_solo_tier.upper()) if player.ranked_solo_tier.upper() in tier_order else 0

    # Calculate LP needed for next division
    lp_per_win = 20
    lp_per_loss = -15
    net_lp_per_game = (win_rate / 100 * lp_per_win) + ((1 - win_rate / 100) * lp_per_loss)
    games_to_promotion = None
    if net_lp_per_game > 0 and player.ranked_solo_rank:
        # Estimate 100 LP needed for promotion
        games_to_promotion = int(100 / net_lp_per_game)

    recommendations = []
    if win_rate < 45:
        recommendations.append("Focus on improving win rate before climbing")
    elif win_rate > 55 and streak_type == "loss":
        recommendations.append("You're on a losing streak - consider a break")
    if losses > wins:
        recommendations.append("Work on closing out games when ahead")

    return ProgressAnalysis(
        puuid=puuid,
        summoner_name=player.summoner_name,
        current_tier=player.ranked_solo_tier,
        current_rank=player.ranked_solo_rank or "I",
        current_league_points=player.ranked_solo_league_points,
        games_played_in_current_rank=total_games,
        win_rate_in_current_rank=round(win_rate, 2),
        current_streak=streak if streak_type != "none" else 0,
        streak_type=streak_type,
        estimated_games_to_promotion=games_to_promotion,
        recommended_improvement=recommendations,
    )
