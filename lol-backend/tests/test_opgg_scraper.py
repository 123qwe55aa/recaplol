"""Tests for OP.GG scraper service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.opgg_scraper import (
    OPGGScraper,
    OPGGError,
    OPGGRateLimitError,
    OPGGNotFoundError,
    OPGGParseError,
)


# Sample HTML fixtures for testing parse methods
SAMPLE_BUILD_PAGE_HTML = """
<html>
<body>
    <div class="champion-stats-trend-rate">52.34%</div>
    <div class="pick-rate">15.2%</div>
    <div class="games">125,432</div>
    <div class="role-badge">Mid</div>
    <div class="role-badge">Support</div>
    <img class="item-image" alt="Infinity Edge" data-item-id="6672" />
    <img class="item-image" alt="Lord Dominik's Regards" data-item-id="6673" />
    <img class="item-image" alt="The Collector" data-item-id="6675" />
    <div class="skill-order">Q &gt; W &gt; E</div>
    <img class="rune-image" alt="Arcane Comet" />
    <img class="rune-image" alt="Nullifying Orb" />
</body>
</html>
"""

SAMPLE_BUILD_PAGE_WITH_FULL_RUNES_HTML = """
<html>
<body>
    <div class="champion-stats-trend-rate">52.34%</div>
    <img class="rune-image" alt="Conqueror" />
    <img class="rune-image" alt="Triumph" />
    <img class="rune-image" alt="Legend: Alacrity" />
    <img class="rune-image" alt="Coup de Grace" />
    <img class="rune-image" alt="Taste of Blood" />
    <img class="rune-image" alt="Treasure Hunter" />
</body>
</html>
"""

SAMPLE_VS_PAGE_HTML = """
<html>
<body>
    <table class="counter-list">
        <tr class="counter-item">
            <td class="champion-name">Zed</td>
            <td class="win-rate">45.2%</td>
            <td class="games">12,345</td>
        </tr>
        <tr class="counter-item">
            <td class="champion-name">Yasuo</td>
            <td class="win-rate">48.7%</td>
            <td class="games">8,921</td>
        </tr>
        <tr class="counter-item">
            <td class="champion-name">Akali</td>
            <td class="win-rate">53.1%</td>
            <td class="games">7,654</td>
        </tr>
    </table>
</body>
</html>
"""

SAMPLE_CURRENT_COUNTERS_PAGE_HTML = """
<html>
<body>
    <ul class="border-t border-t-gray-200">
        <li class="cursor-pointer bg-gray-0 hover:bg-gray-100 border-b border-gray-200 flex">
            <img alt="Smolder" src="/champion/Smolder.png" />
            <span>Smolder</span>
            <span>43.62</span><span>%</span>
            <span>10,509</span>
        </li>
        <li class="cursor-pointer bg-gray-0 hover:bg-gray-100 border-b border-gray-200 flex">
            <img alt="Corki" src="/champion/Corki.png" />
            <span>Corki</span>
            <span>52.8</span><span>%</span>
            <span>928</span>
        </li>
    </ul>
</body>
</html>
"""

SAMPLE_SYNERGIES_PAGE_HTML = """
<html>
<body>
    <table>
        <thead>
            <tr><th></th><th>Pick rate</th><th>Win rate</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><img alt="Lulu" src="/champion/Lulu.png" /><span>Lulu</span></td>
                <td><strong>12.4%</strong></td>
                <td><strong>56.7%</strong></td>
            </tr>
            <tr>
                <td><img alt="Nami" src="/champion/Nami.png" /><span>Nami</span></td>
                <td><strong>9.8%</strong></td>
                <td><strong>54.2%</strong></td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""

SAMPLE_UGG_DUOS_PAYLOAD = [
    {
        "adc_supp": [
            [81, 3, 0, 0, 117, 2, 0, 0, 567, 1000, 1.23, None, None],   # Ezreal + Lulu => 56.7%
            [117, 2, 0, 0, 81, 3, 0, 0, 530, 1000, 1.12, None, None],   # duplicate reversed
            [81, 3, 0, 0, 267, 2, 0, 0, 492, 1000, 0.91, None, None],   # Ezreal + Nami => 49.2%
        ],
        "mid_jungle": [],
        "jungle_supp": [],
        "top_jungle": [],
    },
    "16_10",
    0.0,
    0,
]

