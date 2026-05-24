from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class RankInfo(BaseModel):
    tier: str = Field(None, description="BRONZE, SILVER, GOLD, PLATINUM, DIAMOND, MASTER, GRANDMASTER, CHALLENGER")
    rank: str = Field(None, description="I, II, III, IV")
    league_points: int = Field(0, description="League points")
    wins: int = Field(0, description="Wins")
    losses: int = Field(0, description="Losses")
    queue_type: str = Field("RANKED_SOLO_5x5", description="Queue type")


class PlayerBase(BaseModel):
    puuid: str
    summoner_name: str
    tag_line: str


class PlayerResponse(PlayerBase):
    summoner_id: Optional[str] = None
    profile_icon_id: Optional[int] = None
    summoner_level: int = 1
    revision_date: Optional[int] = None

    ranked_stats: Optional[RankInfo] = None
    ranked_status: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChampionMasteryResponse(BaseModel):
    champion_id: int
    champion_name: Optional[str] = None
    champion_level: int
    champion_points: int
    champion_points_since_last_level: int
    champion_points_until_next_level: int
    chest_granted: bool
    last_played_time: Optional[int] = None
    tokens_earned: int

    model_config = {"from_attributes": True}


class PlayerChampionMasteryResponse(BaseModel):
    puuid: str
    summoner_name: str
    total_champion_levels: int
    total_champion_points: int
    champion_masteries: List[ChampionMasteryResponse]

    model_config = {"from_attributes": True}
