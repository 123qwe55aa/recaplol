"""Tests for Pydantic schemas."""
import pytest
from datetime import datetime

from app.schemas.player import (
    RankInfo,
    PlayerBase,
    PlayerResponse,
    ChampionMasteryResponse,
    PlayerChampionMasteryResponse,
)
from app.schemas.match import (
    ParticipantStats,
    TeamBans,
    MatchTeamInfo,
    MatchResponse,
    MatchListResponse,
    MatchTimelineEvent,
    MatchTimelineResponse,
)
from app.schemas.coach import (
    CoachChatRequest,
    CoachChatResponse,
    CoachDataWindow,
    CoachGenerateRequest,
    CoachPriority,
    CoachReportPayload,
    CoachReportResponse,
)


class TestRankInfoSchema:
    """Test RankInfo schema."""

    def test_rank_info_full(self):
        """Test full RankInfo creation."""
        rank = RankInfo(
            tier="GOLD",
            rank="I",
            league_points=75,
            wins=100,
            losses=50,
            queue_type="RANKED_SOLO_5x5",
        )
        assert rank.tier == "GOLD"
        assert rank.rank == "I"
        assert rank.league_points == 75
        assert rank.wins == 100
        assert rank.losses == 50
        assert rank.queue_type == "RANKED_SOLO_5x5"

    def test_rank_info_defaults(self):
        """Test RankInfo default values."""
        rank = RankInfo()
        assert rank.tier is None
        assert rank.rank is None
        assert rank.league_points == 0
        assert rank.wins == 0
        assert rank.losses == 0
        assert rank.queue_type == "RANKED_SOLO_5x5"


class TestPlayerSchemas:
    """Test Player-related schemas."""

    def test_player_base(self):
        """Test PlayerBase schema."""
        player = PlayerBase(
            puuid="test-puuid",
            summoner_name="TestPlayer",
            tag_line="NA1",
        )
        assert player.puuid == "test-puuid"
        assert player.summoner_name == "TestPlayer"
        assert player.tag_line == "NA1"

    def test_player_response(self):
        """Test PlayerResponse schema."""
        player = PlayerResponse(
            puuid="test-puuid",
            summoner_name="TestPlayer",
            tag_line="NA1",
            summoner_id="summoner-123",
            profile_icon_id=1,
            summoner_level=50,
            ranked_stats=RankInfo(tier="DIAMOND", rank="II", league_points=80),
        )
        assert player.puuid == "test-puuid"
        assert player.summoner_level == 50
        assert player.ranked_stats.tier == "DIAMOND"
        assert player.ranked_stats.rank == "II"

    def test_player_response_minimal(self):
        """Test PlayerResponse with minimal data."""
        player = PlayerResponse(
            puuid="test-puuid",
            summoner_name="MinimalPlayer",
            tag_line="NA1",
        )
        assert player.summoner_level == 1
        assert player.summoner_id is None
        assert player.ranked_stats is None


class TestChampionMasterySchema:
    """Test ChampionMasteryResponse schema."""

    def test_champion_mastery_response_full(self):
        """Test full ChampionMasteryResponse."""
        mastery = ChampionMasteryResponse(
            champion_id=103,
            champion_name="Ahri",
            champion_level=7,
            champion_points=500000,
            champion_points_since_last_level=250000,
            champion_points_until_next_level=100000,
            chest_granted=True,
            last_played_time=1700000000000,
            tokens_earned=2,
        )
        assert mastery.champion_id == 103
        assert mastery.champion_name == "Ahri"
        assert mastery.champion_level == 7
        assert mastery.champion_points == 500000
        assert mastery.chest_granted is True

    def test_champion_mastery_response_from_attributes(self):
        """Test ChampionMasteryResponse from_attributes."""
        mastery = ChampionMasteryResponse(
            champion_id=1,
            champion_level=5,
            champion_points=100000,
            champion_points_since_last_level=50000,
            champion_points_until_next_level=50000,
            chest_granted=False,
            tokens_earned=0,
        )
        assert mastery.champion_id == 1
        assert mastery.chest_granted is False


