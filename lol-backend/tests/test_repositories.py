"""Tests for repositories."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.repositories.player import PlayerRepository, ChampionMasteryRepository
from app.repositories.match import MatchRepository, MatchParticipantRepository
from app.models.player import Player, ChampionMastery
from app.models.match import Match, MatchParticipant


class TestPlayerRepository:
    """Test PlayerRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create a PlayerRepository with mock session."""
        return PlayerRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_puuid(self, repository, mock_session):
        """Test get_by_puuid."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = Player(
            puuid="test-puuid",
            summoner_name="TestPlayer",
            tag_line="NA1",
        )
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_puuid("test-puuid")

        assert result is not None
        assert result.puuid == "test-puuid"
        assert result.summoner_name == "TestPlayer"

    @pytest.mark.asyncio
    async def test_get_by_puuid_not_found(self, repository, mock_session):
        """Test get_by_puuid returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_puuid("nonexistent-puuid")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_summoner_name(self, repository, mock_session):
        """Test get_by_summoner_name."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = Player(
            puuid="test-puuid",
            summoner_name="TestPlayer",
            tag_line="NA1",
        )
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_summoner_name("TestPlayer", "NA1")

        assert result is not None
        assert result.summoner_name == "TestPlayer"
        statement = mock_session.execute.call_args.args[0]
        sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
        assert "ORDER BY players.updated_at DESC" in sql
        assert "LIMIT 1" in sql

    @pytest.mark.asyncio
    async def test_upsert_player_existing(self, repository, mock_session):
        """Test upsert_player updates existing player."""
        existing_player = Player(
            puuid="test-puuid",
            summoner_name="OldName",
            tag_line="NA1",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_player
        mock_session.execute.return_value = mock_result

        result = await repository.upsert_player(
            puuid="test-puuid",
            summoner_name="NewName",
            tag_line="NA1",
            summoner_level=100,
        )

        assert result.summoner_name == "NewName"
        assert result.summoner_level == 100
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_player_new(self, repository, mock_session):
        """Test upsert_player creates new player."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch.object(repository, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = Player(
                puuid="new-puuid",
                summoner_name="NewPlayer",
                tag_line="NA1",
            )

            result = await repository.upsert_player(
                puuid="new-puuid",
                summoner_name="NewPlayer",
                tag_line="NA1",
            )

            mock_create.assert_called_once()
            created_player = mock_create.call_args.args[0]
            assert created_player.summoner_id is None

    @pytest.mark.asyncio
    async def test_upsert_player_updates_existing_by_summoner_id(self, repository, mock_session):
        """Test upsert_player updates existing row when summoner_id already exists."""
        existing_player = Player(
            puuid="old-puuid",
            summoner_id="sum-123",
            summoner_name="OldName",
            tag_line="TW2",
        )
        # First lookup by puuid -> None, second lookup by summoner_id -> existing
        mock_result_by_puuid = MagicMock()
        mock_result_by_puuid.scalar_one_or_none.return_value = None
        mock_result_by_summoner_id = MagicMock()
        mock_result_by_summoner_id.scalar_one_or_none.return_value = existing_player
        mock_session.execute.side_effect = [mock_result_by_puuid, mock_result_by_summoner_id]

        result = await repository.upsert_player(
            puuid="new-puuid",
            summoner_name="NewName",
            tag_line="TW2",
            summoner_id="sum-123",
        )

        assert result is existing_player
        assert result.puuid == "new-puuid"
        assert result.summoner_name == "NewName"
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recently_updated(self, repository, mock_session):
        """Test get_recently_updated."""
        players = [
            Player(puuid="puuid-1", summoner_name="Player1", tag_line="NA1"),
            Player(puuid="puuid-2", summoner_name="Player2", tag_line="NA1"),
        ]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = players
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_recently_updated(limit=10)

        assert len(result) == 2


class TestChampionMasteryRepository:
    """Test ChampionMasteryRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create a ChampionMasteryRepository with mock session."""
        return ChampionMasteryRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_puuid(self, repository, mock_session):
        """Test get_by_puuid returns champion masteries."""
        masteries = [
            ChampionMastery(
                puuid="test-puuid",
                summoner_id="summoner-123",
                champion_id=103,
                champion_level=7,
                champion_points=500000,
            ),
            ChampionMastery(
                puuid="test-puuid",
                summoner_id="summoner-123",
                champion_id=1,
                champion_level=5,
                champion_points=200000,
            ),
        ]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = masteries
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_puuid("test-puuid")

        assert len(result) == 2
        assert result[0].champion_id == 103

    @pytest.mark.asyncio
    async def test_get_by_puuid_and_champion(self, repository, mock_session):
        """Test get_by_puuid_and_champion."""
        mastery = ChampionMastery(
            puuid="test-puuid",
            summoner_id="summoner-123",
            champion_id=103,
            champion_level=7,
            champion_points=500000,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mastery
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_puuid_and_champion("test-puuid", 103)

        assert result is not None
        assert result.champion_id == 103
        assert result.champion_level == 7

    @pytest.mark.asyncio
    async def test_upsert_masteries_new(self, repository, mock_session):
        """Test upsert_masteries creates new masteries."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        masteries_data = [
            {"championId": 103, "championLevel": 7, "championPoints": 500000},
            {"championId": 1, "championLevel": 5, "championPoints": 200000},
        ]

        result = await repository.upsert_masteries(
            "test-puuid", "summoner-123", masteries_data
        )

        assert len(result) == 2
        assert mock_session.flush.called


