from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


class CareerStats(BaseModel):
    puuid: str
    summoner_name: str

    # Overall stats
    total_matches: int = 0
    total_wins: int = 0
    total_losses: int = 0
    win_rate: float = 0.0

    # KDA
    total_kills: int = 0
    total_deaths: int = 0
    total_assists: int = 0
    overall_kda: float = 0.0
    avg_kills: float = 0.0
    avg_deaths: float = 0.0
    avg_assists: float = 0.0

    # Performance
    avg_cs_per_minute: float = 0.0
    avg_vision_score: float = 0.0
    avg_gold_earned: float = 0.0

    # Multi-kills
    total_double_kills: int = 0
    total_triple_kills: int = 0
    total_quadra_kills: int = 0
    total_pentakills: int = 0


class ChampionStats(BaseModel):
    champion_id: int
    champion_name: Optional[str] = None
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    kda: float = 0.0
    avg_cs_per_minute: float = 0.0


class RoleStats(BaseModel):
    role: str  # TOP, JUNGLE, MID, ADC, SUPPORT
    games_played: int = 0
    win_rate: float = 0.0
    avg_kda: float = 0.0
    avg_cs_per_minute: float = 0.0


class PlayerStatsResponse(BaseModel):
    puuid: str
    summoner_name: str
    career: CareerStats
    champion_stats: List[ChampionStats] = Field(default_factory=list)
    role_stats: List[RoleStats] = Field(default_factory=list)


# Analysis schemas
class RankProgress(BaseModel):
    timestamp: datetime
    tier: str
    rank: str
    league_points: int
    wins: int
    losses: int


class KDAEvolution(BaseModel):
    timestamp: datetime
    window: str  # "7 days", "30 days", etc.
    avg_kills: float
    avg_deaths: float
    avg_assists: float
    avg_kda: float
    games_played: int


class TrendAnalysis(BaseModel):
    puuid: str
    summoner_name: str

    # Rank progress
    rank_history: List[RankProgress] = Field(default_factory=list)

    # KDA evolution
    kda_evolution: List[KDAEvolution] = Field(default_factory=list)

    # Performance trends
    recent_win_rate: float = 0.0
    win_rate_change: float = 0.0  # positive = improving

    # Insights
    best_champion: Optional[ChampionStats] = None
    most_played_role: Optional[RoleStats] = None
    improvement_areas: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)


class ProgressAnalysis(BaseModel):
    """Analysis of player rank progression over time."""
    puuid: str
    summoner_name: str

    current_tier: str
    current_rank: str
    current_league_points: int

    # Progress metrics
    games_played_in_current_rank: int = 0
    win_rate_in_current_rank: float = 0.0

    # Promotional games info
    promotional_game_target: Optional[str] = None

    # Win/loss streak
    current_streak: int = 0
    streak_type: str = "none"  # "win", "loss", "none"

    # Recommendations
    estimated_games_to_promotion: Optional[int] = None
    recommended_improvement: List[str] = Field(default_factory=list)
