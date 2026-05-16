from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Index, JSON, String
from sqlalchemy.sql import func

from app.db.database import Base


class CoachReport(Base):
    __tablename__ = "coach_reports"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    puuid = Column(String(78), nullable=False)
    report_json = Column(JSON, nullable=False)
    context_json = Column(JSON, nullable=False)
    data_fingerprint = Column(String(128), nullable=False)
    model = Column(String(128), nullable=True)
    status = Column(String(32), default="completed", nullable=False)
    error_message = Column(String, nullable=True)
    stale = Column(Boolean, default=False, nullable=False)
    generated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_coach_reports_puuid", "puuid"),
        Index("ix_coach_reports_data_fingerprint", "data_fingerprint"),
        Index("ix_coach_reports_generated_at", "generated_at"),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("status", "completed")
        kwargs.setdefault("stale", False)
        kwargs.setdefault("generated_at", datetime.utcnow())
        super().__init__(**kwargs)