class TestMatchRepository:
    """Test MatchRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create a MatchRepository with mock session."""
        return MatchRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_match_id(self, repository, mock_session):
        """Test get_by_match_id."""
        match = Match(
            match_id="NA1_1234567890",
            game_mode="CLASSIC",
            game_duration=1800,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = match
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_match_id("NA1_1234567890")

        assert result is not None
        assert result.match_id == "NA1_1234567890"

    @pytest.mark.asyncio
    async def test_match_exists(self, repository, mock_session):
        """Test match_exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "NA1_1234567890"
        mock_session.execute.return_value = mock_result

        result = await repository.match_exists("NA1_1234567890")

        assert result is True

    @pytest.mark.asyncio
    async def test_match_not_exists(self, repository, mock_session):
        """Test match_exists returns False when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.match_exists("NA1_nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_recent_matches(self, repository, mock_session):
        """Test get_recent_matches orders by Riot match start time."""
        match_ids = ["NA1_111", "NA1_222", "NA1_333"]
        mock_result = MagicMock()
        mock_result.all.return_value = [(mid,) for mid in match_ids]
        mock_session.execute.return_value = mock_result

        result = await repository.get_recent_matches("test-puuid", limit=20)

        assert result == match_ids
        assert len(result) == 3
        statement = mock_session.execute.call_args.args[0]
        sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
        assert "matches" in sql
        assert "game_start_timestamp DESC" in sql

    @pytest.mark.asyncio
    async def test_get_match_count(self, repository, mock_session):
        """Test get_match_count."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock()] * 50
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_match_count("test-puuid")

        assert result == 50


class TestMatchParticipantRepository:
    """Test MatchParticipantRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create a MatchParticipantRepository with mock session."""
        return MatchParticipantRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_participant(self, repository, mock_session):
        """Test get_participant."""
        participant = MatchParticipant(
            match_id="NA1_1234567890",
            puuid="test-puuid",
            summoner_name="TestPlayer",
            kills=10,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = participant
        mock_session.execute.return_value = mock_result

        result = await repository.get_participant("NA1_1234567890", "test-puuid")

        assert result is not None
        assert result.summoner_name == "TestPlayer"
        assert result.kills == 10

    @pytest.mark.asyncio
    async def test_get_participants_by_match(self, repository, mock_session):
        """Test get_participants_by_match."""
        participants = [
            MatchParticipant(match_id="NA1_123", puuid="puuid-1", team_id=100),
            MatchParticipant(match_id="NA1_123", puuid="puuid-2", team_id=200),
        ]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = participants
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_participants_by_match("NA1_123")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_participant_stats(self, repository, mock_session):
        """Test get_participant_stats with filters."""
        participants = [
            MatchParticipant(
                match_id="NA1_123",
                puuid="test-puuid",
                champion_id=103,
                team_position="MID",
                kills=10,
            ),
        ]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = participants
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_participant_stats(
            puuid="test-puuid",
            champion_id=103,
            role="MID",
            limit=100,
        )

        assert len(result) == 1
        assert result[0].champion_id == 103

    @pytest.mark.asyncio
    async def test_upsert_participants(self, repository, mock_session):
        """Test upsert_participants."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        participants_data = [
            {
                "puuid": "test-puuid",
                "summoner_name": "TestPlayer",
                "team_id": 100,
                "champion_id": 103,
                "kills": 10,
                "deaths": 3,
                "assists": 8,
            },
        ]

        result = await repository.upsert_participants("NA1_123", participants_data)

        assert len(result) == 1
        assert result[0].puuid == "test-puuid"
        mock_session.flush.assert_called_once()
