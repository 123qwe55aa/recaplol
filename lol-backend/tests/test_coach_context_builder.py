"""Tests for coach context aggregation."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.match import Match, MatchParticipant
from app.models.player import ChampionMastery, Player
from app.services.coach_context_builder import CoachContextBuilder


@pytest.mark.asyncio
async def test_build_context_aggregates_player_recent_matches_and_fingerprint():
    session = AsyncMock()
    player = Player(
        puuid="puuid-1",
        summoner_id="summoner-1",
        summoner_name="CoachMe",
        tag_line="NA1",
        profile_icon_id=7,
        summoner_level=99,
        ranked_solo_tier="GOLD",
        ranked_solo_rank="II",
        ranked_solo_league_points=44,
    )
    match_ids = ["NA1_3", "NA1_2", "NA1_1"]
    matches = {
        "NA1_3": Match(match_id="NA1_3", game_duration=1800, blue_team_win=1),
        "NA1_2": Match(match_id="NA1_2", game_duration=1500, blue_team_win=0),
        "NA1_1": Match(match_id="NA1_1", game_duration=1200, blue_team_win=1),
    }
    participants = {
        "NA1_3": MatchParticipant(
            match_id="NA1_3",
            puuid="puuid-1",
            team_id=100,
            team_position="MID",
            champion_id=103,
            champion_name="Ahri",
            kills=6,
            deaths=3,
            assists=9,
            total_minions_killed=180,
            neutral_minions_killed=12,
            vision_score=24,
            gold_earned=11000,
            item0=1056,
            item1=3020,
            item2=6655,
            item3=0,
            item4=0,
            item5=0,
            item6=3340,
            perks={
                "styles": [
                    {
                        "description": "primaryStyle",
                        "style": 8100,
                        "selections": [
                            {"perk": 8112},
                            {"perk": 8139},
                            {"perk": 8138},
                            {"perk": 8106},
                        ],
                    },
                    {
                        "description": "subStyle",
                        "style": 8200,
                        "selections": [{"perk": 8210}, {"perk": 8236}],
                    },
                ]
            },
        ),
        "NA1_2": MatchParticipant(
            match_id="NA1_2",
            puuid="puuid-1",
            team_id=200,
            team_position="MID",
            champion_id=103,
            champion_name="Ahri",
            kills=4,
            deaths=6,
            assists=5,
            total_minions_killed=140,
            neutral_minions_killed=10,
            vision_score=18,
            gold_earned=9200,
        ),
        "NA1_1": MatchParticipant(
            match_id="NA1_1",
            puuid="puuid-1",
            team_id=100,
            team_position="JUNGLE",
            champion_id=64,
            champion_name="Lee Sin",
            kills=8,
            deaths=5,
            assists=12,
            total_minions_killed=35,
            neutral_minions_killed=120,
            vision_score=30,
            gold_earned=12500,
        ),
    }
    match_participants = {
        "NA1_3": [
            participants["NA1_3"],
            MatchParticipant(
                match_id="NA1_3",
                puuid="enemy-1",
                team_id=200,
                team_position="MID",
                champion_id=7,
                champion_name="LeBlanc",
                kills=5,
                deaths=5,
                assists=7,
                total_minions_killed=170,
                neutral_minions_killed=8,
                vision_score=19,
                gold_earned=10400,
            ),
        ],
        "NA1_2": [
            participants["NA1_2"],
            MatchParticipant(
                match_id="NA1_2",
                puuid="enemy-2",
                team_id=100,
                team_position="MID",
                champion_id=99,
                champion_name="Lux",
                kills=7,
                deaths=4,
                assists=6,
                total_minions_killed=155,
                neutral_minions_killed=5,
                vision_score=16,
                gold_earned=9800,
            ),
        ],
        "NA1_1": [
            participants["NA1_1"],
            MatchParticipant(
                match_id="NA1_1",
                puuid="enemy-3",
                team_id=200,
                team_position="JUNGLE",
                champion_id=76,
                champion_name="Nidalee",
                kills=6,
                deaths=7,
                assists=10,
                total_minions_killed=28,
                neutral_minions_killed=112,
                vision_score=26,
                gold_earned=11800,
            ),
        ],
    }
    masteries = [
        ChampionMastery(
            puuid="puuid-1",
            summoner_id="summoner-1",
            champion_id=103,
            champion_level=7,
            champion_points=300000,
        ),
        ChampionMastery(
            puuid="puuid-1",
            summoner_id="summoner-1",
            champion_id=64,
            champion_level=5,
            champion_points=120000,
        ),
    ]

    with patch("app.services.coach_context_builder.PlayerRepository") as player_repo:
        with patch("app.services.coach_context_builder.MatchRepository") as match_repo:
            with patch(
                "app.services.coach_context_builder.MatchParticipantRepository"
            ) as participant_repo:
                with patch(
                    "app.services.coach_context_builder.ChampionMasteryRepository"
                ) as mastery_repo:
                    player_repo.return_value.get_by_puuid = AsyncMock(return_value=player)
                    match_repo.return_value.get_recent_matches = AsyncMock(
                        return_value=match_ids
                    )
                    match_repo.return_value.get_by_match_id = AsyncMock(
                        side_effect=lambda match_id: matches[match_id]
                    )
                    participant_repo.return_value.get_participant = AsyncMock(
                        side_effect=lambda match_id, puuid: participants[match_id]
                    )
                    participant_repo.return_value.get_participants_by_match = AsyncMock(
                        side_effect=lambda match_id: match_participants[match_id]
                    )
                    mastery_repo.return_value.get_by_puuid = AsyncMock(
                        return_value=masteries
                    )

                    context = await CoachContextBuilder(session).build_context(
                        "puuid-1", match_limit=3
                    )
                    duplicate = await CoachContextBuilder(session).build_context(
                        "puuid-1", match_limit=3
                    )

    assert context["player"]["puuid"] == "puuid-1"
    assert context["player"]["summoner_name"] == "CoachMe"
    assert context["recent_match_ids"] == match_ids
    assert context["match_count"] == 3
    assert context["primary_role"] == "MID"
    assert context["primary_champions"][0]["champion_name"] == "Ahri"
    assert context["primary_champions"][0]["games"] == 2
    assert context["averages"] == {
        "kills": 6.0,
        "deaths": 4.67,
        "assists": 8.67,
        "cs": 165.67,
        "cs_per_minute": 6.63,
        "vision_score": 24.0,
        "gold_earned": 10900.0,
    }
    assert context["win_rate"] == 1.0
    assert context["matches"][1]["win"] is True
    assert context["matches"][0]["items"] == {
        "inventory": [1056, 3020, 6655],
        "trinket": 3340,
    }
    assert context["matches"][0]["runes"] == {
        "primary_style": 8100,
        "sub_style": 8200,
        "keystone": 8112,
        "selected_perks": [8112, 8139, 8138, 8106, 8210, 8236],
    }
    assert context["matches"][0]["lane_opponent"]["champion_name"] == "LeBlanc"
    assert context["matches"][0]["lane_opponent"]["cs"] == 178.0
    assert context["lane_opponent_comparison"]["sample_size"] == 3
    assert context["lane_opponent_comparison"]["player"]["cs_per_minute"] == 6.63
    assert context["lane_opponent_comparison"]["opponent"]["cs_per_minute"] == 6.37
    assert context["lane_opponent_comparison"]["delta"]["gold_earned"] == 233.33
    assert context["data_fingerprint"] == duplicate["data_fingerprint"]
