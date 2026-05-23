from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.endpoints import coach
from app.db.database import get_db
from app.models.coach import CoachReport


def create_test_app():
    app = FastAPI()
    app.include_router(coach.router)
    return app


class FakeBuilder:
    async def build_context(self, puuid: str, match_limit: int = 20):
        return {
            "player": {"puuid": puuid, "summoner_name": "CoachMe"},
            "recent_match_ids": ["NA1_1", "NA1_2"],
            "match_count": 2,
            "primary_role": "MID",
            "primary_champions": [{"champion_name": "Ahri", "games": 2}],
            "averages": {"deaths": 7.0, "cs_per_minute": 4.5, "vision_score": 12.0},
            "data_fingerprint": "fingerprint-1",
        }


class FakeProvider:
    model = "fake-provider"

    async def generate_report(self, context, findings):
        return {
            "summary": "Focus on deaths and income.",
            "confidence": "low",
            "data_window": {
                "match_count": context["match_count"],
                "recent_match_ids": context["recent_match_ids"],
                "fingerprint": context["data_fingerprint"],
            },
            "priorities": [
                {
                    "category": "deaths",
                    "title": "Reduce avoidable deaths",
                    "severity": "high",
                    "evidence": ["7.0 average deaths"],
                    "recommendation": "Reset earlier.",
                }
            ],
            "follow_up_questions": ["How do I die less?"],
        }

    async def answer_question(self, report, context, question):
        return {
            "answer": f"Answering: {question}",
            "used_evidence": ["7.0 average deaths"],
            "suggested_next_question": "Want a drill?",
        }


class FakePatchNotesService:
    async def fetch_latest(self):
        return {
            "version": "26.10",
            "title": "《英雄聯盟》26.10版本更新公告",
            "url": "https://www.leagueoflegends.com/zh-tw/news/game-updates/league-of-legends-patch-26-10-notes/",
            "published_at": "2026-05-12T18:00:00.000Z",
            "summary": "26.10版本登場，群魔繼續亂舞！",
            "overview": "我們針對近期第二賽季的改動做了一些後續調整。",
            "analysis": {
                "headline": "26.10 版本重點解析",
                "sections": ["版本概要", "英雄", "道具"],
                "takeaways": ["英雄：安比薩獲得上路和打野方向調整。"],
            },
        }


class FailingProvider(FakeProvider):
    async def generate_report(self, context, findings):
        raise RuntimeError("provider down")


class SummaryOnlyProvider(FakeProvider):
    async def generate_report(self, context, findings):
        return {"summary": "AI summary only"}


def make_report(stale=False):
    return CoachReport(
        id=1,
        puuid="test-puuid",
        report_json={
            "summary": "Cached report",
            "confidence": "medium",
            "data_window": {"match_count": 10},
            "priorities": [],
            "follow_up_questions": [],
        },
        context_json={"match_count": 10},
        data_fingerprint="fingerprint-1",
        model="fake-provider",
        status="completed",
        stale=stale,
        generated_at=datetime.utcnow(),
    )


@pytest.fixture
def app():
    test_app = create_test_app()
    test_app.dependency_overrides[get_db] = lambda: AsyncMock()
    test_app.dependency_overrides[coach.get_context_builder] = lambda: FakeBuilder()
    test_app.dependency_overrides[coach.get_ai_provider_dependency] = lambda: FakeProvider()
    test_app.dependency_overrides[coach.get_patch_notes_repository] = lambda: AsyncMock(
        upsert_latest=AsyncMock()
    )
    test_app.dependency_overrides[coach.get_patch_notes_service] = lambda: FakePatchNotesService()
    yield test_app
    test_app.dependency_overrides.clear()


def test_get_report_empty_state(app):
    repo = AsyncMock()
    repo.get_latest_by_puuid = AsyncMock(return_value=None)
    app.dependency_overrides[coach.get_coach_report_repository] = lambda: repo

    with TestClient(app) as client:
        response = client.get("/coach/players/test-puuid/report")

    assert response.status_code == 200
    assert response.json()["has_report"] is False
    assert response.json()["report"] is None


