from datetime import datetime
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patch_notes import PatchNoteAnnouncement
from app.repositories.base import BaseRepository


class PatchNoteAnnouncementRepository(BaseRepository[PatchNoteAnnouncement]):
    def __init__(self, session: AsyncSession):
        super().__init__(PatchNoteAnnouncement, session)

    async def get_latest(self) -> Optional[PatchNoteAnnouncement]:
        result = await self.session.execute(
            select(PatchNoteAnnouncement)
            .order_by(desc(PatchNoteAnnouncement.generated_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_url(self, url: str) -> Optional[PatchNoteAnnouncement]:
        result = await self.session.execute(
            select(PatchNoteAnnouncement).where(PatchNoteAnnouncement.url == url).limit(1)
        )
        return result.scalar_one_or_none()

    async def upsert_latest(self, payload: dict) -> PatchNoteAnnouncement:
        existing = await self.get_by_url(str(payload["url"]))
        if existing:
            existing.version = str(payload["version"])
            existing.title = str(payload["title"])
            existing.published_at = payload.get("published_at")
            existing.summary = str(payload["summary"])
            existing.overview = str(payload["overview"])
            existing.analysis_json = dict(payload["analysis"])
            existing.generated_at = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        record = PatchNoteAnnouncement(
            version=str(payload["version"]),
            title=str(payload["title"]),
            url=str(payload["url"]),
            published_at=payload.get("published_at"),
            summary=str(payload["summary"]),
            overview=str(payload["overview"]),
            analysis_json=dict(payload["analysis"]),
            generated_at=datetime.utcnow(),
        )
        return await self.create(record)
