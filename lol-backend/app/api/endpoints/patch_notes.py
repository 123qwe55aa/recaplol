"""League of Legends patch note endpoints."""

from fastapi import APIRouter, HTTPException

from app.schemas.patch_notes import PatchNoteAnnouncement
from app.services.patch_notes import PatchNotesError, PatchNotesService

router = APIRouter(prefix="/patch-notes", tags=["patch-notes"])

_patch_notes_service = PatchNotesService()


def get_patch_notes_service() -> PatchNotesService:
    return _patch_notes_service


@router.get("/latest", response_model=PatchNoteAnnouncement)
async def get_latest_patch_note():
    try:
        return await get_patch_notes_service().fetch_latest()
    except PatchNotesError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Patch notes unavailable: {exc}") from exc
