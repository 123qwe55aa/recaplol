"""Build AI coach context from persisted player and match data."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.match import MatchParticipantRepository, MatchRepository
from app.repositories.player import ChampionMasteryRepository, PlayerRepository


class CoachContextBuilder:
    """Aggregate plain-dict context for coach report generation."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.player_repo = PlayerRepository(session)
        self.match_repo = MatchRepository(session)
        self.participant_repo = MatchParticipantRepository(session)
        self.mastery_repo = ChampionMasteryRepository(session)

    async def build_context(self, puuid: str, match_limit: int = 20) -> dict:
        player = await self.player_repo.get_by_puuid(puuid)
        recent_match_ids = await self.match_repo.get_recent_matches(
            puuid, limit=match_limit
        )
        masteries = await self.mastery_repo.get_by_puuid(puuid)

        rows = []
        wins = 0
        known_results = 0
        role_counts: Counter[str] = Counter()
        champion_counts: dict[int, dict] = {}

        totals = defaultdict(float)
        total_minutes = 0.0

        for match_id in recent_match_ids:
            match = await self.match_repo.get_by_match_id(match_id)
            participant = await self.participant_repo.get_participant(match_id, puuid)
            if not match or not participant:
                continue

            win = _derive_win(match, participant)
            if win is not None:
                known_results += 1
                wins += int(win)

            role = _get(participant, "team_position") or _get(
                participant, "individual_position"
            )
            if role:
                role_counts[str(role)] += 1

            champion_id = _get(participant, "champion_id")
            champion_name = _get(participant, "champion_name")
            if champion_id is not None:
                champion = champion_counts.setdefault(
                    int(champion_id),
                    {
                        "champion_id": int(champion_id),
                        "champion_name": champion_name,
                        "games": 0,
                    },
                )
                champion["games"] += 1
                if not champion.get("champion_name") and champion_name:
                    champion["champion_name"] = champion_name

            cs = _number(_get(participant, "total_minions_killed")) + _number(
                _get(participant, "neutral_minions_killed")
            )
            duration_seconds = _number(_get(participant, "time_played")) or _number(
                _get(match, "game_duration")
            )
            minutes = duration_seconds / 60.0 if duration_seconds else 0.0
            total_minutes += minutes

            totals["kills"] += _number(_get(participant, "kills"))
            totals["deaths"] += _number(_get(participant, "deaths"))
            totals["assists"] += _number(_get(participant, "assists"))
            totals["cs"] += cs
            totals["vision_score"] += _number(_get(participant, "vision_score"))
            totals["gold_earned"] += _number(_get(participant, "gold_earned"))

            rows.append(
                {
                    "match_id": match_id,
                    "champion_id": champion_id,
                    "champion_name": champion_name,
                    "role": role,
                    "win": win,
                    "kills": _get(participant, "kills"),
                    "deaths": _get(participant, "deaths"),
                    "assists": _get(participant, "assists"),
                    "cs": cs,
                    "vision_score": _get(participant, "vision_score"),
                    "gold_earned": _get(participant, "gold_earned"),
                    "game_duration": _get(match, "game_duration"),
                }
            )

        match_count = len(rows)
        averages = _build_averages(totals, match_count, total_minutes)
        primary_champions = sorted(
            champion_counts.values(),
            key=lambda item: (-item["games"], str(item.get("champion_name") or "")),
        )
        context = {
            "player": _player_dict(player, puuid),
            "recent_match_ids": list(recent_match_ids),
            "match_count": match_count,
            "primary_role": role_counts.most_common(1)[0][0] if role_counts else None,
            "primary_champions": primary_champions,
            "champion_masteries": [_mastery_dict(mastery) for mastery in masteries],
            "averages": averages,
            "win_rate": round(wins / known_results, 2) if known_results else None,
            "matches": rows,
        }
        context["data_fingerprint"] = _fingerprint(context)
        return context


def _build_averages(totals: dict[str, float], count: int, total_minutes: float) -> dict:
    if count == 0:
        return {
            "kills": 0.0,
            "deaths": 0.0,
            "assists": 0.0,
            "cs": 0.0,
            "cs_per_minute": 0.0,
            "vision_score": 0.0,
            "gold_earned": 0.0,
        }
    return {
        "kills": round(totals["kills"] / count, 2),
        "deaths": round(totals["deaths"] / count, 2),
        "assists": round(totals["assists"] / count, 2),
        "cs": round(totals["cs"] / count, 2),
        "cs_per_minute": round(totals["cs"] / total_minutes, 2)
        if total_minutes
        else 0.0,
        "vision_score": round(totals["vision_score"] / count, 2),
        "gold_earned": round(totals["gold_earned"] / count, 2),
    }


def _derive_win(match: Any, participant: Any) -> bool | None:
    if (_get(match, "game_duration") or 0) > 0 and _get(match, "game_duration") <= 300:
        return None
    blue_team_win = _get(match, "blue_team_win")
    team_id = _get(participant, "team_id")
    if blue_team_win is None or team_id is None:
        return None
    blue_win = bool(blue_team_win)
    return blue_win if int(team_id) == 100 else not blue_win


def _fingerprint(context: dict) -> str:
    payload = {
        "player": context.get("player"),
        "recent_match_ids": context.get("recent_match_ids"),
        "match_count": context.get("match_count"),
        "averages": context.get("averages"),
        "win_rate": context.get("win_rate"),
        "matches": context.get("matches"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _player_dict(player: Any, puuid: str) -> dict:
    if not player:
        return {"puuid": puuid}
    return {
        "puuid": _get(player, "puuid"),
        "summoner_id": _get(player, "summoner_id"),
        "summoner_name": _get(player, "summoner_name"),
        "tag_line": _get(player, "tag_line"),
        "profile_icon_id": _get(player, "profile_icon_id"),
        "summoner_level": _get(player, "summoner_level"),
        "ranked_solo_tier": _get(player, "ranked_solo_tier"),
        "ranked_solo_rank": _get(player, "ranked_solo_rank"),
        "ranked_solo_league_points": _get(player, "ranked_solo_league_points"),
    }


def _mastery_dict(mastery: Any) -> dict:
    return {
        "champion_id": _get(mastery, "champion_id"),
        "champion_level": _get(mastery, "champion_level"),
        "champion_points": _get(mastery, "champion_points"),
    }


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
