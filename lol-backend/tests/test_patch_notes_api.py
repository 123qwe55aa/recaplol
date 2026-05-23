"""Tests for patch notes API endpoints."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.endpoints import patch_notes


def test_get_latest_patch_note_returns_service_payload(monkeypatch):
    async def fake_fetch_latest():
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

    monkeypatch.setattr(patch_notes.get_patch_notes_service(), "fetch_latest", fake_fetch_latest)

    app = FastAPI()
    app.include_router(patch_notes.router)

    with TestClient(app) as client:
        response = client.get("/patch-notes/latest")

    assert response.status_code == 200
    assert response.json()["version"] == "26.10"
    assert response.json()["analysis"]["sections"] == ["版本概要", "英雄", "道具"]
