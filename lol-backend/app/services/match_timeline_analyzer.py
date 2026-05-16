"""Deterministic timeline recap analysis for League of Legends matches."""

from __future__ import annotations

from typing import Any


RESOURCE_TYPES = {"DRAGON", "RIFTHERALD", "BARON_NASHOR", "HORDE"}
RESOURCE_WINDOW_MS = 90_000
EARLY_GAME_MS = 10 * 60 * 1000
LANE_PHASE_MS = 14 * 60 * 1000

ROLE_ALIASES = {
    "MID": "MIDDLE",
    "ADC": "BOTTOM",
    "SUPPORT": "UTILITY",
}

ROLE_PROFILES = {
    "TOP": {
        "primary_focus": ["lane_trading", "cs", "side_lane_pressure", "deaths"],
        "avoid_as_primary": [],
        "cs_is_primary": True,
    },
    "JUNGLE": {
        "primary_focus": ["objective_setup", "gank_timing", "farm_pathing", "deaths"],
        "avoid_as_primary": ["lane_cs"],
        "cs_is_primary": False,
    },
    "MIDDLE": {
        "primary_focus": ["lane_trading", "cs", "roam_timing", "deaths"],
        "avoid_as_primary": [],
        "cs_is_primary": True,
    },
    "BOTTOM": {
        "primary_focus": ["cs", "damage_uptime", "positioning", "deaths"],
        "avoid_as_primary": [],
        "cs_is_primary": True,
    },
    "UTILITY": {
        "primary_focus": ["vision_control", "assist_participation", "objective_setup", "deaths"],
        "avoid_as_primary": ["cs", "lane_cs"],
        "cs_is_primary": False,
    },
}

DEFAULT_ROLE_PROFILE = {
    "primary_focus": ["deaths", "objective_setup", "teamfight_impact"],
    "avoid_as_primary": [],
    "cs_is_primary": False,
}


def build_match_recap(
    timeline: dict[str, Any],
    participant_id: int,
    participant_team_id: int | None,
    game_duration: int | None = None,
    team_position: str | None = None,
    individual_position: str | None = None,
) -> dict[str, Any]:
    """Build a player-focused recap from a Riot match timeline payload."""
    role_profile = build_role_profile(team_position, individual_position)
    frames = list((timeline.get("info") or {}).get("frames") or [])
    events = _timeline_events(frames)
    participant_frames = _participant_frames(frames, participant_id)
    death_events = [
        event for event in events
        if event.get("type") == "CHAMPION_KILL"
        and event.get("victimId") == participant_id
    ]
    kill_events = [
        event for event in events
        if event.get("type") == "CHAMPION_KILL"
        and event.get("killerId") == participant_id
    ]
    assist_events = [
        event for event in events
        if event.get("type") == "CHAMPION_KILL"
        and participant_id in (event.get("assistingParticipantIds") or [])
    ]
    resource_events = [
        event for event in events
        if event.get("type") == "ELITE_MONSTER_KILL"
        and event.get("monsterType") in RESOURCE_TYPES
    ]

    resource_windows = _build_resource_windows(
        resource_events=resource_events,
        death_events=death_events,
        participant_team_id=participant_team_id,
    )
    frame_10 = _closest_frame_at_or_before(participant_frames, EARLY_GAME_MS)
    frame_14 = _closest_frame_at_or_before(participant_frames, LANE_PHASE_MS)
    cs_at_10 = _frame_cs(frame_10)
    cs_at_14 = _frame_cs(frame_14)
    early_deaths = sum(1 for event in death_events if _timestamp(event) <= EARLY_GAME_MS)
    resource_deaths = sum(1 for window in resource_windows if window["player_died_before"])

    timeline_stats = {
        "kills": len(kill_events),
        "deaths": len(death_events),
        "assists": len(assist_events),
        "early_deaths": early_deaths,
        "resource_deaths": resource_deaths,
        "gold_at_10": _frame_value(frame_10, "totalGold"),
        "xp_at_10": _frame_value(frame_10, "xp"),
        "level_at_10": _frame_value(frame_10, "level"),
        "cs_at_10": cs_at_10,
        "cs_per_min_at_10": round(cs_at_10 / 10, 2) if cs_at_10 is not None else None,
        "gold_at_14": _frame_value(frame_14, "totalGold"),
        "cs_at_14": cs_at_14,
        "cs_per_min_at_14": round(cs_at_14 / 14, 2) if cs_at_14 is not None else None,
    }

    insights = _build_insights(
        early_deaths=early_deaths,
        resource_deaths=resource_deaths,
        cs_per_min_at_10=timeline_stats["cs_per_min_at_10"],
        role_profile=role_profile,
    )

    return {
        "participant_id": participant_id,
        "participant_team_id": participant_team_id,
        "role_profile": role_profile,
        "game_duration": game_duration,
        "timeline_stats": timeline_stats,
        "match_phase_summary": {
            "early_deaths": early_deaths,
            "lane_phase_cs_per_min": timeline_stats["cs_per_min_at_10"],
            "mid_game_resource_deaths": resource_deaths,
        },
        "resource_windows": resource_windows,
        "key_events": {
            "deaths": [_event_summary(event) for event in death_events],
            "kills": [_event_summary(event) for event in kill_events],
            "assists": [_event_summary(event) for event in assist_events],
            "objectives": [_objective_summary(event, participant_team_id) for event in resource_events],
        },
        "insights": insights,
    }


