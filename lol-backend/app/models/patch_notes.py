from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Index, JSON, String
from sqlalchemy.sql import func

from app.db.database import Base


class PatchNoteAnnouncement(Base):
    __tablename__ = "patch_note_announcements"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    version = Column(String(32), nullable=False)
    title = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False)
    published_at = Column(String(64), nullable=True)
    summary = Column(String, nullable=False)
    overview = Column(String, nullable=False)
    analysis_json = Column(JSON, nullable=False)
    generated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_patch_note_announcements_version", "version"),
        Index("ix_patch_note_announcements_generated_at", "generated_at"),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("generated_at", datetime.utcnow())
        super().__init__(**kwargs)