class TestPlayerChampionMasteryResponse:
    """Test PlayerChampionMasteryResponse schema."""

    def test_player_champion_mastery_response(self):
        """Test PlayerChampionMasteryResponse."""
        masteries = PlayerChampionMasteryResponse(
            puuid="test-puuid",
            summoner_name="TestPlayer",
            total_champion_levels=50,
            total_champion_points=2000000,
            champion_masteries=[
                ChampionMasteryResponse(
                    champion_id=103,
                    champion_level=7,
                    champion_points=500000,
                    champion_points_since_last_level=250000,
                    champion_points_until_next_level=100000,
                    chest_granted=True,
                    tokens_earned=2,
                ),
                ChampionMasteryResponse(
                    champion_id=1,
                    champion_level=5,
                    champion_points=200000,
                    champion_points_since_last_level=100000,
                    champion_points_until_next_level=100000,
                    chest_granted=True,
                    tokens_earned=1,
                ),
            ],
        )
        assert masteries.puuid == "test-puuid"
        assert masteries.total_champion_levels == 50
        assert masteries.total_champion_points == 2000000
        assert len(masteries.champion_masteries) == 2


class TestMatchSchemas:
    """Test Match-related schemas."""

    def test_participant_stats_full(self):
        """Test full ParticipantStats."""
        stats = ParticipantStats(
            summoner_name="TestPlayer",
            team_id=100,
            team_position="MID",
            champion_id=103,
            champion_name="Ahri",
            champion_level=16,
            kills=10,
            deaths=3,
            assists=8,
            kda=6.0,
            total_damage_dealt=250000,
            total_damage_dealt_to_champions=50000,
            total_damage_taken=30000,
            neutral_minions_killed=50,
            total_minions_killed=200,
            cs_per_minute=8.5,
            vision_score=25,
            wards_placed=50,
            wards_destroyed=10,
            gold_earned=15000,
            items=[3031, 3040, 3157, 0, 0, 0, 3364],
            double_kills=1,
            triple_kills=0,
            quadra_kills=0,
            pentakills=0,
        )
        assert stats.summoner_name == "TestPlayer"
        assert stats.kills == 10
        assert stats.deaths == 3
        assert stats.assists == 8
        assert stats.kda == 6.0
        assert stats.cs_per_minute == 8.5
        assert len(stats.items) == 7

    def test_participant_stats_defaults(self):
        """Test ParticipantStats default values."""
        stats = ParticipantStats()
        assert stats.kills == 0
        assert stats.deaths == 0
        assert stats.assists == 0
        assert stats.kda == 0.0
        assert stats.champion_level == 0
        assert stats.items == []

    def test_team_bans(self):
        """Test TeamBans schema."""
        bans = TeamBans(champion_id=103, pick_turn=1)
        assert bans.champion_id == 103
        assert bans.pick_turn == 1

    def test_match_team_info(self):
        """Test MatchTeamInfo schema."""
        team = MatchTeamInfo(
            team_id=100,
            win=True,
            bans=[
                TeamBans(champion_id=103, pick_turn=1),
                TeamBans(champion_id=1, pick_turn=2),
            ],
        )
        assert team.team_id == 100
        assert team.win is True
        assert len(team.bans) == 2

    def test_match_response_full(self):
        """Test full MatchResponse."""
        match = MatchResponse(
            match_id="NA1_1234567890",
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1.1",
            game_duration=1800,
            game_start_timestamp=1700000000000,
            game_end_timestamp=1700001800000,
            blue_team=MatchTeamInfo(
                team_id=100,
                win=True,
                bans=[TeamBans(champion_id=103, pick_turn=1)],
            ),
            red_team=MatchTeamInfo(
                team_id=200,
                win=False,
                bans=[],
            ),
            participants=[
                ParticipantStats(
                    summoner_name="BlueMid",
                    team_id=100,
                    champion_id=103,
                    kills=10,
                    deaths=3,
                    assists=8,
                ),
                ParticipantStats(
                    summoner_name="RedMid",
                    team_id=200,
                    champion_id=1,
                    kills=5,
                    deaths=10,
                    assists=12,
                ),
            ],
        )
        assert match.match_id == "NA1_1234567890"
        assert match.blue_team.win is True
        assert match.red_team.win is False
        assert len(match.participants) == 2

    def test_participant_stats_can_represent_remake(self):
        """Test participant outcome can distinguish remake from loss."""
        stats = ParticipantStats(
            summoner_name="BlueMid",
            team_id=100,
            champion_id=103,
            win=None,
            outcome="REMAKE",
        )

        assert stats.win is None
        assert stats.outcome == "REMAKE"

    def test_match_list_response(self):
        """Test MatchListResponse schema."""
        response = MatchListResponse(
            matches=["NA1_111", "NA1_222", "NA1_333"],
            start_index=0,
            total_count=100,
            puuid="test-puuid",
        )
        assert len(response.matches) == 3
        assert response.start_index == 0
        assert response.total_count == 100

    def test_match_timeline_event(self):
        """Test MatchTimelineEvent schema."""
        event = MatchTimelineEvent(
            type="CHAMPION_KILL",
            timestamp=5000,
            participant_id=5,
            data={"position": {"x": 1000, "y": 500}, "killerId": 5},
        )
        assert event.type == "CHAMPION_KILL"
        assert event.timestamp == 5000
        assert event.participant_id == 5
        assert event.data["position"]["x"] == 1000

    def test_match_timeline_response(self):
        """Test MatchTimelineResponse schema."""
        timeline = MatchTimelineResponse(
            match_id="NA1_1234567890",
            frame_interval=60000,
            frames=[
                {"timestamp": 0, "participantFrames": {}},
                {"timestamp": 60000, "participantFrames": {}},
            ],
        )
        assert timeline.match_id == "NA1_1234567890"
        assert timeline.frame_interval == 60000
        assert len(timeline.frames) == 2


