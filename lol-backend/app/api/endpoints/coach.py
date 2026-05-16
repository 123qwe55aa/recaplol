"""AI Coach API endpoints."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.models.coach import CoachReport
from app.repositories.coach import CoachReportRepository
from app.schemas.coach import (
    CoachChatRequest,
    CoachChatResponse,
    CoachGenerateRequest,
    CoachReportResponse,
)
from app.services.ai_provider import AIProvider, AIProviderError, get_ai_provider
from app.services.coach_context_builder import CoachContextBuilder
from app.services.coach_rule_engine import score_context

router = APIRouter(prefix="/coach", tags=["coach"])


def get_context_builder(db: AsyncSession = Depends(get_db)) -> CoachContextBuilder:
    return CoachContextBuilder(db)


def get_coach_report_repository(
    db: AsyncSession = Depends(get_db),
) -> CoachReportRepository:
    return CoachReportRepository(db)


def get_ai_provider_dependency() -> AIProvider:
    return get_ai_provider()


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


def _normalize_report(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    match_count = int(context.get("match_count") or 0)
    data_window = payload.get("data_window") or {}
    data_window.setdefault("match_count", match_count)
    data_window.setdefault("recent_match_ids", context.get("recent_match_ids") or [])
    data_window.setdefault("fingerprint", context.get("data_fingerprint"))
    data_window.setdefault("primary_role", context.get("primary_role"))
    data_window.setdefault("primary_champions", context.get("primary_champions") or [])

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
