from datetime import datetime
from typing import Optional

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coach import CoachReport
from app.repositories.base import BaseRepository


class CoachReportRepository(BaseRepository[CoachReport]):
    def __init__(self, session: AsyncSession):
        super().__init__(CoachReport, session)

    async def get_latest_by_puuid(self, puuid: str) -> Optional[CoachReport]:
        result = await self.session.execute(
            select(CoachReport)
            .where(CoachReport.puuid == puuid)
            .order_by(desc(CoachReport.generated_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_fingerprint(
        self, puuid: str, fingerprint: str
    ) -> Optional[CoachReport]:
        result = await self.session.execute(
            select(CoachReport).where(
                and_(
                    CoachReport.puuid == puuid,
                    CoachReport.data_fingerprint == fingerprint,
                )
            )
        )
        return result.scalar_one_or_none()

    async def upsert_report(
        self,
        puuid: str,
        data_fingerprint: str,
        report_json: dict,
        context_json: dict,
        model: Optional[str] = None,
        status: str = "completed",
        error_message: Optional[str] = None,
        stale: bool = False,
        generated_at: Optional[datetime] = None,
    ) -> CoachReport:
        existing = await self.get_by_fingerprint(puuid, data_fingerprint)
        if existing:
            existing.report_json = report_json
            existing.context_json = context_json
            existing.model = model
            existing.status = status
            existing.error_message = error_message
            existing.stale = stale
            existing.generated_at = generated_at or datetime.utcnow()
            existing.updated_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        report = CoachReport(
            puuid=puuid,
            report_json=report_json,
            context_json=context_json,
            data_fingerprint=data_fingerprint,
            model=model,
            status=status,
            error_message=error_message,
            stale=stale,
            generated_at=generated_at or datetime.utcnow(),
        )
        return await self.create(report)