SAMPLE_EMPTY_PAGE_HTML = """
<html>
<body>
    <div class="no-data">No statistics available</div>
</body>
</html>
"""


class TestOPGGScraper:
    """Test OPGGScraper class."""

    @pytest.fixture
    def scraper(self):
        """Create a scraper instance for testing."""
        return OPGGScraper(
            timeout=30,
            rate_limit_per_second=2,
            cache_ttl=3600,
        )

    @pytest.fixture
    def filters(self):
        """Sample filters dict."""
        return {
            "champ_slug": "ahri",
            "region": "kr",
            "queue": "RANKED_SOLO_5x5",
            "tier": "overall",
            "version": None,
        }

    # Test URL building
    def test_build_url_kr(self, scraper):
        """Test building URL for Korean server."""
        url = scraper._build_url("ahri", "kr", "RANKED_SOLO_5x5", "overall", None)
        assert url == "https://op.gg/champions/ahri/build?queue=solo"

    def test_build_url_with_queue(self, scraper):
        """Test building URL with different queue type."""
        url = scraper._build_url("ahri", "na", "RANKED_FLEX_SR", "diamond", None)
        assert "queue=flex" in url
        assert "tier=diamond" in url
        assert "na.op.gg" in url

    def test_build_url_with_version(self, scraper):
        """Test building URL with patch version."""
        url = scraper._build_url("ahri", "kr", "RANKED_SOLO_5x5", "overall", "14.1")
        assert "patch=14.1" in url

    def test_build_vs_url(self, scraper):
        """Test building VS (counters) URL."""
        url = scraper._build_vs_url("ahri", "euw", "RANKED_SOLO_5x5", "platinum")
        assert "euw.op.gg" in url
        assert "lol/champions/ahri/counters" in url
        assert "queue=solo" in url

    # Test parsing methods
    def test_parse_win_rate_valid(self, scraper):
        """Test parsing valid win rate."""
        assert scraper._parse_win_rate("52.34%") == 52.34
        assert scraper._parse_win_rate('45.5%') == 45.5
        assert scraper._parse_win_rate("50%") == 50.0

    def test_parse_win_rate_invalid(self, scraper):
        """Test parsing invalid win rate returns None."""
        assert scraper._parse_win_rate("") is None
        assert scraper._parse_win_rate("N/A") is None
        assert scraper._parse_win_rate("abc") is None

    def test_parse_build_page(self, scraper, filters):
        """Test parsing build page HTML."""
        result = scraper._parse_build_page(SAMPLE_BUILD_PAGE_HTML, filters)

        assert result["champion_name"] == "ahri"
        assert result["win_rate"] == 52.34
        assert result["pick_rate"] == 15.2
        assert result["games_played"] == 125432
        assert "Mid" in result["roles"]
        assert len(result["items"]["core"]) == 3
        assert result["items"]["core"][0]["name"] == "Infinity Edge"

    def test_parse_build_page_fallback_selectors(self, scraper, filters):
        """Test parsing with fallback selectors."""
        html = """
        <html><body>
            <div class="stats-value">51.5%</div>
        </body></html>
        """
        result = scraper._parse_build_page(html, filters)
        assert result["win_rate"] == 51.5

    def test_parse_build_page_no_data(self, scraper, filters):
        """Test parsing page with no data."""
        result = scraper._parse_build_page(SAMPLE_EMPTY_PAGE_HTML, filters)

        assert result["win_rate"] is None
        assert result["pick_rate"] is None
        assert result["games_played"] is None
        assert result["items"]["core"] == []

    def test_parse_build_page_extracts_structured_rune_setup(self, scraper, filters):
        """Test parse_build_page extracts primary/secondary rune setup from OP.GG rune order."""
        result = scraper._parse_build_page(SAMPLE_BUILD_PAGE_WITH_FULL_RUNES_HTML, filters)
        assert result["rune_setup"] == {
            "primary_runes": ["Conqueror", "Triumph", "Legend: Alacrity", "Coup de Grace"],
            "secondary_runes": ["Taste of Blood", "Treasure Hunter"],
        }

    def test_parse_vs_page(self, scraper, filters):
        """Test parsing VS (counter matchups) page."""
        result = scraper._parse_vs_page(SAMPLE_VS_PAGE_HTML, filters)

        # Zed and Yasuo have <50% win rate from Ahri's perspective (they counter Ahri)
        assert len(result["counters"]) == 2
        assert result["counters"][0]["champion_name"] == "Zed"
        assert result["counters"][0]["win_rate"] == 45.2

        # Akali has >50% win rate (Ahri beats Akali)
        assert len(result["countered_by"]) == 1
        assert result["countered_by"][0]["champion_name"] == "Akali"
        assert result["countered_by"][0]["win_rate"] == 53.1

    def test_parse_vs_page_no_counters(self, scraper, filters):
        """Test parsing VS page with no counters."""
        result = scraper._parse_vs_page(SAMPLE_EMPTY_PAGE_HTML, filters)
        assert result["counters"] == []
        assert result["countered_by"] == []

    def test_parse_current_counters_page_list(self, scraper, filters):
        """Test parsing current OP.GG counters list markup."""
        result = scraper._parse_vs_page(SAMPLE_CURRENT_COUNTERS_PAGE_HTML, filters)

        assert result["counters"][0]["champion_name"] == "Smolder"
        assert result["counters"][0]["win_rate"] == 43.62
        assert result["counters"][0]["games"] == 10509
        assert result["countered_by"][0]["champion_name"] == "Corki"
        assert result["countered_by"][0]["win_rate"] == 52.8
        assert result["countered_by"][0]["games"] == 928

    def test_parse_synergies_page(self, scraper, filters):
        """Test parsing OP.GG champion synergy table."""
        result = scraper._parse_synergies_page(SAMPLE_SYNERGIES_PAGE_HTML, filters)

        assert result[0]["champion_name"] == "Lulu"
        assert result[0]["pick_rate"] == 12.4
        assert result[0]["win_rate"] == 56.7
        assert result[1]["champion_name"] == "Nami"

    def test_parse_ugg_duos_payload(self, scraper):
        """Test parsing U.GG duos payload for a champion."""
        champ_map = {
            81: "Ezreal",
            117: "Lulu",
            267: "Nami",
        }
        result = scraper._parse_ugg_duos_payload(SAMPLE_UGG_DUOS_PAYLOAD, 81, champ_map)
        assert result[0]["champion_name"] == "Lulu"
        assert result[0]["win_rate"] == 56.7
        assert result[0]["games"] == 1000
        assert result[1]["champion_name"] == "Nami"

    # Test cache key generation
    def test_get_cache_key_deterministic(self, scraper):
        """Test that cache keys are deterministic."""
        filters1 = {"region": "kr", "queue": "RANKED_SOLO_5x5", "tier": "overall"}
        filters2 = {"region": "kr", "queue": "RANKED_SOLO_5x5", "tier": "overall"}

        key1 = scraper._get_cache_key("ahri", filters1)
        key2 = scraper._get_cache_key("ahri", filters2)

        assert key1 == key2

    def test_get_cache_key_different_filters(self, scraper):
        """Test that different filters produce different cache keys."""
        filters1 = {"region": "kr", "queue": "RANKED_SOLO_5x5", "tier": "overall"}
        filters2 = {"region": "na", "queue": "RANKED_SOLO_5x5", "tier": "overall"}

        key1 = scraper._get_cache_key("ahri", filters1)
        key2 = scraper._get_cache_key("ahri", filters2)

        assert key1 != key2

    # Test metrics
    def test_get_metrics_initial(self, scraper):
        """Test metrics before any requests."""
        metrics = scraper.get_metrics()

        assert metrics["requests_total"] == 0
        assert metrics["requests_success"] == 0
        assert metrics["requests_failure"] == 0
        assert metrics["cache_hits"] == 0

    # Test exception classes
    def test_opgg_error_attributes(self):
        """Test OPGGError exception attributes."""
        error = OPGGError("Test error", "ahri", {"region": "kr"})
        assert error.message == "Test error"
        assert error.champ_slug == "ahri"
        assert error.filters == {"region": "kr"}

    def test_opgg_rate_limit_error(self):
        """Test OPGGRateLimitError inheritance."""
        error = OPGGRateLimitError("Rate limited", "ahri")
        assert isinstance(error, OPGGError)

    def test_opgg_not_found_error(self):
        """Test OPGGNotFoundError inheritance."""
        error = OPGGNotFoundError("Champion not found", "unknown")
        assert isinstance(error, OPGGError)

    def test_opgg_parse_error(self):
        """Test OPGGParseError inheritance."""
        error = OPGGParseError("Parse failed", "ahri")
        assert isinstance(error, OPGGError)


