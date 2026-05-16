"""Tests for AI match recap endpoint."""

import pytest

from app.api.endpoints import coach


class FakeAIProvider:
    model = "fake-match-ai"
    seen_match_context = None
    seen_timeline_recap = None

    async def generate_match_recap(self, match_context, timeline_recap):
        self.seen_match_context = match_context
        self.seen_timeline_recap = timeline_recap
        return {
            "summary": "这局阿狸的问题集中在小龙前阵亡。",
            "turning_points": [
                {
                    "title": "小龙前死亡",
                    "timestamp": 540000,
                    "explanation": "死亡发生在小龙前 60 秒，直接影响资源人数。",
                }
            ],
            "strengths": ["对线补刀还能接受"],
            "mistakes": ["资源前没有先处理视野和站位"],
            "next_game_focus": "小龙前 90 秒不要单独过河。",
            "follow_up_questions": ["这波小龙前应该怎么站位？"],
        }


class FakeTimelineRepository:
    async def get_by_match_id(self, match_id):
        return type(
            "Timeline",
            (),
            {
                "timeline_json": {
                    "info": {
                        "participants": [{"participantId": 1, "puuid": "player-puuid"}],
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
                    }
                }
            },
        )()


@pytest.mark.asyncio
async def test_generate_ai_match_recap(monkeypatch):
    fake_match = type("Match", (), {"match_id": "NA1_123", "game_duration": 1800, "blue_team_win": 0})()
    fake_participant = type(
        "Participant",
        (),
        {
            "puuid": "player-puuid",
            "team_id": 100,
            "champion_name": "Ahri",
            "team_position": "MID",
            "kills": 3,
            "deaths": 5,
            "assists": 7,
            "gold_earned": 9000,
            "total_minions_killed": 160,
            "neutral_minions_killed": 0,
            "vision_score": 18,
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

    monkeypatch.setattr(coach, "MatchRepository", FakeMatchRepository)
    monkeypatch.setattr(coach, "MatchParticipantRepository", FakeParticipantRepository)

    provider = FakeAIProvider()
    response = await coach.generate_match_ai_recap(
        match_id="NA1_123",
        puuid="player-puuid",
        db=object(),
        timeline_repo=FakeTimelineRepository(),
        provider=provider,
    )

    data = response.model_dump()
    assert data["match_id"] == "NA1_123"
    assert data["model"] == "fake-match-ai"
    assert data["recap"]["summary"] == "这局阿狸的问题集中在小龙前阵亡。"
    assert data["recap"]["next_game_focus"] == "小龙前 90 秒不要单独过河。"
    assert provider.seen_match_context["role_profile"]["role"] == "MIDDLE"
    assert provider.seen_match_context["role_profile"]["cs_is_primary"] is True
    assert provider.seen_timeline_recap["role_profile"]["role"] == "MIDDLE"
