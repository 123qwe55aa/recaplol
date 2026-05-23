"""Schemas for League of Legends patch notes."""

from pydantic import BaseModel, Field, HttpUrl


class PatchNoteAnalysis(BaseModel):
    headline: str
    sections: list[str] = Field(default_factory=list)
    takeaways: list[str] = Field(default_factory=list)


class PatchNoteAnnouncement(BaseModel):
    version: str
    title: str
    url: HttpUrl
    published_at: str | None = None
    summary: str
    overview: str
    analysis: PatchNoteAnalysis