def test_generate_report_with_fake_provider(app):
    repo = AsyncMock()
    repo.get_by_fingerprint = AsyncMock(return_value=None)
    repo.upsert_report = AsyncMock(return_value=make_report())
    app.dependency_overrides[coach.get_coach_report_repository] = lambda: repo

    with TestClient(app) as client:
        response = client.post("/coach/players/test-puuid/report", json={"force": False})

    assert response.status_code == 200
    data = response.json()
    assert data["has_report"] is True
    assert data["report"]["summary"] == "Cached report"
    repo.upsert_report.assert_awaited_once()


def test_generate_report_cache_hit(app):
    repo = AsyncMock()
    repo.get_by_fingerprint = AsyncMock(return_value=make_report())
    app.dependency_overrides[coach.get_coach_report_repository] = lambda: repo

    with TestClient(app) as client:
        response = client.post("/coach/players/test-puuid/report", json={"force": False})

    assert response.status_code == 200
    assert response.json()["report"]["summary"] == "Cached report"
    assert not getattr(repo, "upsert_report").called


def test_generate_report_failure_returns_stale_latest(app):
    repo = AsyncMock()
    repo.get_by_fingerprint = AsyncMock(return_value=None)
    repo.get_latest_by_puuid = AsyncMock(return_value=make_report(stale=False))
    app.dependency_overrides[coach.get_coach_report_repository] = lambda: repo
    app.dependency_overrides[coach.get_ai_provider_dependency] = lambda: FailingProvider()

    with TestClient(app) as client:
        response = client.post("/coach/players/test-puuid/report", json={"force": True})

    assert response.status_code == 200
    assert response.json()["stale"] is True
    assert response.json()["report"]["summary"] == "Cached report"


def test_generate_report_uses_rule_findings_when_ai_omits_priorities(app):
    repo = AsyncMock()
    repo.get_by_fingerprint = AsyncMock(return_value=None)

    async def upsert_report(**kwargs):
        return CoachReport(
            id=2,
            puuid=kwargs["puuid"],
            report_json=kwargs["report_json"],
            context_json=kwargs["context_json"],
            data_fingerprint=kwargs["data_fingerprint"],
            model=kwargs["model"],
            status=kwargs["status"],
            stale=kwargs["stale"],
            generated_at=kwargs["generated_at"],
        )

    repo.upsert_report = AsyncMock(side_effect=upsert_report)
    app.dependency_overrides[coach.get_coach_report_repository] = lambda: repo
    app.dependency_overrides[coach.get_ai_provider_dependency] = lambda: SummaryOnlyProvider()

    with TestClient(app) as client:
        response = client.post("/coach/players/test-puuid/report", json={"force": True})

    assert response.status_code == 200
    assert response.json()["report"]["summary"] == "AI summary only"
    assert response.json()["report"]["priorities"]


def test_normalize_report_converts_object_summary_to_string():
    normalized = coach._normalize_report(
        {
            "summary": {"win_rate": 0.7, "status": "无段位数据"},
            "priorities": [],
        },
        {"match_count": 2, "data_fingerprint": "fingerprint-1"},
    )

    assert normalized["summary"] == "win_rate: 0.7；status: 无段位数据"


def test_normalize_report_accepts_minimax_report_shape():
    normalized = coach._normalize_report(
        {
            "report_summary": {"win_rate": "70%", "avg_cs_per_min": 4.51},
            "findings": [
                {
                    "category": "cs",
                    "title": "补刀效率有提升空间",
                    "severity": "中等",
                    "evidence": "场均4.51 CS/分钟",
                    "recommendation": "明确主力位置。",
                }
            ],
            "priorities": ["明确并稳定主力位置"],
            "positive_highlights": ["视野意识优秀"],
        },
        {"match_count": 20, "data_fingerprint": "fingerprint-1"},
    )

    assert normalized["summary"] == "win_rate: 70%；avg_cs_per_min: 4.51"
    assert normalized["priorities"][0]["title"] == "补刀效率有提升空间"
    assert normalized["priorities"][0]["evidence"] == ["场均4.51 CS/分钟"]
    assert normalized["notes"] == "视野意识优秀"


