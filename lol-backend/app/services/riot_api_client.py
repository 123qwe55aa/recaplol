import httpx
from typing import Any, Optional, Dict, List
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger(__name__)


class RateLimitError(Exception):
    """Custom exception for rate limit errors from Riot API."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class RiotAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"RiotAPIError({status_code}): {message}")


class RiotAPIClient:
    BASE_URL = "https://americas.api.riotgames.com"
    REGION_URL = "https://na1.api.riotgames.com"

    # Regional base URLs for account API
    REGIONAL_URLS = {
        "americas": "https://americas.api.riotgames.com",
        "europe": "https://europe.api.riotgames.com",
        "asia": "https://asia.api.riotgames.com",
        "sea": "https://sea.api.riotgames.com",
    }

    # Map tag lines to platform-specific base URLs for summoner/ranked/match APIs
    TAG_TO_PLATFORM = {
        "na1": "https://na1.api.riotgames.com",
        "br1": "https://br1.api.riotgames.com",
        "la1": "https://la1.api.riotgames.com",
        "la2": "https://la2.api.riotgames.com",
        "euw1": "https://euw1.api.riotgames.com",
        "eune1": "https://eune1.api.riotgames.com",
        "tr1": "https://tr1.api.riotgames.com",
        "ru": "https://ru.api.riotgames.com",
        "kr": "https://kr.api.riotgames.com",
        "jp1": "https://jp1.api.riotgames.com",
        "tw2": "https://tw2.api.riotgames.com",
        "sg2": "https://sg2.api.riotgames.com",
        "ph2": "https://ph2.api.riotgames.com",
        "th2": "https://th2.api.riotgames.com",
        "vn2": "https://vn2.api.riotgames.com",
        "my2": "https://my2.api.riotgames.com",
        "id2": "https://id2.api.riotgames.com",
    }

    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            headers={"X-Riot-Token": self.api_key},
            timeout=httpx.Timeout(self.timeout),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    @staticmethod
    def _handle_response(response: httpx.Response) -> Any:
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise RateLimitError(
                f"Rate limited, retry after {retry_after}s"
            )
        elif response.status_code == 403:
            raise RiotAPIError(403, "Invalid API key or forbidden")
        else:
            raise RiotAPIError(
                response.status_code,
                response.text or "Unknown error",
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RateLimitError),
    )
    async def _get(self, url: str) -> Optional[Dict]:
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        try:
            logger.debug("riot_api_request", method="GET", url=url)
            response = await self._client.get(url)
            return self._handle_response(response)
        except RateLimitError:
            logger.warning("riot_api_rate_limited", url=url)
            raise
        except Exception as e:
            logger.error("riot_api_error", url=url, error=str(e))
            raise

    # Account endpoint (uses regional routing)
    async def get_puuid_by_riot_id(
        self, game_name: str, tag_line: str
    ) -> Optional[Dict]:
        url = f"{self.BASE_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        data = await self._get(url)
        return data if data else None

    async def get_puuid_by_summoner_id(self, summoner_id: str) -> Optional[str]:
        url = f"{self.REGION_URL}/lol/summoner/v4/summoners/{summoner_id}"
        data = await self._get(url)
        return data.get("puuid") if data else None

    # Summoner/ranked/champion-mastery endpoints (use platform routing)
    async def get_summoner_by_puuid(self, puuid: str, tag_line: str = "na1") -> Optional[Dict]:
        base = self.TAG_TO_PLATFORM.get(tag_line.lower(), self.REGION_URL)
        url = f"{base}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        return await self._get(url)

    async def get_summoner_by_name(self, summoner_name: str) -> Optional[Dict]:
        url = f"{self.REGION_URL}/lol/summoner/v4/summoners/by-name/{summoner_name}"
        return await self._get(url)

    async def get_player_ranked_stats(self, encrypted_id: str, tag_line: str = "na1") -> Optional[Dict]:
        base = self.TAG_TO_PLATFORM.get(tag_line.lower(), self.REGION_URL)
        url = f"{base}/lol/league/v4/entries/by-summoner/{encrypted_id}"
        return await self._get(url)

    async def get_challenger_league(self, queue: str = "RANKED_SOLO_5x5") -> Optional[Dict]:
        url = f"{self.REGION_URL}/lol/league/v4/challengerleagues/by-queue/{queue}"
        return await self._get(url)

    async def get_grandmaster_league(self, queue: str = "RANKED_SOLO_5x5") -> Optional[Dict]:
        url = f"{self.REGION_URL}/lol/league/v4/grandmasterleagues/by-queue/{queue}"
        return await self._get(url)

    async def get_master_league(self, queue: str = "RANKED_SOLO_5x5") -> Optional[Dict]:
        url = f"{self.REGION_URL}/lol/league/v4/masterleagues/by-queue/{queue}"
        return await self._get(url)

    # Match endpoints (use regional routing for Americas/Europe/Asia/SEA)
    async def get_match_ids_by_puuid(
        self,
        puuid: str,
        start: int = 0,
        count: int = 20,
        queue: Optional[int] = None,
        type: Optional[str] = None,
        region: Optional[str] = None,
    ) -> List[str]:
        base_url = self.BASE_URL
        if region:
            base_url = self.REGIONAL_URLS.get(region.lower(), self.BASE_URL)
        url = f"{base_url}/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"start": start, "count": count}
        if queue:
            params["queue"] = queue
        if type:
            params["type"] = type
        data = await self._get(url)
        return data or []

    async def get_match(self, match_id: str) -> Optional[Dict]:
        url = f"{self.BASE_URL}/lol/match/v5/matches/{match_id}"
        return await self._get(url)

    async def get_match_with_region(
        self, match_id: str, region_base: str
    ) -> Optional[Dict]:
        """Fetch match from a specific regional URL."""
        url = f"{region_base}/lol/match/v5/matches/{match_id}"
        return await self._get(url)

    async def get_match_timeline(self, match_id: str) -> Optional[Dict]:
        url = f"{self.BASE_URL}/lol/match/v5/matches/{match_id}/timeline"
        return await self._get(url)

    async def get_match_timeline_with_region(
        self, match_id: str, region_base: str
    ) -> Optional[Dict]:
        """Fetch match timeline from a specific regional URL."""
        url = f"{region_base}/lol/match/v5/matches/{match_id}/timeline"
        return await self._get(url)

    # Champion Mastery endpoints (use platform routing)
    async def get_champion_masteries(
        self, encrypted_summoner_id: str, tag_line: str = "na1"
    ) -> List[Dict]:
        base = self.TAG_TO_PLATFORM.get(tag_line.lower(), self.REGION_URL)
        url = f"{base}/lol/champion-mastery/v4/champion-masteries/by-summoner/{encrypted_summoner_id}"
        data = await self._get(url)
        return data or []

    async def get_champion_mastery_by_champion(
        self, encrypted_summoner_id: str, champion_id: int, tag_line: str = "na1"
    ) -> Optional[Dict]:
        base = self.TAG_TO_PLATFORM.get(tag_line.lower(), self.REGION_URL)
        url = f"{base}/lol/champion-mastery/v4/champion-masteries/by-summoner/{encrypted_summoner_id}/by-champion/{champion_id}"
        return await self._get(url)


def get_riot_client() -> RiotAPIClient:
    return RiotAPIClient(settings.riot_api_key, settings.riot_api_timeout)