class TestOPGGScraperIntegration:
    """Integration tests for OPGGScraper with mocked HTTP responses."""

    @pytest.fixture
    def mock_client(self):
        """Create mock httpx AsyncClient."""
        client = AsyncMock()
        client.get = AsyncMock()
        client.aclose = AsyncMock()
        return client

    @pytest.fixture
    def scraper_with_mock(self, mock_client):
        """Create scraper with mock client."""
        scraper = OPGGScraper()
        scraper._client = mock_client
        return scraper

    @pytest.mark.asyncio
    async def test_fetch_page_success(self, scraper_with_mock, mock_client):
        """Test successful page fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_BUILD_PAGE_HTML
        mock_client.get.return_value = mock_response

        result = await scraper_with_mock._fetch_page(
            "https://op.gg/champions/ahri/build",
            "ahri",
            {"region": "kr"}
        )

        assert result == SAMPLE_BUILD_PAGE_HTML
        assert scraper_with_mock._success_count == 1

    @pytest.mark.asyncio
    async def test_fetch_page_initializes_client_if_missing(self):
        """Test fetch page lazily initializes HTTP client."""
        scraper = OPGGScraper()
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_BUILD_PAGE_HTML
        mock_client.get.return_value = mock_response

        with patch("app.services.opgg_scraper.httpx.AsyncClient", return_value=mock_client):
            result = await scraper._fetch_page(
                "https://op.gg/champions/ahri/build",
                "ahri",
                {"region": "kr"},
            )

        assert result == SAMPLE_BUILD_PAGE_HTML
        assert scraper._client is mock_client

    @pytest.mark.asyncio
    async def test_fetch_page_rate_limited(self, scraper_with_mock, mock_client):
        """Test rate limited response."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_client.get.return_value = mock_response

        with pytest.raises(OPGGRateLimitError):
            await scraper_with_mock._fetch_page(
                "https://op.gg/champions/ahri/build",
                "ahri",
                {}
            )

        assert scraper_with_mock._failure_count == 1

    @pytest.mark.asyncio
    async def test_fetch_page_not_found(self, scraper_with_mock, mock_client):
        """Test 404 response."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response

        with pytest.raises(OPGGNotFoundError):
            await scraper_with_mock._fetch_page(
                "https://op.gg/champions/unknown/build",
                "unknown",
                {}
            )

        assert scraper_with_mock._failure_count == 1

    @pytest.mark.asyncio
    async def test_get_champion_build_success(self, scraper_with_mock, mock_client):
        """Test successful champion build retrieval."""
        # Mock build page response
        mock_build_response = MagicMock()
        mock_build_response.status_code = 200
        mock_build_response.text = SAMPLE_BUILD_PAGE_HTML

        # Mock VS page response
        mock_vs_response = MagicMock()
        mock_vs_response.status_code = 200
        mock_vs_response.text = SAMPLE_VS_PAGE_HTML

        mock_client.get.side_effect = [mock_build_response, mock_vs_response]

        with patch.object(scraper_with_mock, '_set_cache', new_callable=AsyncMock):
            result = await scraper_with_mock.get_champion_build(
                champ_slug="ahri",
                region="kr",
                queue="RANKED_SOLO_5x5",
                tier="overall",
                use_cache=False,
            )

        assert result["champion_name"] == "ahri"
        assert result["win_rate"] == 52.34
        assert "counters" in result["matchups"]
        assert "countered_by" in result["matchups"]
        assert result["cached"] is False

    @pytest.mark.asyncio
    async def test_get_champion_build_uses_ugg_when_opgg_synergies_empty(self, scraper_with_mock):
        """Should fill synergies from U.GG when OP.GG returns none."""
        build_data = {
            "champion_name": "ezreal",
            "win_rate": 50.0,
            "pick_rate": 20.0,
            "games_played": 1000,
            "roles": [],
            "items": {"start": [], "core": [], "final": []},
            "skills": [],
            "runes": [],
            "matchups": {"counters": [], "countered_by": []},
            "synergies": [],
            "last_updated": datetime.now().isoformat(),
            "source": "op.gg",
        }

        with patch.object(scraper_with_mock, "_fetch_page", new_callable=AsyncMock) as mock_fetch, \
             patch.object(scraper_with_mock, "_parse_build_page", return_value=build_data), \
             patch.object(scraper_with_mock, "_parse_vs_page", return_value={"counters": [], "countered_by": []}), \
             patch.object(scraper_with_mock, "_fetch_synergies_with_fallbacks", new_callable=AsyncMock, return_value=[]), \
             patch.object(scraper_with_mock, "_fetch_ugg_synergies_fallback", new_callable=AsyncMock, return_value=[{"champion_name": "Lulu", "win_rate": 56.7, "pick_rate": None, "games": 1000}]), \
             patch.object(scraper_with_mock, "_set_cache", new_callable=AsyncMock):
            mock_fetch.return_value = "<html></html>"
            result = await scraper_with_mock.get_champion_build("ezreal", use_cache=False)

        assert result["synergies"][0]["champion_name"] == "Lulu"

    @pytest.mark.asyncio
    async def test_get_champion_build_cache_hit(self, scraper_with_mock):
        """Test cache hit returns cached data."""
        cached_data = {
            "champion_name": "ahri",
            "win_rate": 52.34,
            "cached": False,
        }

        with patch.object(scraper_with_mock, '_get_from_cache', new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = cached_data

            result = await scraper_with_mock.get_champion_build(
                champ_slug="ahri",
                region="kr",
                use_cache=True,
            )

        assert result["cached"] is True
        assert result["win_rate"] == 52.34
        assert scraper_with_mock._cache_hit_count == 1

    @pytest.mark.asyncio
    async def test_rate_limiting(self, scraper_with_mock, mock_client):
        """Test rate limiting enforcement."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html></html>"
        mock_client.get.return_value = mock_response

        # Make multiple rapid requests
        scraper_with_mock.rate_limit_per_second = 2

        import asyncio
        start = datetime.now()

        for _ in range(3):
            await scraper_with_mock._fetch_page(
                "https://op.gg/champions/ahri/build",
                "ahri",
                {}
            )

        elapsed = (datetime.now() - start).total_seconds()

        # With rate limit of 2/sec and 3 requests, should take at least 0.5 seconds
        assert elapsed >= 0.4  # Allow some tolerance


