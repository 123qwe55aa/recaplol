from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from datetime import datetime

from app.models.match import Match, MatchParticipant
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
        # Subquery: get distinct match_ids with their most recent participant id
        subq = (
            select(
                MatchParticipant.match_id,
                func.max(MatchParticipant.id).label("max_id"),
            )
            .where(MatchParticipant.puuid == puuid)
            .group_by(MatchParticipant.match_id)
            .subquery()
        )
        result = await self.session.execute(
            select(subq.c.match_id)
            .order_by(desc(subq.c.max_id))
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
