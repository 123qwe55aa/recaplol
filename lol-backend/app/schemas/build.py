from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class RuneOption(BaseModel):
    id: str
    name: str
    icon: str
    slot: int


class ItemOption(BaseModel):
    id: str
    name: str
    icon: str
    category: str  # "start", "core", "final"


class SkillOrder(BaseModel):
    order: str  # e.g., "Q > W > E"
    max: str     # e.g., "W"


class ChampionCounter(BaseModel):
    champion_name: str
    win_rate: float
    games: int
    advantage: Optional[float] = None  # Positive = good for this champ, negative = bad


class MatchupList(BaseModel):
    counters: List[ChampionCounter] = Field(default_factory=list)  # Champions that beat this champ (克制该英雄)
    countered_by: List[ChampionCounter] = Field(default_factory=list)  # Champions this champ beats (该英雄克制)


class SummonerSpellOption(BaseModel):
    id: str
    name: str
    icon: str


class RoleBuild(BaseModel):
    role: str
    runes: List[RuneOption]
    items: List[ItemOption]
    skill_order: SkillOrder
    summoner_spells: List[SummonerSpellOption]
    matchups: MatchupList = Field(default_factory=MatchupList)
    jungle_pathing: Optional[str] = None


class ChampionBuild(BaseModel):
    champion_name: str
    win_rate: Optional[float] = None
    pick_rate: Optional[float] = None
    games_played: Optional[int] = None
    roles: List[str] = Field(default_factory=list)
    items: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    skills: List[str] = Field(default_factory=list)
    runes: List[Dict[str, Any]] = Field(default_factory=list)
    matchups: MatchupList = Field(default_factory=MatchupList)
    last_updated: datetime
    source: str = "op.gg"


class ChampionBuildResponse(BaseModel):
    success: bool = True
    data: Optional[ChampionBuild] = None
    error: Optional[str] = None
    cached: bool = False


class ChampionListItem(BaseModel):
    name: str
    slug: str  # URL-friendly name


class ChampionSearchResponse(BaseModel):
    success: bool = True
    data: List[ChampionListItem] = Field(default_factory=list)
    error: Optional[str] = None
