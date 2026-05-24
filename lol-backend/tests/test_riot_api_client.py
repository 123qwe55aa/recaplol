"""Tests for Riot API client."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.riot_api_client import RiotAPIClient, RiotAPIError, RateLimitError


class TestRiotAPIError:
    """Test RiotAPIError exception."""

    def test_riot_api_error_creation(self):
        """Test RiotAPIError creation."""
        error = RiotAPIError(404, "Not found")
        assert error.status_code == 404
        assert error.message == "Not found"
        assert str(error) == "RiotAPIError(404): Not found"

    def test_riot_api_error_format(self):
        """Test RiotAPIError string format."""
        error = RiotAPIError(403, "Invalid API key")
        assert "403" in str(error)
        assert "Invalid API key" in str(error)


class TestRiotAPIClient:
    """Test RiotAPIClient."""

    @pytest.fixture
    def client(self):
        """Create a client for testing."""
        return RiotAPIClient(api_key="test-api-key", timeout=30)

    @pytest.fixture
    def mock_response(self):
        """Create a mock httpx response."""
        def _create_response(status_code=200, json_data=None, headers=None):
            response = MagicMock(spec=httpx.Response)
            response.status_code = status_code
            response.headers = headers or {}
            if json_data is not None:
                response.json.return_value = json_data
            response.text = ""
            return response
        return _create_response

    class TestHandleResponse:
        """Test _handle_response method."""

        def test_handle_200_response(self, client, mock_response):
            """Test 200 response handling."""
            data = {"puuid": "test-puuid"}
            resp = mock_response(200, data)
            result = client._handle_response(resp)
            assert result == data

        def test_handle_404_response(self, client, mock_response):
            """Test 404 returns None."""
            resp = mock_response(404, None)
            result = client._handle_response(resp)
            assert result is None

        def test_handle_429_response(self, client, mock_response):
            """Test 429 raises RateLimitError."""
            resp = mock_response(429, None, {"Retry-After": "60"})
            with pytest.raises(RateLimitError):
                client._handle_response(resp)

        def test_handle_403_response(self, client, mock_response):
            """Test 403 raises RiotAPIError."""
            resp = mock_response(403, None)
            with pytest.raises(RiotAPIError) as exc_info:
                client._handle_response(resp)
            assert exc_info.value.status_code == 403

        def test_handle_401_response(self, client, mock_response):
            """Test 401 raises RiotAPIError for invalid/expired key."""
            resp = mock_response(401, None)
            with pytest.raises(RiotAPIError) as exc_info:
                client._handle_response(resp)
            assert exc_info.value.status_code == 401

        def test_handle_other_error(self, client, mock_response):
            """Test other status codes raise RiotAPIError."""
            resp = mock_response(500, None)
            with pytest.raises(RiotAPIError) as exc_info:
                client._handle_response(resp)
            assert exc_info.value.status_code == 500

    class TestClientContextManager:
        """Test client async context manager."""

        @pytest.mark.asyncio
        async def test_client_aenter(self):
            """Test client enters context."""
            client = RiotAPIClient(api_key="test-key")
            async with client as c:
                assert c._client is not None

        @pytest.mark.asyncio
        async def test_client_aexit(self):
            """Test client exits context."""
            client = RiotAPIClient(api_key="test-key")
            async with client as c:
                pass
            # Client should be closed after exiting

        @pytest.mark.asyncio
        async def test_get_without_initialization_raises(self, client):
            """Test _get raises if client not initialized."""
            with pytest.raises(RuntimeError):
                await client._get("http://example.com")

    class TestPlayerEndpoints:
        """Test player-related endpoints."""

        @pytest.mark.asyncio
        async def test_get_puuid_by_riot_id(self, mock_response):
            """Test get_puuid_by_riot_id."""
            client = RiotAPIClient(api_key="test-key")
            mock_json = {"puuid": "test-puuid-123", "gameName": "TestPlayer", "tagLine": "NA1"}

            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_json
                result = await client.get_puuid_by_riot_id("TestPlayer", "NA1")

                mock_get.assert_called_once()
                assert result == mock_json

        @pytest.mark.asyncio
        async def test_get_puuid_by_riot_id_not_found(self, mock_response):
            """Test get_puuid_by_riot_id when not found."""
            client = RiotAPIClient(api_key="test-key")

            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = None
                result = await client.get_puuid_by_riot_id("Unknown", "NA1")
                assert result is None

        @pytest.mark.asyncio
        async def test_get_summoner_by_puuid(self, mock_response):
            """Test get_summoner_by_puuid."""
            client = RiotAPIClient(api_key="test-key")
            mock_json = {"id": "summoner-123", "puuid": "test-puuid", "name": "TestPlayer", "level": 50}

            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_json
                result = await client.get_summoner_by_puuid("test-puuid")

                assert result == mock_json
                mock_get.assert_called_once()

        @pytest.mark.asyncio
        async def test_get_summoner_by_name(self, mock_response):
            """Test get_summoner_by_name."""
            client = RiotAPIClient(api_key="test-key")
            mock_json = {"id": "summoner-123", "name": "TestPlayer", "level": 50}

            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_json
                result = await client.get_summoner_by_name("TestPlayer")

                assert result == mock_json

        @pytest.mark.asyncio
        async def test_get_player_ranked_stats(self, mock_response):
            """Test get_player_ranked_stats."""
            client = RiotAPIClient(api_key="test-key")
            mock_json = [
                {"queueType": "RANKED_SOLO_5x5", "tier": "GOLD", "rank": "I", "leaguePoints": 75}
            ]

            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_json
                result = await client.get_player_ranked_stats("summoner-123")

                assert result == mock_json

    class TestMatchEndpoints:
        """Test match-related endpoints."""

        @pytest.mark.asyncio
        async def test_get_match_ids_by_puuid(self, mock_response):
            """Test get_match_ids_by_puuid."""
            client = RiotAPIClient(api_key="test-key")
            mock_json = ["NA1_111", "NA1_222", "NA1_333"]

            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_json
                result = await client.get_match_ids_by_puuid("test-puuid", start=0, count=20)

                assert result == mock_json
                assert len(result) == 3

        @pytest.mark.asyncio
        async def test_get_match_ids_by_puuid_with_queue_filter(self, mock_response):
            """Test get_match_ids_by_puuid with queue filter."""
            client = RiotAPIClient(api_key="test-key")
            mock_json = ["NA1_111"]

            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_json
                result = await client.get_match_ids_by_puuid(
                    "test-puuid", queue=420  # RANKED_SOLO_5x5
                )

                assert result == mock_json

        @pytest.mark.asyncio
        async def test_get_match_ids_empty(self, mock_response):
            """Test get_match_ids_by_puuid returns empty list when no matches."""
            client = RiotAPIClient(api_key="test-key")

            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = None
                result = await client.get_match_ids_by_puuid("test-puuid")

                assert result == []

        @pytest.mark.asyncio
        async def test_get_match(self, mock_response):
            """Test get_match."""
            client = RiotAPIClient(api_key="test-key")
            mock_json = {
                "metadata": {"matchId": "NA1_1234567890"},
                "info": {"gameDuration": 1800}
            }

            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_json
                result = await client.get_match("NA1_1234567890")

                assert result["metadata"]["matchId"] == "NA1_1234567890"

        @pytest.mark.asyncio
        async def test_get_match_timeline(self, mock_response):
            """Test get_match_timeline."""
            client = RiotAPIClient(api_key="test-key")
            mock_json = {
                "metadata": {"matchId": "NA1_1234567890"},
                "info": {"frameInterval": 60000}
            }

            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_json
                result = await client.get_match_timeline("NA1_1234567890")

                assert result["info"]["frameInterval"] == 60000

    class TestChampionMasteryEndpoints:
        """Test champion mastery endpoints."""

        @pytest.mark.asyncio
        async def test_get_champion_masteries(self, mock_response):
            """Test get_champion_masteries."""
            client = RiotAPIClient(api_key="test-key")
            mock_json = [
                {"championId": 103, "championLevel": 7, "championPoints": 500000},
                {"championId": 1, "championLevel": 5, "championPoints": 200000},
            ]

            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_json
                result = await client.get_champion_masteries("summoner-123")

                assert len(result) == 2
                assert result[0]["championId"] == 103

        @pytest.mark.asyncio
        async def test_get_champion_masteries_empty(self, mock_response):
            """Test get_champion_masteries returns empty list."""
            client = RiotAPIClient(api_key="test-key")

            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = None
                result = await client.get_champion_masteries("summoner-123")

                assert result == []

        @pytest.mark.asyncio
        async def test_get_champion_mastery_by_champion(self, mock_response):
            """Test get_champion_mastery_by_champion."""
            client = RiotAPIClient(api_key="test-key")
            mock_json = {"championId": 103, "championLevel": 7, "championPoints": 500000}

            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_json
                result = await client.get_champion_mastery_by_champion("summoner-123", 103)

                assert result["championId"] == 103
                assert result["championLevel"] == 7

    class TestStatusEndpoints:
        """Test LoL status endpoints."""

        @pytest.mark.asyncio
        async def test_get_lol_status_uses_platform_routing(self):
            """Test get_lol_status uses platform-specific routing."""
            client = RiotAPIClient(api_key="test-key")
            mock_json = {
                "id": "TW2",
                "name": "Taiwan",
                "locales": ["zh_TW"],
                "maintenances": [],
                "incidents": [],
            }

            with patch.object(client, '_get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_json
                result = await client.get_lol_status("tw2")

                assert result == mock_json
                mock_get.assert_called_once_with(
                    "https://tw2.api.riotgames.com/lol/status/v4/platform-data"
                )


class TestGetRiotClient:
    """Test get_riot_client function."""

    def test_get_riot_client_creation(self):
        """Test get_riot_client creates client with settings."""
        from app.services.riot_api_client import get_riot_client
        from app.core.config import settings

        client = get_riot_client()
        assert client.api_key == settings.riot_api_key
        assert client.timeout == settings.riot_api_timeout
