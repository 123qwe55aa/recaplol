from typing import Optional, List
import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from datetime import datetime

from app.models.match import Match, MatchParticipant, MatchTimeline
from app.repositories.base import BaseRepository


class MatchRepository(BaseRepository[Match]):
    def __init__(self, session: AsyncSession):
        super().__init__(Match, session)

    async def get_by_match_id(self, match_id: str) -> Optional[Match]:
        result = await self.session.execute(
            select(Match).where(Match.match_id == match_id)
        )
        return result.scalar_one_or_none()

    async def match_exists(self, match_id: str) -> bool:
        result = await self.session.execute(
            select(Match.match_id).where(Match.match_id == match_id)
        )
        return result.scalar_one_or_none() is not None

    async def get_recent_matches(
        self, puuid: str, limit: int = 20, offset: int = 0
    ) -> List[str]:
        subq = (
            select(
                MatchParticipant.match_id.label("match_id"),
            )
            .where(MatchParticipant.puuid == puuid)
            .group_by(MatchParticipant.match_id)
            .subquery()
        )
        result = await self.session.execute(
            select(subq.c.match_id)
            .join(Match, Match.match_id == subq.c.match_id)
            .order_by(desc(Match.game_start_timestamp), desc(subq.c.match_id))
            .limit(limit)
            .offset(offset)
        )
        return [r[0] for r in result.all()]

    async def get_match_count(self, puuid: str) -> int:
        result = await self.session.execute(
            select(MatchParticipant)
            .where(MatchParticipant.puuid == puuid)
        )
        return len(result.scalars().all())


class MatchParticipantRepository(BaseRepository[MatchParticipant]):
    def __init__(self, session: AsyncSession):
        super().__init__(MatchParticipant, session)

    async def get_participant(
        self, match_id: str, puuid: str
    ) -> Optional[MatchParticipant]:
        result = await self.session.execute(
            select(MatchParticipant).where(
                and_(
                    MatchParticipant.match_id == match_id,
                    MatchParticipant.puuid == puuid
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_participants_by_match(self, match_id: str) -> List[MatchParticipant]:
        result = await self.session.execute(
            select(MatchParticipant).where(MatchParticipant.match_id == match_id)
        )
        return list(result.scalars().all())

    async def get_latest_summoner_id_by_puuid(self, puuid: str) -> Optional[str]:
        result = await self.session.execute(
            select(MatchParticipant.summoner_id)
            .where(
                and_(
                    MatchParticipant.puuid == puuid,
                    MatchParticipant.summoner_id.is_not(None),
                    MatchParticipant.summoner_id != "",
                )
            )
            .order_by(desc(MatchParticipant.id))
            .limit(1)
        )
        row = result.first()
        if inspect.isawaitable(row):
            row = await row
        if not row:
            return None
        value = row[0]
        if not isinstance(value, str):
            return None
        value = value.strip()
        return value or None

    async def get_participant_stats(
        self,
        puuid: str,
        champion_id: Optional[int] = None,
        role: Optional[str] = None,
        limit: int = 100
    ):
        query = select(MatchParticipant).where(MatchParticipant.puuid == puuid)
        if champion_id:
            query = query.where(MatchParticipant.champion_id == champion_id)
        if role:
            query = query.where(MatchParticipant.team_position == role)
        query = query.order_by(desc(MatchParticipant.id)).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def upsert_participants(
        self, match_id: str, participants: List[dict]
    ) -> List[MatchParticipant]:
        results = []
        for p in participants:
            existing = await self.get_participant(match_id, p["puuid"])
            if existing:
                for key, value in p.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                results.append(existing)
            else:
                participant = MatchParticipant(match_id=match_id, **p)
                self.session.add(participant)
                results.append(participant)
        await self.session.flush()
        return results


class MatchTimelineRepository(BaseRepository[MatchTimeline]):
    def __init__(self, session: AsyncSession):
        super().__init__(MatchTimeline, session)

    async def get_by_match_id(self, match_id: str) -> Optional[MatchTimeline]:
        result = await self.session.execute(
            select(MatchTimeline).where(MatchTimeline.match_id == match_id)
        )
        return result.scalar_one_or_none()

    async def upsert_timeline(
        self,
        match_id: str,
        timeline_json: dict,
        frame_interval: Optional[int] = None,
        fetched_region: Optional[str] = None,
    ) -> MatchTimeline:
        existing = await self.get_by_match_id(match_id)
        if existing:
            existing.timeline_json = timeline_json
            existing.frame_interval = frame_interval
            existing.fetched_region = fetched_region
            await self.session.flush()
            return existing

        timeline = MatchTimeline(
            match_id=match_id,
            timeline_json=timeline_json,
            frame_interval=frame_interval,
            fetched_region=fetched_region,
        )
        self.session.add(timeline)
        await self.session.flush()
        return timeline
