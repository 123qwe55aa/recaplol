"""League of Legends patch note endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.patch_notes import PatchNoteAnnouncement
from app.db.database import get_db
from app.repositories.patch_notes import PatchNoteAnnouncementRepository
from app.services.patch_notes import PatchNotesError, PatchNotesService

router = APIRouter(prefix="/patch-notes", tags=["patch-notes"])

_patch_notes_service = PatchNotesService()


def get_patch_notes_service() -> PatchNotesService:
    return _patch_notes_service


def get_patch_notes_repository(
    db: AsyncSession = Depends(get_db),
) -> PatchNoteAnnouncementRepository:
    return PatchNoteAnnouncementRepository(db)


@router.get("/latest", response_model=PatchNoteAnnouncement)
async def get_latest_patch_note(
    repo: PatchNoteAnnouncementRepository = Depends(get_patch_notes_repository),
):
    try:
        payload = await get_patch_notes_service().fetch_latest()
        saved = await repo.upsert_latest(payload)
        return {
            "version": saved.version,
            "title": saved.title,
            "url": saved.url,
            "published_at": saved.published_at,
            "summary": saved.summary,
            "overview": saved.overview,
            "analysis": saved.analysis_json,
        }
    except PatchNotesError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Patch notes unavailable: {exc}") from exc
