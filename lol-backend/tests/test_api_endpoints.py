"""Tests for API endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.endpoints import player, stats, analysis, opgg, health
from app.models.player import Player, ChampionMastery
from app.models.match import Match, MatchParticipant
from app.services.riot_api_client import RiotAPIError


# Create test app
def create_test_app():
    app = FastAPI()
    app.include_router(player.router)
    app.include_router(stats.router)
    app.include_router(analysis.router)
    app.include_router(opgg.router)
    app.include_router(health.router)
    return app


class TestPlayerEndpoints:
    """Test Player API endpoints."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def mock_player(self):
        """Create mock player."""
        return Player(
            puuid="test-puuid",
            summoner_id="summoner-123",
            summoner_name="TestPlayer",
            tag_line="NA1",
            profile_icon_id=1,
            summoner_level=50,
            revision_date=1700000000000,
            ranked_solo_tier="GOLD",
            ranked_solo_rank="I",
            ranked_solo_league_points=75,
            ranked_solo_wins=100,
            ranked_solo_losses=50,
        )

    @pytest.fixture
    def mock_masteries(self):
        """Create mock champion masteries."""
        return [
            ChampionMastery(
                puuid="test-puuid",
                summoner_id="summoner-123",
                champion_id=103,
                champion_level=7,
                champion_points=500000,
                champion_points_since_last_level=250000,
                champion_points_until_next_level=100000,
                chest_granted=True,
                last_played_time=1700000000000,
                tokens_earned=2,
            ),
            ChampionMastery(
                puuid="test-puuid",
                summoner_id="summoner-123",
                champion_id=1,
                champion_level=5,
                champion_points=200000,
                champion_points_since_last_level=100000,
                champion_points_until_next_level=100000,
                chest_granted=True,
                tokens_earned=1,
            ),
        ]

    def test_get_player_not_found(self, mock_db):
        """Test get_player returns 404 when player not found."""
        from app.repositories.player import PlayerRepository

        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=None)

            app = create_test_app()

            # Override dependency
            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with TestClient(app) as client:
                response = client.get("/players/test-puuid")
                assert response.status_code == 404

            app.dependency_overrides.clear()


    def test_get_player_success(self, mock_db, mock_player):
        """Test get_player returns player data."""
        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=mock_player)

            app = create_test_app()

            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with TestClient(app) as client:
                response = client.get("/players/test-puuid")
                assert response.status_code == 200
                data = response.json()
                assert data["puuid"] == "test-puuid"
                assert data["summoner_name"] == "TestPlayer"
                assert data["ranked_stats"]["tier"] == "GOLD"

            app.dependency_overrides.clear()

    def test_get_player_ranked_not_found(self, mock_db):
        """Test get_player_ranked returns 404 when no ranked data."""
        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=None)

            app = create_test_app()

            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with TestClient(app) as client:
                response = client.get("/players/test-puuid/ranked")
                assert response.status_code == 404

            app.dependency_overrides.clear()

    def test_get_player_ranked_no_data(self, mock_db):
        """Test get_player_ranked returns 404 when player has no ranked data."""
        player_no_ranked = Player(
            puuid="test-puuid",
            summoner_name="TestPlayer",
            tag_line="NA1",
        )

        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=player_no_ranked)

            app = create_test_app()

            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with TestClient(app) as client:
                response = client.get("/players/test-puuid/ranked")
                assert response.status_code == 404

            app.dependency_overrides.clear()

    def test_get_player_ranked_success(self, mock_db, mock_player):
        """Test get_player_ranked returns ranked info."""
        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=mock_player)

            app = create_test_app()

            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with TestClient(app) as client:
                response = client.get("/players/test-puuid/ranked")
                assert response.status_code == 200
                data = response.json()
                assert data["tier"] == "GOLD"
                assert data["rank"] == "I"
                assert data["league_points"] == 75

            app.dependency_overrides.clear()

    def test_get_player_mastery_not_found(self, mock_db):
        """Test get_player_mastery returns 404 when player not found."""
        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=None)

            app = create_test_app()

            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with TestClient(app) as client:
                response = client.get("/players/test-puuid/mastery")
                assert response.status_code == 404

            app.dependency_overrides.clear()

    def test_get_player_mastery_success(self, mock_db, mock_player, mock_masteries):
        """Test get_player_mastery returns mastery data."""
        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            with patch("app.api.endpoints.player.ChampionMasteryRepository") as MockMasteryRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get_by_puuid = AsyncMock(return_value=mock_player)

                mock_mastery_repo = MockMasteryRepo.return_value
                mock_mastery_repo.get_by_puuid = AsyncMock(return_value=mock_masteries)

                app = create_test_app()

                from app.db.database import get_db
                app.dependency_overrides[get_db] = lambda: mock_db

                with TestClient(app) as client:
                    response = client.get("/players/test-puuid/mastery?limit=10")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["puuid"] == "test-puuid"
                    assert len(data["champion_masteries"]) == 2
                    assert data["total_champion_points"] == 700000

                app.dependency_overrides.clear()

    def test_get_player_mastery_syncs_from_riot_when_empty(self, mock_db, mock_player, mock_masteries):
        """Test get_player_mastery backfills mastery data from Riot when cache is empty."""
        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            with patch("app.api.endpoints.player.ChampionMasteryRepository") as MockMasteryRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get_by_puuid = AsyncMock(return_value=mock_player)

                mock_mastery_repo = MockMasteryRepo.return_value
                mock_mastery_repo.get_by_puuid = AsyncMock(side_effect=[[], mock_masteries])
                mock_mastery_repo.upsert_masteries = AsyncMock(return_value=mock_masteries)

                mock_riot_client = AsyncMock()
                mock_riot_client.__aenter__.return_value = mock_riot_client
                mock_riot_client.__aexit__.return_value = None
                mock_riot_client.get_champion_masteries = AsyncMock(return_value=[
                    {"championId": 103, "championLevel": 7, "championPoints": 500000},
                    {"championId": 1, "championLevel": 5, "championPoints": 200000},
                ])

                app = create_test_app()

                from app.db.database import get_db
                app.dependency_overrides[get_db] = lambda: mock_db

                with patch("app.api.endpoints.player.get_riot_client", return_value=mock_riot_client):
                    with TestClient(app) as client:
                        response = client.get("/players/test-puuid/mastery?limit=10")
                        assert response.status_code == 200
                        data = response.json()
                        assert data["puuid"] == "test-puuid"
                        assert len(data["champion_masteries"]) == 2

                mock_mastery_repo.upsert_masteries.assert_awaited_once()
                app.dependency_overrides.clear()

    def test_get_player_by_summoner_not_found(self, mock_db):
        """Test get_player_by_summoner returns 404 when player not found."""
        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_summoner_name = AsyncMock(return_value=None)
            mock_riot_client = AsyncMock()
            mock_riot_client.__aenter__.return_value = mock_riot_client
            mock_riot_client.__aexit__.return_value = None
            mock_riot_client.get_puuid_by_riot_id = AsyncMock(return_value=None)

            app = create_test_app()

            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with patch("app.api.endpoints.player.get_riot_client", return_value=mock_riot_client):
                with TestClient(app) as client:
                    response = client.get("/players/by-summoner/TestPlayer?tag_line=NA1")
                    assert response.status_code == 404

            app.dependency_overrides.clear()

    def test_get_player_by_summoner_success(self, mock_db, mock_player):
        """Test get_player_by_summoner returns player data."""
        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_summoner_name = AsyncMock(return_value=mock_player)

            app = create_test_app()

            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with TestClient(app) as client:
                response = client.get("/players/by-summoner/TestPlayer?tag_line=NA1")
                assert response.status_code == 200
                data = response.json()
                assert data["summoner_name"] == "TestPlayer"

            app.dependency_overrides.clear()

    def test_get_player_by_summoner_refreshes_stale_sea_puuid(self, mock_db):
        """Test SEA player lookup returns the latest Riot Account PUUID."""
        stale_player = Player(
            puuid="old-puuid",
            summoner_name="TestPlayer",
            tag_line="TW2",
            profile_icon_id=1,
            summoner_level=50,
            revision_date=1700000000000,
        )
        refreshed_player = Player(
            puuid="new-puuid",
            summoner_name="TestPlayer",
            tag_line="TW2",
            profile_icon_id=2,
            summoner_level=51,
            revision_date=1800000000000,
        )

        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_summoner_name = AsyncMock(return_value=stale_player)
            mock_repo.upsert_player = AsyncMock(return_value=refreshed_player)

            mock_riot_client = AsyncMock()
            mock_riot_client.__aenter__.return_value = mock_riot_client
            mock_riot_client.__aexit__.return_value = None
            mock_riot_client.get_puuid_by_riot_id = AsyncMock(return_value={"puuid": "new-puuid"})
            mock_riot_client.get_summoner_by_puuid = AsyncMock(
                return_value={
                    "name": "TestPlayer",
                    "profileIconId": 2,
                    "summonerLevel": 51,
                    "revisionDate": 1800000000000,
                }
            )

            app = create_test_app()

            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with patch("app.api.endpoints.player.get_riot_client", return_value=mock_riot_client):
                with TestClient(app) as client:
                    response = client.get("/players/by-summoner/TestPlayer?tag_line=TW2")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["puuid"] == "new-puuid"

            mock_repo.upsert_player.assert_awaited_once()
            app.dependency_overrides.clear()

    def test_refresh_player_by_puuid_not_found(self, mock_db):
        """Test refresh endpoint returns 404 when player does not exist."""
        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=None)

            app = create_test_app()

            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with TestClient(app) as client:
                response = client.post("/players/test-puuid/refresh")
                assert response.status_code == 404

            app.dependency_overrides.clear()

    def test_refresh_player_by_puuid_success(self, mock_db, mock_player):
        """Test refresh endpoint updates player using PUUID path."""
        refreshed_player = Player(
            puuid="test-puuid",
            summoner_id="summoner-456",
            summoner_name="RefreshedName",
            tag_line="NA1",
            profile_icon_id=2,
            summoner_level=60,
            revision_date=1800000000000,
            ranked_solo_tier="PLATINUM",
            ranked_solo_rank="II",
            ranked_solo_league_points=33,
            ranked_solo_wins=120,
            ranked_solo_losses=100,
        )

        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=mock_player)
            mock_repo.upsert_player = AsyncMock(return_value=refreshed_player)

            mock_riot_client = AsyncMock()
            mock_riot_client.__aenter__.return_value = mock_riot_client
            mock_riot_client.__aexit__.return_value = None
            mock_riot_client.get_summoner_by_puuid = AsyncMock(
                return_value={
                    "id": "summoner-456",
                    "name": "RefreshedName",
                    "profileIconId": 2,
                    "summonerLevel": 60,
                    "revisionDate": 1800000000000,
                }
            )
            mock_riot_client.get_player_ranked_stats = AsyncMock(
                return_value=[
                    {
                        "queueType": "RANKED_SOLO_5x5",
                        "tier": "PLATINUM",
                        "rank": "II",
                        "leaguePoints": 33,
                        "wins": 120,
                        "losses": 100,
                    }
                ]
            )

            app = create_test_app()
            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with patch("app.api.endpoints.player.get_riot_client", return_value=mock_riot_client):
                with TestClient(app) as client:
                    response = client.post("/players/test-puuid/refresh")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["puuid"] == "test-puuid"
                    assert data["summoner_name"] == "RefreshedName"
                    assert data["ranked_stats"]["tier"] == "PLATINUM"

            app.dependency_overrides.clear()

    def test_refresh_player_by_puuid_ignores_ranked_decrypt_error(self, mock_db, mock_player):
        """Test refresh succeeds when Riot ranked endpoint returns decrypting 400."""
        refreshed_player = Player(
            puuid="test-puuid",
            summoner_id="summoner-456",
            summoner_name="RefreshedName",
            tag_line="NA1",
            profile_icon_id=2,
            summoner_level=60,
            revision_date=1800000000000,
            ranked_solo_tier=None,
            ranked_solo_rank=None,
            ranked_solo_league_points=0,
            ranked_solo_wins=0,
            ranked_solo_losses=0,
        )

        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=mock_player)
            mock_repo.upsert_player = AsyncMock(return_value=refreshed_player)

            mock_riot_client = AsyncMock()
            mock_riot_client.__aenter__.return_value = mock_riot_client
            mock_riot_client.__aexit__.return_value = None
            mock_riot_client.get_summoner_by_puuid = AsyncMock(
                return_value={
                    "id": "summoner-456",
                    "name": "RefreshedName",
                    "profileIconId": 2,
                    "summonerLevel": 60,
                    "revisionDate": 1800000000000,
                }
            )
            mock_riot_client.get_player_ranked_stats = AsyncMock(
                side_effect=RiotAPIError(
                    400,
                    "Bad Request - Exception decrypting encrypted-id",
                )
            )

            app = create_test_app()
            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with patch("app.api.endpoints.player.get_riot_client", return_value=mock_riot_client):
                with TestClient(app) as client:
                    response = client.post("/players/test-puuid/refresh")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["puuid"] == "test-puuid"
                    assert data["summoner_name"] == "RefreshedName"
                    assert data["ranked_stats"] is None

            app.dependency_overrides.clear()

    def test_refresh_player_by_puuid_ignores_summoner_decrypt_error(self, mock_db, mock_player):
        """Test refresh returns existing player when by-puuid endpoint decrypt fails."""
        with patch("app.api.endpoints.player.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=mock_player)

            mock_riot_client = AsyncMock()
            mock_riot_client.__aenter__.return_value = mock_riot_client
            mock_riot_client.__aexit__.return_value = None
            mock_riot_client.get_summoner_by_puuid = AsyncMock(
                side_effect=RiotAPIError(
                    400,
                    "Bad Request - Exception decrypting test-puuid",
                )
            )

            app = create_test_app()
            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with patch("app.api.endpoints.player.get_riot_client", return_value=mock_riot_client):
                with TestClient(app) as client:
                    response = client.post("/players/test-puuid/refresh")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["puuid"] == "test-puuid"
                    assert data["summoner_name"] == "TestPlayer"

            app.dependency_overrides.clear()


class TestStatsEndpoints:
    """Test Stats API endpoints."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def mock_player(self):
        """Create mock player."""
        return Player(
            puuid="test-puuid",
            summoner_name="TestPlayer",
            tag_line="NA1",
            summoner_level=50,
        )

    @pytest.fixture
    def mock_participants(self):
        """Create mock match participants."""
        return [
            MatchParticipant(
                match_id="NA1_123",
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
                kda=600,
                double_kills=1,
                triple_kills=0,
                quadra_kills=0,
                pentakills=0,
                total_minions_killed=200,
                neutral_minions_killed=50,
                vision_score=25,
                gold_earned=15000,
            ),
            MatchParticipant(
                match_id="NA1_124",
                puuid="test-puuid",
                summoner_name="TestPlayer",
                team_id=100,
                team_position="MID",
                champion_id=103,
                champion_name="Ahri",
                champion_level=15,
                kills=8,
                deaths=4,
                assists=10,
                kda=450,
                double_kills=0,
                triple_kills=1,
                quadra_kills=0,
                pentakills=0,
                total_minions_killed=180,
                neutral_minions_killed=45,
                vision_score=22,
                gold_earned=14000,
            ),
        ]

    @pytest.fixture
    def mock_matches(self):
        """Create mock matches with team outcomes."""
        return [
            Match(match_id="NA1_123", blue_team_win=1),
            Match(match_id="NA1_124", blue_team_win=0),
        ]

    def test_get_player_overview_not_found(self, mock_db):
        """Test get_player_overview returns 404 when player not found."""
        with patch("app.api.endpoints.stats.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=None)

            app = create_test_app()

            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with TestClient(app) as client:
                response = client.get("/stats/players/test-puuid/overview")
                assert response.status_code == 404

            app.dependency_overrides.clear()

    def test_get_player_overview_success(self, mock_db, mock_player, mock_participants, mock_matches):
        """Test get_player_overview returns career stats."""
        with patch("app.api.endpoints.stats.PlayerRepository") as MockRepo:
            with patch("app.api.endpoints.stats.MatchRepository") as MockMatchRepo:
                with patch("app.api.endpoints.stats.MatchParticipantRepository") as MockPartRepo:
                    mock_player_repo = MockRepo.return_value
                    mock_player_repo.get_by_puuid = AsyncMock(return_value=mock_player)

                    mock_match_repo = MockMatchRepo.return_value
                    mock_match_repo.get_recent_matches = AsyncMock(
                        return_value=["NA1_123", "NA1_124"]
                    )
                    mock_match_repo.get_by_match_id = AsyncMock(
                        side_effect=mock_matches
                    )

                    mock_part_repo = MockPartRepo.return_value
                    mock_part_repo.get_participant = AsyncMock(
                        side_effect=mock_participants
                    )

                    app = create_test_app()

                    from app.db.database import get_db
                    app.dependency_overrides[get_db] = lambda: mock_db

                    with TestClient(app) as client:
                        response = client.get("/stats/players/test-puuid/overview")
                        assert response.status_code == 200
                        data = response.json()
                        assert data["puuid"] == "test-puuid"
                        assert data["career"]["total_matches"] == 2

                    app.dependency_overrides.clear()

    def test_get_player_champion_stats_not_found(self, mock_db):
        """Test get_player_champion_stats returns 404 when player not found."""
        with patch("app.api.endpoints.stats.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=None)

            app = create_test_app()

            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with TestClient(app) as client:
                response = client.get("/stats/players/test-puuid/champions/103")
                assert response.status_code == 404

            app.dependency_overrides.clear()

    def test_get_player_champion_stats_no_matches(self, mock_db, mock_player):
        """Test get_player_champion_stats returns 404 when no matches."""
        with patch("app.api.endpoints.stats.PlayerRepository") as MockRepo:
            with patch("app.api.endpoints.stats.MatchParticipantRepository") as MockPartRepo:
                mock_player_repo = MockRepo.return_value
                mock_player_repo.get_by_puuid = AsyncMock(return_value=mock_player)

                mock_part_repo = MockPartRepo.return_value
                mock_part_repo.get_participant_stats = AsyncMock(return_value=[])

                app = create_test_app()

                from app.db.database import get_db
                app.dependency_overrides[get_db] = lambda: mock_db

                with TestClient(app) as client:
                    response = client.get("/stats/players/test-puuid/champions/103")
                    assert response.status_code == 404

                app.dependency_overrides.clear()

    def test_get_player_champion_stats_success(self, mock_db, mock_player, mock_participants, mock_matches):
        """Test get_player_champion_stats returns champion stats."""
        with patch("app.api.endpoints.stats.PlayerRepository") as MockRepo:
            with patch("app.api.endpoints.stats.MatchRepository") as MockMatchRepo:
                with patch("app.api.endpoints.stats.MatchParticipantRepository") as MockPartRepo:
                    mock_player_repo = MockRepo.return_value
                    mock_player_repo.get_by_puuid = AsyncMock(return_value=mock_player)

                    mock_match_repo = MockMatchRepo.return_value
                    mock_match_repo.get_by_match_id = AsyncMock(
                        side_effect=mock_matches
                    )

                    mock_part_repo = MockPartRepo.return_value
                    mock_part_repo.get_participant_stats = AsyncMock(
                        return_value=mock_participants
                    )

                    app = create_test_app()

                    from app.db.database import get_db
                    app.dependency_overrides[get_db] = lambda: mock_db

                    with TestClient(app) as client:
                        response = client.get("/stats/players/test-puuid/champions/103")
                        assert response.status_code == 200
                        data = response.json()
                        assert data["champion_id"] == 103
                        assert data["games_played"] == 2

                    app.dependency_overrides.clear()

    def test_get_player_recent_stats_not_found(self, mock_db):
        """Test get_player_recent_stats returns 404 when player not found."""
        with patch("app.api.endpoints.stats.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=None)

            app = create_test_app()

            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with TestClient(app) as client:
                response = client.get("/stats/players/test-puuid/recent")
                assert response.status_code == 404

            app.dependency_overrides.clear()

    def test_get_player_recent_stats_success(self, mock_db, mock_player, mock_participants, mock_matches):
        """Test get_player_recent_stats returns recent stats."""
        with patch("app.api.endpoints.stats.PlayerRepository") as MockRepo:
            with patch("app.api.endpoints.stats.MatchRepository") as MockMatchRepo:
                with patch("app.api.endpoints.stats.MatchParticipantRepository") as MockPartRepo:
                    mock_player_repo = MockRepo.return_value
                    mock_player_repo.get_by_puuid = AsyncMock(return_value=mock_player)

                    mock_match_repo = MockMatchRepo.return_value
                    mock_match_repo.get_recent_matches = AsyncMock(
                        return_value=["NA1_123", "NA1_124"]
                    )
                    mock_match_repo.get_by_match_id = AsyncMock(
                        side_effect=mock_matches
                    )

                    mock_part_repo = MockPartRepo.return_value
                    mock_part_repo.get_participant = AsyncMock(
                        side_effect=mock_participants
                    )

                    app = create_test_app()

                    from app.db.database import get_db
                    app.dependency_overrides[get_db] = lambda: mock_db

                    with TestClient(app) as client:
                        response = client.get("/stats/players/test-puuid/recent?limit=10")
                        assert response.status_code == 200
                        data = response.json()
                        assert data["puuid"] == "test-puuid"

                    app.dependency_overrides.clear()


class TestAnalysisEndpoints:
    """Test Analysis API endpoints."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def mock_player(self):
        """Create mock player."""
        return Player(
            puuid="test-puuid",
            summoner_name="TestPlayer",
            tag_line="NA1",
            summoner_level=50,
            ranked_solo_tier="GOLD",
            ranked_solo_rank="I",
            ranked_solo_league_points=75,
            ranked_solo_wins=10,
            ranked_solo_losses=5,
        )

    @pytest.fixture
    def mock_participants(self):
        """Create mock match participants."""
        return [
            MatchParticipant(
                match_id="NA1_123",
                puuid="test-puuid",
                summoner_name="TestPlayer",
                team_id=100,
                team_position="MID",
                champion_id=103,
                champion_name="Ahri",
                kills=10,
                deaths=3,
                assists=8,
                kda=600,
                total_minions_killed=200,
                neutral_minions_killed=50,
                vision_score=25,
                gold_earned=15000,
            ),
            MatchParticipant(
                match_id="NA1_124",
                puuid="test-puuid",
                summoner_name="TestPlayer",
                team_id=100,
                team_position="MID",
                champion_id=1,
                champion_name="Annie",
                kills=5,
                deaths=2,
                assists=3,
                kda=400,
                total_minions_killed=180,
                neutral_minions_killed=0,
                vision_score=15,
                gold_earned=12000,
            ),
        ]

    @pytest.fixture
    def mock_matches(self):
        """Create mock matches with team outcomes."""
        return [
            Match(match_id="NA1_123", blue_team_win=1),
            Match(match_id="NA1_124", blue_team_win=0),
        ]

    def test_get_player_trends_not_found(self, mock_db):
        """Test get_player_trends returns 404 when player not found."""
        with patch("app.api.endpoints.analysis.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=None)

            app = create_test_app()

            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with TestClient(app) as client:
                response = client.get("/analysis/players/test-puuid/trends")
                assert response.status_code == 404

            app.dependency_overrides.clear()

    def test_get_player_trends_no_participants(self, mock_db, mock_player):
        """Test get_player_trends returns empty trends when no matches."""
        with patch("app.api.endpoints.analysis.PlayerRepository") as MockRepo:
            with patch("app.api.endpoints.analysis.MatchRepository") as MockMatchRepo:
                mock_player_repo = MockRepo.return_value
                mock_player_repo.get_by_puuid = AsyncMock(return_value=mock_player)

                mock_match_repo = MockMatchRepo.return_value
                mock_match_repo.get_recent_matches = AsyncMock(return_value=[])

                app = create_test_app()

                from app.db.database import get_db
                app.dependency_overrides[get_db] = lambda: mock_db

                with TestClient(app) as client:
                    response = client.get("/analysis/players/test-puuid/trends")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["puuid"] == "test-puuid"
                    assert len(data["kda_evolution"]) == 0

                app.dependency_overrides.clear()

    def test_get_player_trends_success(self, mock_db, mock_player, mock_participants, mock_matches):
        """Test get_player_trends returns trend analysis."""
        with patch("app.api.endpoints.analysis.PlayerRepository") as MockRepo:
            with patch("app.api.endpoints.analysis.MatchRepository") as MockMatchRepo:
                with patch("app.api.endpoints.analysis.MatchParticipantRepository") as MockPartRepo:
                    mock_player_repo = MockRepo.return_value
                    mock_player_repo.get_by_puuid = AsyncMock(return_value=mock_player)

                    mock_match_repo = MockMatchRepo.return_value
                    mock_match_repo.get_recent_matches = AsyncMock(
                        return_value=["NA1_123", "NA1_124"]
                    )
                    mock_match_repo.get_by_match_id = AsyncMock(
                        side_effect=mock_matches
                    )

                    mock_part_repo = MockPartRepo.return_value
                    mock_part_repo.get_participant = AsyncMock(
                        side_effect=mock_participants
                    )

                    app = create_test_app()

                    from app.db.database import get_db
                    app.dependency_overrides[get_db] = lambda: mock_db

                    with TestClient(app) as client:
                        response = client.get("/analysis/players/test-puuid/trends?limit=50")
                        assert response.status_code == 200
                        data = response.json()
                        assert data["puuid"] == "test-puuid"
                        assert data["recent_win_rate"] == 50.0
                        assert len(data["kda_evolution"]) > 0

                    app.dependency_overrides.clear()

    def test_get_player_progress_no_ranked(self, mock_db):
        """Test get_player_progress returns 404 when player has no ranked data."""
        player_no_ranked = Player(
            puuid="test-puuid",
            summoner_name="TestPlayer",
            tag_line="NA1",
        )

        with patch("app.api.endpoints.analysis.PlayerRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_puuid = AsyncMock(return_value=player_no_ranked)

            app = create_test_app()

            from app.db.database import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            with TestClient(app) as client:
                response = client.get("/analysis/players/test-puuid/progress")
                assert response.status_code == 404

            app.dependency_overrides.clear()

    def test_get_player_progress_success(self, mock_db, mock_player, mock_participants, mock_matches):
        """Test get_player_progress returns progress analysis."""
        with patch("app.api.endpoints.analysis.PlayerRepository") as MockRepo:
            with patch("app.api.endpoints.analysis.MatchRepository") as MockMatchRepo:
                with patch("app.api.endpoints.analysis.MatchParticipantRepository") as MockPartRepo:
                    mock_player_repo = MockRepo.return_value
                    mock_player_repo.get_by_puuid = AsyncMock(return_value=mock_player)

                    mock_match_repo = MockMatchRepo.return_value
                    mock_match_repo.get_recent_matches = AsyncMock(
                        return_value=["NA1_123", "NA1_124"]
                    )
                    mock_match_repo.get_by_match_id = AsyncMock(
                        side_effect=mock_matches
                    )

                    mock_part_repo = MockPartRepo.return_value
                    mock_part_repo.get_participant = AsyncMock(
                        side_effect=mock_participants
                    )

                    app = create_test_app()

                    from app.db.database import get_db
                    app.dependency_overrides[get_db] = lambda: mock_db

                    with TestClient(app) as client:
                        response = client.get("/analysis/players/test-puuid/progress?limit=50")
                        assert response.status_code == 200
                        data = response.json()
                        assert data["puuid"] == "test-puuid"
                        assert data["current_tier"] == "GOLD"
                        assert data["win_rate_in_current_rank"] == 50.0

                    app.dependency_overrides.clear()


class TestStatsCalculation:
    """Test statistics calculation functions."""

    def test_calculate_career_stats_empty(self):
        """Test career stats calculation with no participants."""
        from app.api.endpoints.stats import _calculate_career_stats

        result = _calculate_career_stats([], "test-puuid", "TestPlayer")

        assert result.total_matches == 0
        assert result.puuid == "test-puuid"

    def test_calculate_career_stats_with_data(self):
        """Test career stats calculation with participants."""
        from app.api.endpoints.stats import _calculate_career_stats

        participant = MatchParticipant(
            match_id="NA1_123",
            puuid="test-puuid",
            kills=10,
            deaths=3,
            assists=8,
            kda=600,
            double_kills=1,
            triple_kills=0,
            quadra_kills=0,
            pentakills=0,
            total_minions_killed=200,
            neutral_minions_killed=50,
            vision_score=30,
            gold_earned=15000,
        )
        participant.win = False
        participants = [participant]

        result = _calculate_career_stats(participants, "test-puuid", "TestPlayer")

        assert result.total_matches == 1
        assert result.total_wins == 0
        assert result.total_losses == 1
        assert result.win_rate == 0
        assert result.total_kills == 10
        assert result.total_deaths == 3
        assert result.total_assists == 8

    def test_calculate_champion_stats(self):
        """Test champion stats calculation."""
        from app.api.endpoints.stats import _calculate_champion_stats

        participant = MatchParticipant(
            match_id="NA1_123",
            puuid="test-puuid",
            champion_id=103,
            champion_name="Ahri",
            kills=10,
            deaths=3,
            assists=8,
            kda=600,
            total_minions_killed=200,
            neutral_minions_killed=50,
        )
        participant.win = False
        participants = [participant]

        result = _calculate_champion_stats(participants, 103)

        assert result.champion_id == 103
        assert result.games_played == 1
        assert result.wins == 0
        assert result.losses == 1
        assert result.win_rate == 0

    def test_calculate_role_stats(self):
        """Test role stats calculation."""
        from app.api.endpoints.stats import _calculate_role_stats

        participants = [
            MatchParticipant(
                match_id="NA1_123",
                puuid="test-puuid",
                team_position="MID",
                kills=10,
                deaths=3,
                assists=8,
                kda=600,
                total_minions_killed=200,
                neutral_minions_killed=50,
            ),
            MatchParticipant(
                match_id="NA1_124",
                puuid="test-puuid",
                team_position="MID",
                kills=5,
                deaths=2,
                assists=5,
                kda=500,
                total_minions_killed=180,
                neutral_minions_killed=40,
            ),
        ]

        result = _calculate_role_stats(participants)

        assert len(result) == 1
        assert result[0].role == "MID"
        assert result[0].games_played == 2


class TestAnalysisCalculation:
    """Test analysis calculation functions."""

    def test_analyze_kda_trends_empty(self):
        """Test KDA trend analysis with no participants."""
        from app.api.endpoints.analysis import _analyze_kda_trends

        result = _analyze_kda_trends([])

        assert len(result) == 0

    def test_identify_strengths_and_weaknesses(self):
        """Test strengths and weaknesses identification."""
        from app.api.endpoints.analysis import _identify_strengths_and_weaknesses
        from app.schemas.stats import CareerStats, ChampionStats, RoleStats

        career = CareerStats(
            puuid="test-puuid",
            summoner_name="TestPlayer",
            total_matches=100,
            overall_kda=5.0,
            avg_cs_per_minute=9.0,
            avg_vision_score=35,
            total_double_kills=10,
            total_triple_kills=2,
            total_quadra_kills=1,
            total_pentakills=0,
        )

        champion_stats = [
            ChampionStats(champion_id=103, games_played=50),
            ChampionStats(champion_id=1, games_played=30),
        ]

        role_stats = [
            RoleStats(role="MID", games_played=80),
        ]

        strengths, improvements = _identify_strengths_and_weaknesses(
            champion_stats, role_stats, career
        )

        assert len(strengths) > 0
        assert "Exceptional overall KDA ratio" in strengths


class TestOPGGEndpoints:
    """Test OP.GG API endpoints."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings with OP.GG enabled."""
        with patch('app.api.endpoints.opgg.settings') as mock:
            mock.opgg_enabled = True
            mock.opgg_max_retries = 2
            yield mock

    @pytest.fixture
    def mock_scraper(self):
        """Create mock OPGG scraper."""
        scraper = MagicMock()
        scraper.get_champion_build = AsyncMock()
        scraper.get_metrics.return_value = {
            "requests_total": 100,
            "requests_success": 90,
            "requests_failure": 10,
            "cache_hits": 50,
            "cache_hit_rate": 0.5,
        }
        return scraper

    def test_get_champion_build_success(self, mock_settings, mock_scraper):
        """Test successful champion build retrieval."""
        mock_scraper.get_champion_build.return_value = {
            "champion_name": "ahri",
            "win_rate": 52.34,
            "pick_rate": 15.2,
            "games_played": 125432,
            "roles": ["Mid"],
            "items": {
                "start": [{"id": "1001", "name": "Sapphire Crystal"}],
                "core": [{"id": "3020", "name": "Sorcerer's Shoes"}],
                "final": [],
            },
            "skills": ["Q > W > E"],
            "runes": [{"name": "Arcane Comet"}],
            "matchups": {
                "counters": [
                    {"champion_name": "Zed", "win_rate": 45.2, "games": 12345, "advantage": -4.8}
                ],
                "countered_by": [
                    {"champion_name": "Akali", "win_rate": 53.1, "games": 7654, "advantage": 3.1}
                ],
            },
            "synergies": [
                {"champion_name": "Lulu", "win_rate": 56.7, "pick_rate": 12.4, "games": 0}
            ],
            "last_updated": "2024-01-15T10:30:00",
            "source": "op.gg",
            "cached": False,
        }

        with patch('app.api.endpoints.opgg.get_opgg_scraper', return_value=mock_scraper):
            app = create_test_app()
            with TestClient(app) as client:
                response = client.get(
                    "/opgg/champions/ahri/build",
                    params={"region": "kr", "queue": "RANKED_SOLO_5x5", "tier": "overall"}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["champion_name"] == "ahri"
                assert data["data"]["win_rate"] == 52.34
                assert data["data"]["synergies"][0]["champion_name"] == "Lulu"
                assert data["cached"] is False

    def test_get_champion_build_cached(self, mock_settings, mock_scraper):
        """Test cached champion build response."""
        mock_scraper.get_champion_build.return_value = {
            "champion_name": "ahri",
            "win_rate": 52.34,
            "pick_rate": 15.2,
            "games_played": 125432,
            "roles": ["Mid"],
            "items": {"start": [], "core": [], "final": []},
            "skills": [],
            "runes": [],
            "matchups": {"counters": [], "countered_by": []},
            "last_updated": "2024-01-15T10:30:00",
            "source": "op.gg",
            "cached": True,
        }

        with patch('app.api.endpoints.opgg.get_opgg_scraper', return_value=mock_scraper):
            app = create_test_app()
            with TestClient(app) as client:
                response = client.get("/opgg/champions/ahri/build")

                assert response.status_code == 200
                data = response.json()
                assert data["cached"] is True

    def test_get_champion_build_rate_limited(self, mock_settings, mock_scraper):
        """Test rate limit response."""
        from app.services.opgg_scraper import OPGGRateLimitError

        mock_scraper.get_champion_build.side_effect = OPGGRateLimitError(
            "Rate limited", "ahri"
        )

        with patch('app.api.endpoints.opgg.get_opgg_scraper', return_value=mock_scraper):
            app = create_test_app()
            with TestClient(app) as client:
                response = client.get("/opgg/champions/ahri/build")

                assert response.status_code == 429
                assert "rate limit" in response.json()["detail"].lower()

    def test_get_champion_build_not_found(self, mock_settings, mock_scraper):
        """Test champion not found response."""
        from app.services.opgg_scraper import OPGGNotFoundError

        mock_scraper.get_champion_build.side_effect = OPGGNotFoundError(
            "Champion not found", "unknown"
        )

        with patch('app.api.endpoints.opgg.get_opgg_scraper', return_value=mock_scraper):
            app = create_test_app()
            with TestClient(app) as client:
                response = client.get("/opgg/champions/unknown/build")

                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()

    def test_get_champion_build_parse_error(self, mock_settings, mock_scraper):
        """Test parse error response."""
        from app.services.opgg_scraper import OPGGParseError

        mock_scraper.get_champion_build.side_effect = OPGGParseError(
            "Parse failed", "ahri"
        )

        with patch('app.api.endpoints.opgg.get_opgg_scraper', return_value=mock_scraper):
            app = create_test_app()
            with TestClient(app) as client:
                response = client.get("/opgg/champions/ahri/build")

                assert response.status_code == 500
                assert "parse" in response.json()["detail"].lower()

    def test_get_champion_build_feature_disabled(self):
        """Test response when OP.GG feature is disabled."""
        with patch('app.api.endpoints.opgg.settings') as mock:
            mock.opgg_enabled = False

            app = create_test_app()
            with TestClient(app) as client:
                response = client.get("/opgg/champions/ahri/build")

                assert response.status_code == 503
                assert "disabled" in response.json()["detail"].lower()

    def test_get_champion_build_with_counters_limit(self, mock_settings, mock_scraper):
        """Test counters limit parameter."""
        mock_scraper.get_champion_build.return_value = {
            "champion_name": "ahri",
            "win_rate": 52.34,
            "pick_rate": 15.2,
            "games_played": 125432,
            "roles": ["Mid"],
            "items": {"start": [], "core": [], "final": []},
            "skills": [],
            "runes": [],
            "matchups": {
                "counters": [
                    {"champion_name": "Zed", "win_rate": 45.2, "games": 12345},
                    {"champion_name": "Yasuo", "win_rate": 47.1, "games": 11000},
                    {"champion_name": "Fizz", "win_rate": 48.0, "games": 9500},
                    {"champion_name": "LeBlanc", "win_rate": 48.5, "games": 8000},
                    {"champion_name": "Syndra", "win_rate": 49.0, "games": 7500},
                    {"champion_name": "Orianna", "win_rate": 49.3, "games": 7000},
                ],
                "countered_by": [
                    {"champion_name": "Akali", "win_rate": 53.1, "games": 7654},
                    {"champion_name": "Viktor", "win_rate": 52.5, "games": 6500},
                ],
            },
            "last_updated": "2024-01-15T10:30:00",
            "source": "op.gg",
            "cached": False,
        }

        with patch('app.api.endpoints.opgg.get_opgg_scraper', return_value=mock_scraper):
            app = create_test_app()
            with TestClient(app) as client:
                response = client.get(
                    "/opgg/champions/ahri/build",
                    params={"counters_count": 3}
                )

                assert response.status_code == 200
                data = response.json()
                # Should be limited to 3
                assert len(data["data"]["matchups"]["counters"]) == 3
                # countered_by should be unchanged (2 < 3)
                assert len(data["data"]["matchups"]["countered_by"]) == 2

    def test_list_supported_champions(self):
        """Test listing supported champions."""
        app = create_test_app()
        with TestClient(app) as client:
            response = client.get("/opgg/champions")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert "ahri" in data

    def test_list_supported_regions(self):
        """Test listing supported regions."""
        app = create_test_app()
        with TestClient(app) as client:
            response = client.get("/opgg/regions")

            assert response.status_code == 200
            data = response.json()
            assert "regions" in data
            assert len(data["regions"]) > 0
            assert any(r["code"] == "kr" for r in data["regions"])
            assert any(r["name"] == "Korea" for r in data["regions"])

    def test_get_opgg_metrics(self, mock_settings, mock_scraper):
        """Test getting OP.GG metrics."""
        mock_settings.opgg_cache_ttl = 21600
        mock_settings.opgg_rate_limit_per_second = 2

        with patch('app.api.endpoints.opgg.get_opgg_scraper', return_value=mock_scraper):
            app = create_test_app()
            with TestClient(app) as client:
                response = client.get("/opgg/metrics")

                assert response.status_code == 200
                data = response.json()
                assert data["requests_total"] == 100
                assert data["requests_success"] == 90
                assert data["requests_failure"] == 10
                assert data["cache_hits"] == 50
                assert data["feature_enabled"] is True
                assert data["cache_ttl_seconds"] == 21600


class TestOPGGEndpointRetry:
    """Test retry logic in OP.GG endpoints."""

    @pytest.fixture
    def mock_settings(self):
        with patch('app.api.endpoints.opgg.settings') as mock:
            mock.opgg_enabled = True
            mock.opgg_max_retries = 2
            yield mock

    @pytest.fixture
    def mock_scraper(self):
        scraper = MagicMock()
        return scraper

    def test_retry_on_rate_limit(self, mock_settings, mock_scraper):
        """Test retry on rate limit with eventual success."""
        from app.services.opgg_scraper import OPGGRateLimitError

        call_count = 0

        async def mock_get_build(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OPGGRateLimitError("Rate limited", "ahri")
            return {
                "champion_name": "ahri",
                "win_rate": 52.34,
                "pick_rate": 15.2,
                "games_played": 125432,
                "roles": ["Mid"],
                "items": {"start": [], "core": [], "final": []},
                "skills": [],
                "runes": [],
                "matchups": {"counters": [], "countered_by": []},
                "last_updated": "2024-01-15T10:30:00",
                "source": "op.gg",
                "cached": False,
            }

        mock_scraper.get_champion_build = mock_get_build

        with patch('app.api.endpoints.opgg.get_opgg_scraper', return_value=mock_scraper):
            app = create_test_app()
            with TestClient(app) as client:
                response = client.get("/opgg/champions/ahri/build")

                assert response.status_code == 200
                assert call_count == 2

    def test_max_retries_exceeded(self, mock_settings, mock_scraper):
        """Test max retries exceeded returns 429."""
        from app.services.opgg_scraper import OPGGRateLimitError

        mock_scraper.get_champion_build.side_effect = OPGGRateLimitError(
            "Rate limited", "ahri"
        )

        with patch('app.api.endpoints.opgg.get_opgg_scraper', return_value=mock_scraper):
            app = create_test_app()
            with TestClient(app) as client:
                response = client.get("/opgg/champions/ahri/build")

                assert response.status_code == 429


class TestHealthEndpoints:
    """Test health/diagnostics endpoints."""

    def test_riot_health_missing_key(self):
        app = create_test_app()
        with patch("app.api.endpoints.health.settings") as mock_settings:
            mock_settings.riot_api_key = ""
            with TestClient(app) as client:
                response = client.get("/health/riot")
                assert response.status_code == 200
                data = response.json()
                assert data["ok"] is False
                assert data["reason"] == "missing_riot_api_key"

    def test_riot_health_connected(self):
        app = create_test_app()
        mock_riot_client = AsyncMock()
        mock_riot_client.__aenter__.return_value = mock_riot_client
        mock_riot_client.__aexit__.return_value = None
        mock_riot_client.get_puuid_by_riot_id = AsyncMock(return_value={"puuid": "x"})

        with patch("app.api.endpoints.health.settings") as mock_settings:
            mock_settings.riot_api_key = "RGAPI-12345678-xxxx"
            with patch("app.api.endpoints.health.get_riot_client", return_value=mock_riot_client):
                with TestClient(app) as client:
                    response = client.get("/health/riot")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["ok"] is True
                    assert data["reason"] == "connected"
                    assert data["key_prefix"] == "RGAPI-12..."

    def test_riot_health_unauthorized(self):
        app = create_test_app()
        mock_riot_client = AsyncMock()
        mock_riot_client.__aenter__.return_value = mock_riot_client
        mock_riot_client.__aexit__.return_value = None
        mock_riot_client.get_puuid_by_riot_id = AsyncMock(
            side_effect=RiotAPIError(401, "Invalid API key or forbidden")
        )

        with patch("app.api.endpoints.health.settings") as mock_settings:
            mock_settings.riot_api_key = "RGAPI-12345678-xxxx"
            with patch("app.api.endpoints.health.get_riot_client", return_value=mock_riot_client):
                with TestClient(app) as client:
                    response = client.get("/health/riot")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["ok"] is False
                    assert data["reason"] == "riot_api_error"
                    assert data["upstream_status"] == 401