def test_normalize_report_converts_primary_champion_names_to_dicts():
    normalized = coach._normalize_report(
        {
            "summary": "先稳定主力位置。",
            "data_window": {
                "match_count": 20,
                "primary_champions": ["Ezreal", "Maokai"],
            },
            "priorities": [],
        },
        {"match_count": 20, "data_fingerprint": "fingerprint-1"},
    )

    assert normalized["data_window"]["primary_champions"] == [
        {"champion_name": "Ezreal"},
        {"champion_name": "Maokai"},
    ]


def test_normalize_report_includes_dashboard_context():
    normalized = coach._normalize_report(
        {
            "summary": "训练重点清晰。",
            "priorities": [],
        },
        {
            "match_count": 2,
            "data_fingerprint": "fingerprint-1",
            "win_rate": 0.5,
            "primary_role": "UTILITY",
            "averages": {
                "kills": 2.5,
                "deaths": 4.0,
                "assists": 12.0,
                "cs_per_minute": 1.2,
                "vision_score": 42.0,
            },
            "matches": [
                {
                    "match_id": "NA1_1",
                    "champion_name": "Soraka",
                    "role": "UTILITY",
                    "win": True,
                    "kills": 1,
                    "deaths": 3,
                    "assists": 18,
                    "cs": 24,
                    "vision_score": 58,
                    "game_duration": 1800,
                }
            ],
        },
    )

    assert normalized["dashboard"]["win_rate"] == 0.5
    assert normalized["dashboard"]["primary_role"] == "UTILITY"
    assert normalized["dashboard"]["averages"]["vision_score"] == 42.0
    assert normalized["recent_matches"][0]["champion_name"] == "Soraka"


def test_chat_uses_latest_report(app):
    repo = AsyncMock()
    repo.get_latest_by_puuid = AsyncMock(return_value=make_report())
    app.dependency_overrides[coach.get_coach_report_repository] = lambda: repo

    with TestClient(app) as client:
        response = client.post(
            "/coach/players/test-puuid/chat", json={"question": "What first?"}
        )

    assert response.status_code == 200
    assert response.json()["answer"] == "Answering: What first?"


def test_chat_backfills_latest_patch_note_when_report_context_missing_it(app):
    captured = {}

    class RecordingProvider(FakeProvider):
        async def answer_question(self, report, context, question):
            captured["context"] = context
            return await super().answer_question(report, context, question)

    patch_record = type(
        "Patch",
        (),
        {
            "version": "26.10",
            "title": "《英雄聯盟》26.10版本更新公告",
            "url": "https://www.leagueoflegends.com/zh-tw/news/game-updates/league-of-legends-patch-26-10-notes/",
            "published_at": "2026-05-12T18:00:00.000Z",
            "summary": "26.10版本登場，群魔繼續亂舞！",
            "overview": "我們針對近期第二賽季的改動做了一些後續調整。",
            "analysis_json": {
                "headline": "26.10 版本重點解析",
                "sections": ["版本概要", "英雄", "道具"],
                "takeaways": ["英雄：安比薩獲得上路和打野方向調整。"],
            },
        },
    )()

    repo = AsyncMock()
    repo.get_latest_by_puuid = AsyncMock(return_value=make_report())
    patch_repo = AsyncMock()
    patch_repo.get_latest = AsyncMock(return_value=patch_record)
    app.dependency_overrides[coach.get_coach_report_repository] = lambda: repo
    app.dependency_overrides[coach.get_patch_notes_repository] = lambda: patch_repo
    app.dependency_overrides[coach.get_ai_provider_dependency] = lambda: RecordingProvider()

    with TestClient(app) as client:
        response = client.post(
            "/coach/players/test-puuid/chat", json={"question": "这个版本增强了什么？"}
        )

    assert response.status_code == 200
    assert captured["context"]["patch_note"]["version"] == "26.10"
    assert (
        captured["context"]["patch_note"]["analysis"]["headline"]
        == "26.10 版本重點解析"
    )
