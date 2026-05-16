from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Index, JSON, SmallInteger
from sqlalchemy.sql import func

from app.db.database import Base


class Match(Base):
    __tablename__ = "matches"

    match_id = Column(String(32), primary_key=True)
    game_mode = Column(String(32), nullable=True)
    game_type = Column(String(32), nullable=True)
    game_version = Column(String(32), nullable=True)
    game_duration = Column(Integer, nullable=True)  # seconds
    game_start_timestamp = Column(BigInteger, nullable=True)
    game_end_timestamp = Column(BigInteger, nullable=True)

    # Cached data for quick access
    blue_team_id = Column(Integer, nullable=True)
    red_team_id = Column(Integer, nullable=True)
    blue_team_win = Column(SmallInteger, nullable=True)
    blue_team_bans = Column(JSON, nullable=True)
    red_team_bans = Column(JSON, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_matches_game_start", "game_start_timestamp"),
        Index("ix_matches_updated_at", "updated_at"),
    )


class MatchParticipant(Base):
    __tablename__ = "match_participants"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    match_id = Column(String(32), nullable=False)
    puuid = Column(String(78), nullable=False)

    # Identity
    summoner_name = Column(String(32), nullable=True)
    summoner_id = Column(String(63), nullable=True)
    team_id = Column(Integer, nullable=True)  # 100 = blue, 200 = red
    team_position = Column(String(32), nullable=True)  # TOP, JUNGLE, MID, ADC, SUPPORT
    individual_position = Column(String(32), nullable=True)

    # Champion
    champion_id = Column(Integer, nullable=True)
    champion_name = Column(String(64), nullable=True)
    champion_level = Column(Integer, default=0)

    # Gameplay stats
    kills = Column(Integer, default=0)
    deaths = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    kda = Column(Integer, default=0)
    double_kills = Column(Integer, default=0)
    triple_kills = Column(Integer, default=0)
    quadra_kills = Column(Integer, default=0)
    pentakills = Column(Integer, default=0)

    # Damage
    total_damage_dealt = Column(Integer, default=0)
    total_damage_dealt_to_champions = Column(Integer, default=0)
    total_damage_taken = Column(Integer, default=0)
    damage_dealt_to_objectives = Column(Integer, default=0)
    damage_dealt_to_turrets = Column(Integer, default=0)

    # CS
    neutral_minions_killed = Column(Integer, default=0)
    total_minions_killed = Column(Integer, default=0)
    cs_per_minute = Column(Integer, default=0)

    # Vision
    vision_score = Column(Integer, default=0)
    wards_placed = Column(Integer, default=0)
    wards_destroyed = Column(Integer, default=0)
    vision_wards_bought_in_game = Column(Integer, default=0)

    # Economy
    gold_earned = Column(Integer, default=0)
    gold_spent = Column(Integer, default=0)
    item0 = Column(Integer, nullable=True)
    item1 = Column(Integer, nullable=True)
    item2 = Column(Integer, nullable=True)
    item3 = Column(Integer, nullable=True)
    item4 = Column(Integer, nullable=True)
    item5 = Column(Integer, nullable=True)
    item6 = Column(Integer, nullable=True)  # trinket

    # Other
    perks = Column(JSON, nullable=True)  # runes and keystones
    summoner1_id = Column(Integer, nullable=True)
    summoner2_id = Column(Integer, nullable=True)
    time_played = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_match_participants_match_id", "match_id"),
        Index("ix_match_participants_puuid", "puuid"),
        Index("ix_match_participants_puuid_game_time", "puuid", "match_id"),
    )

    def __init__(self, **kwargs):
        # Apply Python-side defaults for fields not provided
        kwargs.setdefault('champion_level', 0)
        kwargs.setdefault('kills', 0)
        kwargs.setdefault('deaths', 0)
        kwargs.setdefault('assists', 0)
        kwargs.setdefault('kda', 0)
        kwargs.setdefault('double_kills', 0)
        kwargs.setdefault('triple_kills', 0)
        kwargs.setdefault('quadra_kills', 0)
        kwargs.setdefault('pentakills', 0)
        kwargs.setdefault('total_damage_dealt', 0)
        kwargs.setdefault('total_damage_dealt_to_champions', 0)
        kwargs.setdefault('total_damage_taken', 0)
        kwargs.setdefault('damage_dealt_to_objectives', 0)
        kwargs.setdefault('damage_dealt_to_turrets', 0)
        kwargs.setdefault('neutral_minions_killed', 0)
        kwargs.setdefault('total_minions_killed', 0)
        kwargs.setdefault('cs_per_minute', 0)
        kwargs.setdefault('vision_score', 0)
        kwargs.setdefault('wards_placed', 0)
        kwargs.setdefault('wards_destroyed', 0)
        kwargs.setdefault('vision_wards_bought_in_game', 0)
        kwargs.setdefault('gold_earned', 0)
        kwargs.setdefault('gold_spent', 0)
        kwargs.setdefault('time_played', 0)
        super().__init__(**kwargs)
