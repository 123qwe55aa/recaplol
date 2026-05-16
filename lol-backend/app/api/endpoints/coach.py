"""AI Coach API endpoints."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.models.coach import CoachReport
from app.repositories.coach import CoachMatchRecapRepository, CoachReportRepository
from app.repositories.match import (
    MatchParticipantRepository,
    MatchRepository,
    MatchTimelineRepository,
)
from app.schemas.coach import (
    CoachChatRequest,
    CoachChatResponse,
    CoachGenerateRequest,
    CoachMatchRecapPayload,
    CoachMatchRecapResponse,
    CoachReportResponse,
)
from app.services.ai_provider import AIProvider, AIProviderError, get_ai_provider
from app.services.coach_context_builder import CoachContextBuilder
from app.services.coach_rule_engine import score_context
from app.services.match_timeline_analyzer import build_match_recap

router = APIRouter(prefix="/coach", tags=["coach"])


def get_context_builder(db: AsyncSession = Depends(get_db)) -> CoachContextBuilder:
    return CoachContextBuilder(db)


def get_coach_report_repository(
    db: AsyncSession = Depends(get_db),
) -> CoachReportRepository:
    return CoachReportRepository(db)


def get_match_recap_repository(
    db: AsyncSession = Depends(get_db),
) -> CoachMatchRecapRepository:
    return CoachMatchRecapRepository(db)


def get_ai_provider_dependency() -> AIProvider:
    return get_ai_provider()


def get_match_timeline_repository(
    db: AsyncSession = Depends(get_db),
) -> MatchTimelineRepository:
    return MatchTimelineRepository(db)


@router.get("/players/{puuid}/report", response_model=CoachReportResponse)
async def get_latest_report(
    puuid: str,
    repo: CoachReportRepository = Depends(get_coach_report_repository),
):
    report = await repo.get_latest_by_puuid(puuid)
    if not report:
        return CoachReportResponse(
            puuid=puuid,
            has_report=False,
            report=None,
            stale=False,
            status="empty",
        )
    return _report_response(report)


@router.post("/players/{puuid}/report", response_model=CoachReportResponse)
async def generate_report(
    puuid: str,
    request: CoachGenerateRequest | None = None,
    builder: CoachContextBuilder = Depends(get_context_builder),
    repo: CoachReportRepository = Depends(get_coach_report_repository),
    provider: AIProvider = Depends(get_ai_provider_dependency),
):
    request = request or CoachGenerateRequest()
    match_limit = request.match_limit or settings.coach_default_match_limit
    context = await builder.build_context(puuid, match_limit=match_limit)
    fingerprint = context.get("data_fingerprint")
    if not fingerprint:
        raise HTTPException(status_code=500, detail="Coach context missing fingerprint")

    if not request.force:
        cached = await repo.get_by_fingerprint(puuid, fingerprint)
        if cached:
            return _report_response(cached)

    findings_result = score_context(context)
    findings = findings_result.get("findings", [])

    try:
        report_payload = await provider.generate_report(context, findings)
    except Exception as exc:
        latest = await repo.get_latest_by_puuid(puuid)
        if latest:
            return _report_response(latest, stale=True, error_message=str(exc))
        raise HTTPException(status_code=503, detail=f"AI coach unavailable: {exc}")

    if not (report_payload.get("priorities") or report_payload.get("findings")):
        report_payload = {**report_payload, "findings": findings}

    normalized = _normalize_report(report_payload, context)
    saved = await repo.upsert_report(
        puuid=puuid,
        data_fingerprint=fingerprint,
        report_json=normalized,
        context_json=context,
        model=getattr(provider, "model", None),
        status="completed",
        stale=False,
        generated_at=datetime.utcnow(),
    )
    return _report_response(saved)


@router.post("/players/{puuid}/chat", response_model=CoachChatResponse)
async def chat_about_report(
    puuid: str,
    request: CoachChatRequest,
    repo: CoachReportRepository = Depends(get_coach_report_repository),
    provider: AIProvider = Depends(get_ai_provider_dependency),
):
    report = await repo.get_latest_by_puuid(puuid)
    if not report:
        raise HTTPException(status_code=404, detail="No coach report found")

    try:
        answer = await provider.answer_question(
            report=report.report_json,
            context=report.context_json,
            question=request.question,
        )
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI coach unavailable: {exc}")

    return CoachChatResponse(
        answer=str(answer.get("answer", "")),
        model=getattr(provider, "model", None),
        report_id=report.id,
        cited_priorities=list(answer.get("cited_priorities") or []),
        used_evidence=list(answer.get("used_evidence") or []),
        suggested_next_question=answer.get("suggested_next_question"),
    )


@router.post("/matches/{match_id}/recap/{puuid}", response_model=CoachMatchRecapResponse)
async def generate_match_ai_recap(
    match_id: str,
    puuid: str,
    db: AsyncSession = Depends(get_db),
    timeline_repo: MatchTimelineRepository = Depends(get_match_timeline_repository),
    recap_repo: CoachMatchRecapRepository = Depends(get_match_recap_repository),
    provider: AIProvider = Depends(get_ai_provider_dependency),
):
    match_repo = MatchRepository(db)
    participant_repo = MatchParticipantRepository(db)
    match = await match_repo.get_by_match_id(match_id)
    if not match:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    participant = await participant_repo.get_participant(match_id, puuid)
    if not participant:
        raise HTTPException(status_code=404, detail=f"Participant {puuid} not found")

    timeline = await timeline_repo.get_by_match_id(match_id)
    if not timeline:
        raise HTTPException(status_code=404, detail=f"Timeline {match_id} not found")

    participant_id = _participant_id_for_puuid(timeline.timeline_json, puuid)
    if participant_id is None:
        raise HTTPException(status_code=404, detail=f"Timeline participant {puuid} not found")

    deterministic_recap = build_match_recap(
        timeline=timeline.timeline_json,
        participant_id=participant_id,
        participant_team_id=participant.team_id,
        game_duration=match.game_duration,
        team_position=participant.team_position,
        individual_position=getattr(participant, "individual_position", None),
    )
    role_profile = deterministic_recap["role_profile"]
    match_context = {
        "match_id": match_id,
        "result": _participant_result(match, participant),
        "game_duration": match.game_duration,
        "role_profile": role_profile,
        "participant": {
            "puuid": puuid,
            "participant_id": participant_id,
            "team_id": participant.team_id,
            "champion_name": participant.champion_name,
            "team_position": participant.team_position,
            "individual_position": getattr(participant, "individual_position", None),
            "kills": participant.kills,
            "deaths": participant.deaths,
            "assists": participant.assists,
            "gold_earned": participant.gold_earned,
            "cs": (participant.total_minions_killed or 0)
            + (participant.neutral_minions_killed or 0),
            "vision_score": participant.vision_score,
        },
    }
    fingerprint = _match_recap_fingerprint(
        match_context=match_context,
        timeline_recap=deterministic_recap,
    )

    cached = await recap_repo.get_by_fingerprint(match_id, puuid, fingerprint)
    if cached:
        return _match_recap_response(cached)

    try:
        ai_payload = await provider.generate_match_recap(
            match_context=match_context,
            timeline_recap=deterministic_recap,
        )
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI match recap unavailable: {exc}")

    saved = await recap_repo.upsert_recap(
        match_id=match_id,
        puuid=puuid,
        data_fingerprint=fingerprint,
        recap_json=ai_payload,
        timeline_stats=deterministic_recap["timeline_stats"],
        deterministic_insights=deterministic_recap["insights"],
        context_json=match_context,
        model=getattr(provider, "model", None),
    )
    return _match_recap_response(saved)


@router.get("/matches/{match_id}/recap/{puuid}", response_model=CoachMatchRecapResponse)
async def get_cached_match_ai_recap(
    match_id: str,
    puuid: str,
    recap_repo: CoachMatchRecapRepository = Depends(get_match_recap_repository),
):
    cached = await recap_repo.get_latest_by_match_player(match_id, puuid)
    if not cached:
        raise HTTPException(status_code=404, detail=f"AI recap {match_id} not found")
    return _match_recap_response(cached)


def _report_response(
    report: CoachReport, stale: bool | None = None, error_message: str | None = None
) -> CoachReportResponse:
    return CoachReportResponse(
        id=report.id,
        puuid=report.puuid,
        has_report=True,
        report=_normalize_report(report.report_json, report.context_json),
        data_fingerprint=report.data_fingerprint,
        model=report.model,
        status=report.status,
        error_message=error_message or report.error_message,
        stale=report.stale if stale is None else stale,
        generated_at=report.generated_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def _match_recap_response(recap: Any) -> CoachMatchRecapResponse:
    return CoachMatchRecapResponse(
        match_id=recap.match_id,
        puuid=recap.puuid,
        model=getattr(recap, "model", None),
        timeline_stats=dict(getattr(recap, "timeline_stats", None) or {}),
        deterministic_insights=list(getattr(recap, "deterministic_insights", None) or []),
        recap=CoachMatchRecapPayload.model_validate(recap.recap_json),
    )


def _match_recap_fingerprint(match_context: dict[str, Any], timeline_recap: dict[str, Any]) -> str:
    payload = {
        "match_context": match_context,
        "timeline_stats": timeline_recap.get("timeline_stats"),
        "deterministic_insights": timeline_recap.get("insights"),
        "role_profile": timeline_recap.get("role_profile"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _participant_id_for_puuid(timeline_json: dict[str, Any], puuid: str) -> int | None:
    info = timeline_json.get("info") or {}
    for participant in info.get("participants") or []:
        if participant.get("puuid") == puuid:
            participant_id = participant.get("participantId")
            return int(participant_id) if participant_id is not None else None

    metadata_participants = (timeline_json.get("metadata") or {}).get("participants") or []
    for index, participant_puuid in enumerate(metadata_participants, start=1):
        if participant_puuid == puuid:
            return index
    return None


def _participant_result(match: Any, participant: Any) -> str:
    if (match.game_duration or 0) > 0 and match.game_duration <= 300:
        return "remake"
    if match.blue_team_win is None or participant.team_id is None:
        return "unknown"
    blue_win = bool(match.blue_team_win)
    participant_win = blue_win if participant.team_id == 100 else not blue_win
    return "win" if participant_win else "loss"


def _normalize_report(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    match_count = int(context.get("match_count") or 0)
    data_window = payload.get("data_window") or {}
    data_window.setdefault("match_count", match_count)
    data_window.setdefault("recent_match_ids", context.get("recent_match_ids") or [])
    data_window.setdefault("fingerprint", context.get("data_fingerprint"))
    data_window.setdefault("primary_role", context.get("primary_role"))
    data_window.setdefault("primary_champions", context.get("primary_champions") or [])
    data_window["primary_champions"] = _normalize_primary_champions(
        data_window.get("primary_champions")
    )

    priority_items = payload.get("priorities") or []
    if not any(isinstance(priority, dict) for priority in priority_items):
        priority_items = payload.get("findings") or priority_items

    priorities = []
    for priority in priority_items:
        priorities.append(_normalize_priority(priority))

    notes = payload.get("notes")
    if notes is None:
        notes = payload.get("positive_highlights")

    return {
        "summary": _coerce_optional_text(
            payload.get("summary") or payload.get("report_summary"),
            "No coach summary is available yet.",
        ),
        "confidence": payload.get("confidence") or "medium",
        "generated_at": payload.get("generated_at"),
        "data_window": data_window,
        "priorities": priorities[:3],
        "notes": _coerce_optional_text(notes),
        "follow_up_questions": list(payload.get("follow_up_questions") or []),
    }


def _normalize_priority(priority: Any) -> dict[str, Any]:
    if not isinstance(priority, dict):
        title = _coerce_optional_text(priority, "Coaching priority")
        return {
            "area": None,
            "category": None,
            "title": title,
            "severity": "medium",
            "problem": None,
            "impact": None,
            "evidence": [],
            "recommendation": title,
            "rationale": None,
            "actions": [title],
            "action_items": [title],
            "opgg_reference": None,
        }

    evidence = priority.get("evidence") or []
    if isinstance(evidence, str):
        evidence = [evidence]

    severity = priority.get("severity", "medium")
    if isinstance(severity, (int, float)):
        if severity >= 0.7:
            severity = "high"
        elif severity >= 0.4:
            severity = "medium"
        else:
            severity = "low"

    recommendation = priority.get("recommendation") or priority.get("rationale")
    actions = priority.get("actions") or priority.get("action_items") or []
    if isinstance(actions, str):
        actions = [actions]
    if not actions and recommendation:
        actions = [recommendation]

    return {
        "area": priority.get("area"),
        "category": priority.get("category"),
        "title": priority.get("title") or priority.get("category") or "Coaching priority",
        "severity": str(severity),
        "problem": priority.get("problem"),
        "impact": priority.get("impact"),
        "evidence": list(evidence),
        "recommendation": recommendation,
        "rationale": priority.get("rationale"),
        "actions": list(actions),
        "action_items": list(actions),
        "opgg_reference": priority.get("opgg_reference"),
    }


def _normalize_primary_champions(value: Any) -> list[dict[str, Any]]:
    champions = value or []
    if not isinstance(champions, list):
        champions = [champions]

    normalized = []
    for champion in champions:
        if isinstance(champion, dict):
            normalized.append(champion)
        elif champion is not None:
            normalized.append({"champion_name": str(champion)})
    return normalized


def _coerce_optional_text(value: Any, default: str | None = None) -> str | None:
    if value is None or value == "":
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "；".join(f"{key}: {item}" for key, item in value.items())
    if isinstance(value, list):
        return "；".join(str(item) for item in value)
    return json.dumps(value, ensure_ascii=False)
