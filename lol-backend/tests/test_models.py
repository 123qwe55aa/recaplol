"""Tests for data models."""
import pytest
from datetime import datetime

from app.models.player import Player, ChampionMastery
from app.models.match import Match, MatchParticipant
from app.models.coach import CoachReport


class TestPlayerModel:
    """Test Player model."""

    def test_player_creation(self):
        """Test basic Player model creation."""
        player = Player(
            puuid="test-puuid-12345",
            summoner_name="TestPlayer",
            tag_line="NA1",
            summoner_level=50,
            ranked_solo_tier="GOLD",
            ranked_solo_rank="I",
            ranked_solo_league_points=75,
            ranked_solo_wins=100,
            ranked_solo_losses=50,
        )
        assert player.puuid == "test-puuid-12345"
        assert player.summoner_name == "TestPlayer"
        assert player.tag_line == "NA1"
        assert player.summoner_level == 50
        assert player.ranked_solo_tier == "GOLD"
        assert player.ranked_solo_rank == "I"
        assert player.ranked_solo_league_points == 75
        assert player.ranked_solo_wins == 100
        assert player.ranked_solo_losses == 50
        assert player.profile_icon_id is None
        assert player.summoner_id is None

    def test_player_default_values(self):
        """Test Player model default values."""
        player = Player(
            puuid="test-puuid",
            summoner_name="DefaultPlayer",
            tag_line="NA1",
        )
        assert player.summoner_level == 1
        assert player.ranked_solo_league_points == 0
        assert player.ranked_solo_wins == 0
        assert player.ranked_solo_losses == 0
        assert player.ranked_solo_tier is None
        assert player.ranked_solo_rank is None

    def test_player_tablename(self):
        """Test Player table name."""
        assert Player.__tablename__ == "players"


class TestChampionMasteryModel:
    """Test ChampionMastery model."""

    def test_champion_mastery_creation(self):
        """Test basic ChampionMastery model creation."""
        mastery = ChampionMastery(
            puuid="test-puuid",
            summoner_id="summoner-123",
            champion_id=1,
            champion_level=7,
            champion_points=500000,
            champion_points_since_last_level=250000,
            champion_points_until_next_level=100000,
            chest_granted=True,
            last_played_time=1700000000000,
            tokens_earned=2,
        )
        assert mastery.puuid == "test-puuid"
        assert mastery.summoner_id == "summoner-123"
        assert mastery.champion_id == 1
        assert mastery.champion_level == 7
        assert mastery.champion_points == 500000
        assert mastery.chest_granted == True
        assert mastery.tokens_earned == 2

    def test_champion_mastery_default_values(self):
        """Test ChampionMastery default values."""
        mastery = ChampionMastery(
            puuid="test-puuid",
            summoner_id="summoner-123",
            champion_id=1,
        )
        assert mastery.champion_level == 0
        assert mastery.champion_points == 0
        assert mastery.chest_granted == 0
        assert mastery.tokens_earned == 0

    def test_champion_mastery_tablename(self):
        """Test ChampionMastery table name."""
        assert ChampionMastery.__tablename__ == "champion_masteries"


class TestMatchModel:
    """Test Match model."""

    def test_match_creation(self):
        """Test basic Match model creation."""
        match = Match(
            match_id="NA1_1234567890",
            game_mode="CLASSIC",
            game_type="MATCHED_GAME",
            game_version="14.1.1",
            game_duration=1800,
            game_start_timestamp=1700000000000,
            game_end_timestamp=1700001800000,
            blue_team_id=100,
            red_team_id=200,
            blue_team_win=1,
        )
        assert match.match_id == "NA1_1234567890"
        assert match.game_mode == "CLASSIC"
        assert match.game_duration == 1800
        assert match.blue_team_id == 100
        assert match.red_team_id == 200
        assert match.blue_team_win == 1

    def test_match_default_values(self):
        """Test Match default values."""
        match = Match(match_id="NA1_0000000000")
        assert match.game_mode is None
        assert match.game_type is None
        assert match.game_version is None
        assert match.game_duration is None
        assert match.blue_team_id is None
        assert match.red_team_id is None
        assert match.blue_team_win is None

    def test_match_tablename(self):
        """Test Match table name."""
        assert Match.__tablename__ == "matches"


