"""Tests for match timeline recap analysis."""

from app.services.match_timeline_analyzer import build_match_recap


def test_build_match_recap_flags_early_deaths_and_resource_death():
    timeline = {
        "info": {
            "frameInterval": 60000,
            "frames": [
                {
                    "timestamp": 600000,
                    "participantFrames": {
                        "1": {
                            "participantId": 1,
                            "totalGold": 3200,
                            "xp": 4100,
                            "level": 7,
                            "minionsKilled": 68,
                            "jungleMinionsKilled": 0,
                        }
                    },
                    "events": [
                        {
                            "type": "CHAMPION_KILL",
                            "timestamp": 540000,
                            "victimId": 1,
                            "killerId": 4,
                            "assistingParticipantIds": [5],
                        }
                    ],
                },
                {
                    "timestamp": 840000,
                    "participantFrames": {
                        "1": {
                            "participantId": 1,
                            "totalGold": 4700,
                            "xp": 6200,
                            "level": 9,
                            "minionsKilled": 99,
                            "jungleMinionsKilled": 0,
                        }
                    },
                    "events": [
                        {
                            "type": "ELITE_MONSTER_KILL",
                            "timestamp": 600000,
                            "monsterType": "DRAGON",
                            "killerTeamId": 200,
                        }
                    ],
                },
            ],
        }
    }

    recap = build_match_recap(
        timeline=timeline,
        participant_id=1,
        participant_team_id=100,
        game_duration=1800,
    )

    assert recap["match_phase_summary"]["early_deaths"] == 1
    assert recap["timeline_stats"]["deaths"] == 1
    assert recap["timeline_stats"]["resource_deaths"] == 1
    assert recap["resource_windows"][0]["resource"] == "DRAGON"
    assert recap["resource_windows"][0]["player_died_before"] is True
    assert any(insight["type"] == "early_death" for insight in recap["insights"])
    assert any(insight["type"] == "resource_death" for insight in recap["insights"])


def test_build_match_recap_calculates_ten_minute_cs_and_gold():
    timeline = {
        "info": {
            "frameInterval": 60000,
            "frames": [
                {
                    "timestamp": 600000,
                    "participantFrames": {
                        "3": {
                            "participantId": 3,
                            "totalGold": 3550,
                            "xp": 4550,
                            "level": 8,
                            "minionsKilled": 74,
                            "jungleMinionsKilled": 3,
                        }
                    },
                    "events": [],
                }
            ],
        }
    }

    recap = build_match_recap(
        timeline=timeline,
        participant_id=3,
        participant_team_id=100,
        game_duration=1600,
    )

    assert recap["timeline_stats"]["gold_at_10"] == 3550
    assert recap["timeline_stats"]["cs_at_10"] == 77
    assert recap["timeline_stats"]["cs_per_min_at_10"] == 7.7
    assert recap["match_phase_summary"]["lane_phase_cs_per_min"] == 7.7