class TestOPGGCache:
    """Test caching functionality."""

    @pytest.fixture
    def scraper(self):
        return OPGGScraper(cache_ttl=3600)

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, scraper):
        """Test setting and getting cache."""
        test_data = {"champion_name": "ahri", "win_rate": 52.0}

        with patch('redis.asyncio.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.get.return_value = '{"champion_name": "ahri", "win_rate": 52.0}'

            result = await scraper._get_from_cache("test_key")

        assert result is not None
        assert result["win_rate"] == 52.0

    @pytest.mark.asyncio
    async def test_cache_miss(self, scraper):
        """Test cache miss returns None."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.get.return_value = None

            result = await scraper._get_from_cache("nonexistent_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_error_handling(self, scraper):
        """Test cache errors are handled gracefully."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")

            result = await scraper._get_from_cache("test_key")

        assert result is None  # Should return None, not raise


class TestOPGGRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_wait(self):
        """Test rate limiter enforces delay."""
        scraper = OPGGScraper(rate_limit_per_second=1)

        import asyncio

        async def run_test():
            times = []
            for _ in range(3):
                await scraper._rate_limit()
                times.append(datetime.now())

            # Check intervals
            for i in range(1, len(times)):
                interval = (times[i] - times[i-1]).total_seconds()
                # With 1 req/sec, should have ~1 second between requests
                # Allow some tolerance
                assert interval >= 0.9

        asyncio.run(run_test())

    def test_rate_limit_reset(self):
        """Test rate limit counter resets after window."""
        scraper = OPGGScraper(rate_limit_per_second=2)

        import asyncio

        async def run_test():
            # Fill up the bucket
            for _ in range(2):
                await scraper._rate_limit()

            # Counter should be at limit
            assert scraper._request_count == 2

            # Manually reset window
            scraper._window_start = datetime.now() - timedelta(seconds=2)

            # Should allow requests again
            await scraper._rate_limit()
            assert scraper._request_count == 1

        asyncio.run(run_test())
