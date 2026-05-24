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
                        },
                        {
                            "type": "ITEM_PURCHASED",
                            "timestamp": 300000,
                            "participantId": 1,
                            "itemId": 1056,
                        },
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
    assert recap["key_events"]["items"][0] == {
        "type": "ITEM_PURCHASED",
        "timestamp": 300000,
        "minute": 5.0,
        "item_id": 1056,
        "before_id": None,
        "after_id": None,
    }
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


def test_build_match_recap_calculates_team_deltas_at_ten_and_fourteen():
    timeline = {
        "info": {
            "frames": [
                {
                    "timestamp": 600000,
                    "participantFrames": {
                        "1": {"participantId": 1, "totalGold": 3200, "xp": 4300, "level": 7, "minionsKilled": 68, "jungleMinionsKilled": 0},
                        "2": {"participantId": 2, "totalGold": 3100, "xp": 4000, "level": 7, "minionsKilled": 12, "jungleMinionsKilled": 48},
                        "3": {"participantId": 3, "totalGold": 3400, "xp": 4500, "level": 8, "minionsKilled": 72, "jungleMinionsKilled": 0},
                        "4": {"participantId": 4, "totalGold": 3000, "xp": 3600, "level": 6, "minionsKilled": 64, "jungleMinionsKilled": 0},
                        "5": {"participantId": 5, "totalGold": 2300, "xp": 3000, "level": 6, "minionsKilled": 14, "jungleMinionsKilled": 0},
                        "6": {"participantId": 6, "totalGold": 3000, "xp": 4000, "level": 7, "minionsKilled": 60, "jungleMinionsKilled": 0},
                        "7": {"participantId": 7, "totalGold": 3000, "xp": 3900, "level": 7, "minionsKilled": 10, "jungleMinionsKilled": 44},
                        "8": {"participantId": 8, "totalGold": 3300, "xp": 4300, "level": 8, "minionsKilled": 68, "jungleMinionsKilled": 0},
                        "9": {"participantId": 9, "totalGold": 2900, "xp": 3500, "level": 6, "minionsKilled": 59, "jungleMinionsKilled": 0},
                        "10": {"participantId": 10, "totalGold": 2200, "xp": 2900, "level": 6, "minionsKilled": 10, "jungleMinionsKilled": 0},
                    },
                    "events": [],
                },
                {
                    "timestamp": 840000,
                    "participantFrames": {
                        "1": {"participantId": 1, "totalGold": 4700, "xp": 6100, "level": 9, "minionsKilled": 103, "jungleMinionsKilled": 0},
                        "2": {"participantId": 2, "totalGold": 4550, "xp": 5850, "level": 9, "minionsKilled": 18, "jungleMinionsKilled": 76},
                        "3": {"participantId": 3, "totalGold": 5000, "xp": 6400, "level": 10, "minionsKilled": 111, "jungleMinionsKilled": 0},
                        "4": {"participantId": 4, "totalGold": 4300, "xp": 5050, "level": 8, "minionsKilled": 98, "jungleMinionsKilled": 0},
                        "5": {"participantId": 5, "totalGold": 3300, "xp": 4300, "level": 8, "minionsKilled": 20, "jungleMinionsKilled": 0},
                        "6": {"participantId": 6, "totalGold": 4300, "xp": 5700, "level": 9, "minionsKilled": 94, "jungleMinionsKilled": 0},
                        "7": {"participantId": 7, "totalGold": 4200, "xp": 5450, "level": 8, "minionsKilled": 16, "jungleMinionsKilled": 69},
                        "8": {"participantId": 8, "totalGold": 4600, "xp": 5900, "level": 9, "minionsKilled": 101, "jungleMinionsKilled": 0},
                        "9": {"participantId": 9, "totalGold": 4050, "xp": 4800, "level": 8, "minionsKilled": 91, "jungleMinionsKilled": 0},
                        "10": {"participantId": 10, "totalGold": 3100, "xp": 4100, "level": 7, "minionsKilled": 15, "jungleMinionsKilled": 0},
                    },
                    "events": [],
                },
            ],
        }
    }

    recap = build_match_recap(
        timeline=timeline,
        participant_id=3,
        participant_team_id=100,
        game_duration=1800,
        team_position="MIDDLE",
    )

    assert recap["timeline_stats"]["team_gold_delta_at_10"] == 600
    assert recap["timeline_stats"]["team_xp_delta_at_10"] == 800
    assert recap["timeline_stats"]["team_cs_delta_at_10"] == 27
    assert recap["timeline_stats"]["team_gold_delta_at_14"] == 1600
    assert recap["timeline_stats"]["team_xp_delta_at_14"] == 1750
    assert recap["timeline_stats"]["team_cs_delta_at_14"] == 40
    assert recap["match_phase_summary"]["team_gold_delta_at_10"] == 600


def test_build_match_recap_does_not_flag_support_low_cs():
    timeline = {
        "info": {
            "frames": [
                {
                    "timestamp": 600000,
                    "participantFrames": {
                        "5": {
                            "participantId": 5,
                            "totalGold": 2600,
                            "xp": 3200,
                            "level": 6,
                            "minionsKilled": 12,
                            "jungleMinionsKilled": 0,
                        }
                    },
                    "events": [],
                }
            ],
        }
    }

    recap = build_match_recap(
        timeline=timeline,
        participant_id=5,
        participant_team_id=100,
        game_duration=1800,
        team_position="UTILITY",
    )

    assert recap["timeline_stats"]["cs_per_min_at_10"] == 1.2
    assert recap["role_profile"]["role"] == "UTILITY"
    assert recap["role_profile"]["cs_is_primary"] is False
    assert not any(insight["type"] == "lane_cs" for insight in recap["insights"])


def test_build_match_recap_flags_laner_low_cs():
    timeline = {
        "info": {
            "frames": [
                {
                    "timestamp": 600000,
                    "participantFrames": {
                        "3": {
                            "participantId": 3,
                            "totalGold": 2900,
                            "xp": 3900,
                            "level": 7,
                            "minionsKilled": 43,
                            "jungleMinionsKilled": 0,
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
        game_duration=1800,
        team_position="MIDDLE",
    )

    assert recap["role_profile"]["cs_is_primary"] is True
    assert any(insight["type"] == "lane_cs" for insight in recap["insights"])
