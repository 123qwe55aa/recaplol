from pydantic import BaseModel, Field
from typing import Optional, List


class ParticipantStats(BaseModel):
    # Identity
    puuid: Optional[str] = None
    summoner_name: Optional[str] = None
    team_id: Optional[int] = None
    team_position: Optional[str] = None
    champion_id: Optional[int] = None
    champion_name: Optional[str] = None
    champion_level: int = 0

    # KDA
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    kda: float = 0.0

    # Damage
    total_damage_dealt: int = 0
    total_damage_dealt_to_champions: int = 0
    total_damage_taken: int = 0

    # CS
    neutral_minions_killed: int = 0
    total_minions_killed: int = 0
    cs_per_minute: float = 0.0

    # Vision
    vision_score: int = 0
    wards_placed: int = 0
    wards_destroyed: int = 0

    # Economy
    gold_earned: int = 0
    items: List[int] = Field(default_factory=list)

    # Multi-kills
    double_kills: int = 0
    triple_kills: int = 0
    quadra_kills: int = 0
    pentakills: int = 0

    # Outcome (derived from team_id + blue_team_win, with REMAKE as neutral)
    win: Optional[bool] = None
    outcome: str = "UNKNOWN"


class TeamBans(BaseModel):
    champion_id: Optional[int] = None
    pick_turn: Optional[int] = None


class MatchTeamInfo(BaseModel):
    team_id: int
    win: Optional[bool] = None
    outcome: str = "UNKNOWN"
    bans: List[TeamBans] = Field(default_factory=list)


class MatchResponse(BaseModel):
    match_id: str
    game_mode: Optional[str] = None
    game_type: Optional[str] = None
    game_version: Optional[str] = None
    game_duration: int = 0  # seconds
    game_start_timestamp: Optional[int] = None
    game_end_timestamp: Optional[int] = None

    blue_team: Optional[MatchTeamInfo] = None
    red_team: Optional[MatchTeamInfo] = None

    participants: List[ParticipantStats] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class MatchListResponse(BaseModel):
    matches: List[str] = Field(default_factory=list)
    start_index: int = 0
    total_count: int = 0
    puuid: str


class MatchSummaryResponse(BaseModel):
    """Match with full details for list display."""
    match_id: str
    game_mode: Optional[str] = None
    game_type: Optional[str] = None
    game_version: Optional[str] = None
    game_duration: int = 0
    game_start_timestamp: Optional[int] = None
    game_end_timestamp: Optional[int] = None
    blue_team_win: Optional[bool] = None
    participants: List[ParticipantStats] = Field(default_factory=list)

    def get_participant_win(self, team_id: int) -> bool:
        if self.blue_team_win is None:
            return False
        return self.blue_team_win if team_id == 100 else not self.blue_team_win


class MatchListWithDetailsResponse(BaseModel):
    """Match list response with embedded full details for each match."""
    matches: List[MatchSummaryResponse] = Field(default_factory=list)
    start_index: int = 0
    total_count: int = 0
    puuid: str


class MatchTimelineEvent(BaseModel):
    type: str
    timestamp: int
    participant_id: int
    data: dict = Field(default_factory=dict)


class MatchTimelineResponse(BaseModel):
    match_id: str
    frame_interval: int
    frames: List[dict] = Field(default_factory=list)


class TimelineInsight(BaseModel):
    type: str
    severity: str = "medium"
    title: str
    evidence: List[str] = Field(default_factory=list)
    recommendation: str


class ResourceWindow(BaseModel):
    resource: Optional[str] = None
    timestamp: int
    minute: float
    killer_team_id: Optional[int] = None
    player_team_id: Optional[int] = None
    player_team_secured: Optional[bool] = None
    player_died_before: bool = False
    death_timestamps: List[int] = Field(default_factory=list)


class MatchRecapParticipant(BaseModel):
    puuid: str
    participant_id: int
    team_id: Optional[int] = None
    champion_name: Optional[str] = None
    team_position: Optional[str] = None


class MatchRecapResponse(BaseModel):
    match_id: str
    participant: MatchRecapParticipant
    timeline_stats: dict = Field(default_factory=dict)
    match_phase_summary: dict = Field(default_factory=dict)
    resource_windows: List[ResourceWindow] = Field(default_factory=list)
    key_events: dict = Field(default_factory=dict)
    insights: List[TimelineInsight] = Field(default_factory=list)