class TestMatchParticipantModel:
    """Test MatchParticipant model."""

    def test_match_participant_creation(self):
        """Test basic MatchParticipant creation."""
        participant = MatchParticipant(
            match_id="NA1_1234567890",
            puuid="test-puuid",
            summoner_name="TestPlayer",
            team_id=100,
            team_position="MID",
            champion_id=103,
            champion_name="Ahri",
            champion_level=16,
            kills=10,
            deaths=3,
            assists=8,
            kda=600,  # stored as integer (6.0 * 100)
            double_kills=1,
            triple_kills=0,
            quadra_kills=0,
            pentakills=0,
            total_damage_dealt=250000,
            total_damage_dealt_to_champions=50000,
            total_damage_taken=30000,
            gold_earned=15000,
        )
        assert participant.match_id == "NA1_1234567890"
        assert participant.puuid == "test-puuid"
        assert participant.summoner_name == "TestPlayer"
        assert participant.team_id == 100
        assert participant.team_position == "MID"
        assert participant.champion_id == 103
        assert participant.champion_name == "Ahri"
        assert participant.kills == 10
        assert participant.deaths == 3
        assert participant.assists == 8
        assert participant.kda == 600
        assert participant.double_kills == 1

    def test_match_participant_items(self):
        """Test MatchParticipant items."""
        participant = MatchParticipant(
            match_id="NA1_1234567890",
            puuid="test-puuid",
            item0=3031,
            item1=3040,
            item2=3157,
            item3=0,
            item4=0,
            item5=0,
            item6=3364,
        )
        assert participant.item0 == 3031
        assert participant.item1 == 3040
        assert participant.item2 == 3157
        assert participant.item3 == 0
        assert participant.item6 == 3364

    def test_match_participant_default_values(self):
        """Test MatchParticipant default values."""
        participant = MatchParticipant(
            match_id="NA1_1234567890",
            puuid="test-puuid",
        )
        assert participant.champion_level == 0
        assert participant.kills == 0
        assert participant.deaths == 0
        assert participant.assists == 0
        assert participant.kda == 0
        assert participant.double_kills == 0
        assert participant.triple_kills == 0
        assert participant.quadra_kills == 0
        assert participant.pentakills == 0
        assert participant.wards_placed == 0
        assert participant.wards_destroyed == 0
        assert participant.vision_score == 0

    def test_match_participant_tablename(self):
        """Test MatchParticipant table name."""
        assert MatchParticipant.__tablename__ == "match_participants"


class TestCoachReportModel:
    """Test CoachReport model."""

    def test_coach_report_creation(self):
        """Test basic CoachReport model creation."""
        generated_at = datetime.utcnow()
        report = CoachReport(
            puuid="test-puuid",
            report_json={"summary": "Play fewer risky fights."},
            context_json={"match_count": 10},
            data_fingerprint="fingerprint-123",
            model="gpt-4.1-mini",
            status="completed",
            error_message=None,
            stale=False,
            generated_at=generated_at,
        )

        assert report.puuid == "test-puuid"
        assert report.report_json == {"summary": "Play fewer risky fights."}
        assert report.context_json == {"match_count": 10}
        assert report.data_fingerprint == "fingerprint-123"
        assert report.model == "gpt-4.1-mini"
        assert report.status == "completed"
        assert report.error_message is None
        assert report.stale is False
        assert report.generated_at == generated_at

    def test_coach_report_default_values(self):
        """Test CoachReport Python-side defaults."""
        report = CoachReport(
            puuid="test-puuid",
            report_json={},
            context_json={},
            data_fingerprint="fingerprint-123",
        )

        assert report.model is None
        assert report.status == "completed"
        assert report.error_message is None
        assert report.stale is False
        assert isinstance(report.generated_at, datetime)

    def test_coach_report_tablename_and_indexes(self):
        """Test CoachReport table name and indexes."""
        assert CoachReport.__tablename__ == "coach_reports"

        index_names = {index.name for index in CoachReport.__table__.indexes}
        assert "ix_coach_reports_puuid" in index_names
        assert "ix_coach_reports_data_fingerprint" in index_names
        assert "ix_coach_reports_generated_at" in index_names
