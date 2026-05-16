"""Tests for deterministic coach rule scoring."""

from app.services.coach_rule_engine import build_fallback_report, score_context


def test_high_deaths_ranks_above_other_issues():
    context = {
        "match_count": 12,
        "averages": {
            "deaths": 8.4,
            "cs_per_minute": 4.8,
            "vision_score": 14.0,
        },
        "primary_champions": [
            {"champion_id": 103, "champion_name": "Ahri", "games": 10},
        ],
    }

    result = score_context(context)

    assert len(result["findings"]) <= 3
    assert result["findings"][0]["category"] == "deaths"
    assert result["findings"][0]["severity"] > result["findings"][1]["severity"]


def test_low_cs_per_minute_produces_cs_priority():
    context = {
        "match_count": 10,
        "averages": {"deaths": 4.0, "cs_per_minute": 4.9, "vision_score": 24.0},
        "primary_champions": [
            {"champion_id": 81, "champion_name": "Ezreal", "games": 5},
            {"champion_id": 22, "champion_name": "Ashe", "games": 5},
        ],
    }

    result = score_context(context)

    cs_priority = next(item for item in result["findings"] if item["category"] == "cs")
    assert "4.9" in cs_priority["evidence"]
    assert cs_priority["title"]


def test_low_vision_score_produces_vision_priority():
    context = {
        "match_count": 10,
        "averages": {"deaths": 4.0, "cs_per_minute": 7.2, "vision_score": 10.5},
        "primary_champions": [
            {"champion_id": 412, "champion_name": "Thresh", "games": 6},
            {"champion_id": 111, "champion_name": "Nautilus", "games": 4},
        ],
    }

    result = score_context(context)

    assert any(item["category"] == "vision" for item in result["findings"])


def test_narrow_champion_pool_produces_champion_pool_guidance():
    context = {
        "match_count": 8,
        "averages": {"deaths": 4.0, "cs_per_minute": 7.0, "vision_score": 25.0},
        "primary_champions": [
            {"champion_id": 238, "champion_name": "Zed", "games": 8},
        ],
    }

    result = score_context(context)

    pool_priority = next(
        item for item in result["findings"] if item["category"] == "champion_pool"
    )
    assert "Zed" in pool_priority["evidence"]
    assert "backup" in pool_priority["recommendation"].lower()


def test_fewer_than_five_matches_lowers_confidence():
    context = {
        "match_count": 3,
        "averages": {"deaths": 3.0, "cs_per_minute": 7.0, "vision_score": 25.0},
        "primary_champions": [
            {"champion_id": 99, "champion_name": "Lux", "games": 3},
        ],
    }

    result = score_context(context)
    report = build_fallback_report(context, result["findings"])

    assert result["confidence"] == "low"
    assert report["confidence"] == "low"
    assert report["follow_up_questions"]
    assert report["data_window"]["match_count"] == 3