def build_role_profile(
    team_position: str | None,
    individual_position: str | None = None,
) -> dict[str, Any]:
    role = _normalize_role(team_position) or _normalize_role(individual_position) or "UNKNOWN"
    profile = ROLE_PROFILES.get(role, DEFAULT_ROLE_PROFILE)
    return {
        "role": role,
        "team_position": team_position,
        "individual_position": individual_position,
        "primary_focus": list(profile["primary_focus"]),
        "avoid_as_primary": list(profile["avoid_as_primary"]),
        "cs_is_primary": bool(profile["cs_is_primary"]),
    }


def _normalize_role(role: str | None) -> str | None:
    if not role:
        return None
    normalized = role.upper()
    return ROLE_ALIASES.get(normalized, normalized)


def _timeline_events(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for frame in frames:
        events.extend(frame.get("events") or [])
    return sorted(events, key=_timestamp)


def _participant_frames(
    frames: list[dict[str, Any]],
    participant_id: int,
) -> list[dict[str, Any]]:
    output = []
    participant_key = str(participant_id)
    for frame in frames:
        participant_frame = (frame.get("participantFrames") or {}).get(participant_key)
        if participant_frame:
            output.append({
                **participant_frame,
                "timestamp": frame.get("timestamp", participant_frame.get("timestamp", 0)),
            })
    return sorted(output, key=_timestamp)


def _build_resource_windows(
    resource_events: list[dict[str, Any]],
    death_events: list[dict[str, Any]],
    participant_team_id: int | None,
) -> list[dict[str, Any]]:
    windows = []
    for event in resource_events:
        timestamp = _timestamp(event)
        deaths_before = [
            death for death in death_events
            if 0 <= timestamp - _timestamp(death) <= RESOURCE_WINDOW_MS
        ]
        killer_team_id = event.get("killerTeamId")
        windows.append({
            "resource": event.get("monsterType"),
            "timestamp": timestamp,
            "minute": round(timestamp / 60_000, 1),
            "killer_team_id": killer_team_id,
            "player_team_id": participant_team_id,
            "player_team_secured": (
                killer_team_id == participant_team_id
                if killer_team_id is not None and participant_team_id is not None
                else None
            ),
            "player_died_before": bool(deaths_before),
            "death_timestamps": [_timestamp(death) for death in deaths_before],
        })
    return windows


def _build_insights(
    early_deaths: int,
    resource_deaths: int,
    cs_per_min_at_10: float | None,
    role_profile: dict[str, Any],
) -> list[dict[str, Any]]:
    insights = []
    if early_deaths:
        insights.append({
            "type": "early_death",
            "severity": "high" if early_deaths >= 2 else "medium",
            "title": "前 10 分钟死亡偏早",
            "evidence": [f"前 10 分钟死亡 {early_deaths} 次"],
            "recommendation": "前 10 分钟把目标改成稳定补刀和保血量，河道无视野时少接长追击。",
        })
    if resource_deaths:
        insights.append({
            "type": "resource_death",
            "severity": "high",
            "title": "关键资源前阵亡",
            "evidence": [f"资源刷新/击杀前 90 秒内死亡 {resource_deaths} 次"],
            "recommendation": "小龙、先锋、男爵前 90 秒优先补视野和保持人数，不在无队友覆盖的位置单独越线。",
        })
    if (
        role_profile.get("cs_is_primary")
        and cs_per_min_at_10 is not None
        and cs_per_min_at_10 < 5.5
    ):
        insights.append({
            "type": "lane_cs",
            "severity": "medium",
            "title": "对线期补刀偏低",
            "evidence": [f"10 分钟补刀约 {cs_per_min_at_10}/分钟"],
            "recommendation": "复盘前 10 分钟漏刀来源，优先减少无收益游走和塔下漏刀。",
        })
    return insights[:5]


def _closest_frame_at_or_before(
    frames: list[dict[str, Any]],
    timestamp: int,
) -> dict[str, Any] | None:
    candidates = [frame for frame in frames if _timestamp(frame) <= timestamp]
    if candidates:
        return candidates[-1]
    return frames[0] if frames else None


def _frame_cs(frame: dict[str, Any] | None) -> int | None:
    if not frame:
        return None
    return int(frame.get("minionsKilled") or 0) + int(frame.get("jungleMinionsKilled") or 0)


def _frame_value(frame: dict[str, Any] | None, key: str) -> int | None:
    if not frame:
        return None
    value = frame.get(key)
    return int(value) if value is not None else None


def _event_summary(event: dict[str, Any]) -> dict[str, Any]:
    timestamp = _timestamp(event)
    return {
        "type": event.get("type"),
        "timestamp": timestamp,
        "minute": round(timestamp / 60_000, 1),
        "killer_id": event.get("killerId"),
        "victim_id": event.get("victimId"),
        "assists": event.get("assistingParticipantIds") or [],
    }


def _objective_summary(
    event: dict[str, Any],
    participant_team_id: int | None,
) -> dict[str, Any]:
    timestamp = _timestamp(event)
    killer_team_id = event.get("killerTeamId")
    return {
        "type": event.get("monsterType"),
        "timestamp": timestamp,
        "minute": round(timestamp / 60_000, 1),
        "killer_team_id": killer_team_id,
        "player_team_secured": (
            killer_team_id == participant_team_id
            if killer_team_id is not None and participant_team_id is not None
            else None
        ),
    }


def _timestamp(item: dict[str, Any]) -> int:
    return int(item.get("timestamp") or 0)