class TestCoachSchemas:
    """Test coach-related schemas."""

    def test_coach_report_payload(self):
        """Test full CoachReportPayload validation."""
        payload = CoachReportPayload(
            summary="Your biggest gains are deaths and vision.",
            data_window=CoachDataWindow(match_count=12, days=14),
            priorities=[
                CoachPriority(
                    area="deaths",
                    title="Reduce risky mid-game fights",
                    severity="high",
                    evidence=["Averaged 7.2 deaths across 12 games"],
                    recommendation="Track missing enemies before contesting river.",
                )
            ],
            confidence=0.82,
        )

        assert payload.summary.startswith("Your biggest gains")
        assert payload.data_window.match_count == 12
        assert payload.data_window.days == 14
        assert payload.priorities[0].area == "deaths"
        assert payload.priorities[0].evidence == ["Averaged 7.2 deaths across 12 games"]
        assert payload.confidence == 0.82

    def test_coach_report_response(self):
        """Test CoachReportResponse validation."""
        generated_at = datetime.utcnow()
        response = CoachReportResponse(
            id=1,
            puuid="test-puuid",
            report=CoachReportPayload(
                summary="Focus on farming.",
                data_window=CoachDataWindow(match_count=8),
                priorities=[],
                confidence=0.7,
            ),
            data_fingerprint="fingerprint-123",
            model="gpt-4.1-mini",
            status="completed",
            stale=False,
            generated_at=generated_at,
            created_at=generated_at,
            updated_at=generated_at,
        )

        assert response.id == 1
        assert response.puuid == "test-puuid"
        assert response.report.summary == "Focus on farming."
        assert response.data_fingerprint == "fingerprint-123"
        assert response.error_message is None
        assert response.stale is False

    def test_coach_request_defaults(self):
        """Test coach request defaults."""
        generate_request = CoachGenerateRequest()
        chat_request = CoachChatRequest(question="How do I die less?")

        assert generate_request.force is False
        assert generate_request.match_limit == 20
        assert chat_request.question == "How do I die less?"
        assert chat_request.messages == []

    def test_coach_chat_response(self):
        """Test CoachChatResponse validation."""
        response = CoachChatResponse(
            answer="Ward river before pushing and skip fights without jungle vision.",
            model="gpt-4.1-mini",
            report_id=7,
            cited_priorities=["vision", "deaths"],
        )

        assert response.answer.startswith("Ward river")
        assert response.model == "gpt-4.1-mini"
        assert response.report_id == 7
        assert response.cited_priorities == ["vision", "deaths"]
