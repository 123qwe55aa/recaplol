"""Tests for match recap API endpoints."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.endpoints import match


@pytest.fixture(autouse=True)
def reset_overrides():
    yield


class FakeTimelineRepository:
    def __init__(self, timeline=None):
        self.timeline = timeline
        self.saved = None

    async def get_by_match_id(self, match_id):
        return self.timeline

    async def upsert_timeline(self, **kwargs):
        self.saved = kwargs
        self.timeline = type(
            "Timeline",
            (),
            {
                "match_id": kwargs["match_id"],
                "frame_interval": kwargs["frame_interval"],
                "timeline_json": kwargs["timeline_json"],
                "fetched_region": kwargs.get("fetched_region"),
            },
        )()
        return self.timeline


class FakeRiotClient:
    def __init__(self, timeline):
        self.timeline = timeline

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def get_match_timeline_with_region(self, match_id, region_base):
        return self.timeline


@pytest.mark.asyncio
async def test_fetch_match_timeline_stores_riot_timeline():
    app = FastAPI()
    app.include_router(match.router)
    repo = FakeTimelineRepository()
    riot_timeline = {
        "metadata": {"matchId": "NA1_123"},
        "info": {"frameInterval": 60000, "frames": []},
    }
    app.dependency_overrides[match.get_match_timeline_repository] = lambda: repo
    app.dependency_overrides[match.get_riot_client_dependency] = lambda: FakeRiotClient(riot_timeline)

    with TestClient(app) as client:
        response = client.post("/matches/timeline/fetch/NA1_123")

    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == "NA1_123"
    assert data["frame_interval"] == 60000
    assert repo.saved["timeline_json"] == riot_timeline


@pytest.mark.asyncio
async def test_get_match_recap_returns_timeline_insights(monkeypatch):
    timeline = type(
        "Timeline",
        (),
        {
            "timeline_json": {
                "info": {
                    "frameInterval": 60000,
                    "frames": [
                        {
                            "timestamp": 600000,
                            "participantFrames": {
                                "1": {
                                    "participantId": 1,
                                    "totalGold": 3000,
                                    "xp": 4000,
                                    "level": 7,
                                    "minionsKilled": 50,
                                    "jungleMinionsKilled": 0,
                                }
                            },
                            "events": [
                                {
                                    "type": "CHAMPION_KILL",
                                    "timestamp": 540000,
                                    "victimId": 1,
                                    "killerId": 4,
                                },
                                {
                                    "type": "ELITE_MONSTER_KILL",
                                    "timestamp": 600000,
                                    "monsterType": "DRAGON",
                                    "killerTeamId": 200,
                                },
                            ],
                        }
                    ],
                    "participants": [{"participantId": 1, "puuid": "player-puuid"}],
                }
            }
        },
    )()
    fake_match = type("Match", (), {"match_id": "NA1_123", "game_duration": 1800})()
    fake_participant = type(
        "Participant",
        (),
        {
            "puuid": "player-puuid",
            "team_id": 100,
            "champion_name": "Ahri",
            "team_position": "MID",
        },
    )()

    class FakeMatchRepository:
        def __init__(self, db):
            pass

        async def get_by_match_id(self, match_id):
            return fake_match

    class FakeParticipantRepository:
        def __init__(self, db):
            pass

        async def get_participant(self, match_id, puuid):
            return fake_participant

    monkeypatch.setattr(match, "MatchRepository", FakeMatchRepository)
    monkeypatch.setattr(match, "MatchParticipantRepository", FakeParticipantRepository)

    response = await match.get_match_recap(
        match_id="NA1_123",
        puuid="player-puuid",
        db=object(),
        timeline_repo=FakeTimelineRepository(timeline),
    )

    data = response.model_dump()
    assert data["match_id"] == "NA1_123"
    assert data["participant"]["champion_name"] == "Ahri"
    assert data["timeline_stats"]["early_deaths"] == 1
    assert data["timeline_stats"]["resource_deaths"] == 1
    assert data["insights"][0]["title"]
