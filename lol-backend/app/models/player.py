from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Index, JSON
from sqlalchemy.sql import func
from datetime import datetime

from app.db.database import Base


class Player(Base):
    __tablename__ = "players"

    puuid = Column(String(78), primary_key=True)
    summoner_id = Column(String(63), unique=True, nullable=True)
    summoner_name = Column(String(32), nullable=False)
    tag_line = Column(String(32), nullable=False)
    profile_icon_id = Column(Integer, nullable=True)
    summoner_level = Column(Integer, default=1, nullable=False)
    revision_date = Column(BigInteger, nullable=True)

    # Ranked data
    ranked_solo_tier = Column(String(32), nullable=True)
    ranked_solo_rank = Column(String(10), nullable=True)
    ranked_solo_league_points = Column(Integer, default=0, nullable=False)
    ranked_solo_wins = Column(Integer, default=0, nullable=False)
    ranked_solo_losses = Column(Integer, default=0, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_players_summoner_name", "summoner_name"),
        Index("ix_players_updated_at", "updated_at"),
    )

    def __init__(self, **kwargs):
        # Apply Python-side defaults for fields not provided
        kwargs.setdefault('summoner_level', 1)
        kwargs.setdefault('ranked_solo_league_points', 0)
        kwargs.setdefault('ranked_solo_wins', 0)
        kwargs.setdefault('ranked_solo_losses', 0)
        super().__init__(**kwargs)


class ChampionMastery(Base):
    __tablename__ = "champion_masteries"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    puuid = Column(String(78), nullable=False)
    summoner_id = Column(String(63), nullable=False)
    champion_id = Column(Integer, nullable=False)
    champion_level = Column(Integer, default=0, nullable=False)
    champion_points = Column(Integer, default=0, nullable=False)
    champion_points_since_last_level = Column(BigInteger, default=0)
    champion_points_until_next_level = Column(BigInteger, default=0)
    chest_granted = Column(Integer, default=0)
    last_played_time = Column(BigInteger, nullable=True)
    tokens_earned = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_champion_mastery_puuid_champion", "puuid", "champion_id", unique=True),
        Index("ix_champion_mastery_puuid", "puuid"),
    )

    def __init__(self, **kwargs):
        # Apply Python-side defaults for fields not provided
        kwargs.setdefault('champion_level', 0)
        kwargs.setdefault('champion_points', 0)
        kwargs.setdefault('chest_granted', 0)
        kwargs.setdefault('tokens_earned', 0)
        super().__init__(**kwargs)
