from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from datetime import datetime

from app.models.player import Player, ChampionMastery
from app.repositories.base import BaseRepository


class PlayerRepository(BaseRepository[Player]):
    def __init__(self, session: AsyncSession):
        super().__init__(Player, session)

    async def get_by_puuid(self, puuid: str) -> Optional[Player]:
        result = await self.session.execute(
            select(Player).where(Player.puuid == puuid)
        )
        return result.scalar_one_or_none()

    async def get_by_summoner_name(self, name: str, tag_line: str) -> Optional[Player]:
        result = await self.session.execute(
            select(Player).where(
                and_(
                    Player.summoner_name == name,
                    Player.tag_line == tag_line
                )
            ).order_by(
                desc(Player.updated_at),
                desc(Player.created_at),
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_summoner_id(self, summoner_id: str) -> Optional[Player]:
        result = await self.session.execute(
            select(Player).where(Player.summoner_id == summoner_id)
        )
        return result.scalar_one_or_none()

    async def upsert_player(
        self,
        puuid: str,
        summoner_name: str,
        tag_line: str,
        **kwargs
    ) -> Player:
        # Avoid unique conflicts from empty-string summoner IDs.
        if kwargs.get("summoner_id") == "":
            kwargs["summoner_id"] = None

        existing = await self.get_by_puuid(puuid)
        if not existing and kwargs.get("summoner_id"):
            existing = await self.get_by_summoner_id(kwargs["summoner_id"])

        if existing:
            existing.puuid = puuid
            existing.summoner_name = summoner_name
            existing.tag_line = tag_line
            for key, value in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        else:
            player = Player(
                puuid=puuid,
                summoner_name=summoner_name,
                tag_line=tag_line,
                **kwargs
            )
            return await self.create(player)

    async def get_recently_updated(self, limit: int = 100) -> List[Player]:
        result = await self.session.execute(
            select(Player)
            .order_by(Player.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class ChampionMasteryRepository(BaseRepository[ChampionMastery]):
    def __init__(self, session: AsyncSession):
        super().__init__(ChampionMastery, session)

    async def get_by_puuid(self, puuid: str) -> List[ChampionMastery]:
        result = await self.session.execute(
            select(ChampionMastery)
            .where(ChampionMastery.puuid == puuid)
            .order_by(ChampionMastery.champion_points.desc())
        )
        return list(result.scalars().all())

    async def get_by_puuid_and_champion(
        self, puuid: str, champion_id: int
    ) -> Optional[ChampionMastery]:
        result = await self.session.execute(
            select(ChampionMastery).where(
                and_(
                    ChampionMastery.puuid == puuid,
                    ChampionMastery.champion_id == champion_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def upsert_masteries(
        self, puuid: str, summoner_id: str, masteries: List[dict]
    ) -> List[ChampionMastery]:
        results = []
        for m in masteries:
            existing = await self.get_by_puuid_and_champion(puuid, m["championId"])
            if existing:
                for key, value in m.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                results.append(existing)
            else:
                mastery = ChampionMastery(
                    puuid=puuid,
                    summoner_id=summoner_id,
                    champion_id=m["championId"],
                    champion_level=m.get("championLevel", 0),
                    champion_points=m.get("championPoints", 0),
                    champion_points_since_last_level=m.get("championPointsSinceLastLevel", 0),
                    champion_points_until_next_level=m.get("championPointsUntilNextLevel", 0),
                    chest_granted=m.get("chestGranted", False),
                    last_played_time=m.get("lastPlayedTime"),
                    tokens_earned=m.get("tokensEarned", 0),
                )
                self.session.add(mastery)
                results.append(mastery)
        await self.session.flush()
        return results
