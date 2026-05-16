"""OP.GG scraper service for champion builds, counters, and win rates."""
import httpx
import asyncio
import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import structlog

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OPGGError(Exception):
    """Base exception for OP.GG related errors."""
    def __init__(self, message: str, champ_slug: str = "", filters: Dict[str, Any] | None = None):
        self.message = message
        self.champ_slug = champ_slug
        self.filters = filters or {}
        super().__init__(message)


class OPGGRateLimitError(OPGGError):
    """Raised when OP.GG rate limits us."""
    pass


class OPGGParseError(OPGGError):
    """Raised when OP.GG page structure doesn't match expected format."""
    pass


class OPGGNotFoundError(OPGGError):
    """Raised when champion is not found on OP.GG."""
    pass


class OPGGScraper:
    """Scraper for OP.GG champion data including builds, counters, and win rates."""

    # OP.GG base URLs (supports multiple regions)
    BASE_URLS = {
        "kr": "https://op.gg",
        "na": "https://na.op.gg",
        "euw": "https://euw.op.gg",
        "eune": "https://eune.op.gg",
        "jp": "https://jp.op.gg",
        "oce": "https://oce.op.gg",
        "ru": "https://ru.op.gg",
        "br": "https://br.op.gg",
        "las": "https://las.op.gg",
        "lan": "https://lan.op.gg",
        "tr": "https://tr.op.gg",
        "sg": "https://sg.op.gg",
        "my": "https://my.op.gg",
        "ph": "https://ph.op.gg",
        "th": "https://th.op.gg",
        "tw": "https://tw.op.gg",
        "vn": "https://vn.op.gg",
    }

    # Default headers to mimic browser
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    def __init__(
        self,
        timeout: int = 2,
        rate_limit_per_second: int = 2,
        cache_ttl: int = 21600,  # 6 hours default
    ):
        self.timeout = timeout
        self.rate_limit_per_second = rate_limit_per_second
        self.cache_ttl = cache_ttl
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_time: float = 0
        self._lock = asyncio.Lock()
        self._request_count = 0
        self._window_start = datetime.now()

        # Metrics
        self._success_count = 0
        self._failure_count = 0
        self._cache_hit_count = 0

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            headers=self.HEADERS,
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        async with self._lock:
            now = datetime.now()
            # Reset counter every second
            if (now - self._window_start).total_seconds() >= 1.0:
                self._request_count = 0
                self._window_start = now

            if self._request_count >= self.rate_limit_per_second:
                wait_time = 1.0 - (now - self._window_start).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                self._request_count = 0
                self._window_start = datetime.now()

            self._request_count += 1

    def _get_cache_key(self, champ_slug: str, filters: Dict[str, Any]) -> str:
        """Generate cache key for request."""
        key_data = f"{champ_slug}:{json.dumps(filters, sort_keys=True)}"
        return f"opgg:champion:{hashlib.md5(key_data.encode()).hexdigest()}"

    async def _fetch_page(self, url: str, champ_slug: str, filters: Dict[str, Any]) -> str:
        """Fetch a page with rate limiting and retry logic."""
        await self._rate_limit()

        try:
            logger.debug("opgg_request_start", url=url, champ_slug=champ_slug)
            response = await self._client.get(url)
            elapsed_ms = 0  # Would need to track this properly

            if response.status_code == 200:
                self._success_count += 1
                logger.info(
                    "opgg_request_success",
                    url=url,
                    champ_slug=champ_slug,
                    status_code=200,
                )
                return response.text
            elif response.status_code == 429:
                self._failure_count += 1
                logger.warning("opgg_rate_limited", url=url)
                raise OPGGRateLimitError(
                    "OP.GG rate limited",
                    champ_slug=champ_slug,
                    filters=filters,
                )
            elif response.status_code == 404:
                self._failure_count += 1
                logger.warning("opgg_champ_not_found", url=url, champ_slug=champ_slug)
                raise OPGGNotFoundError(
                    f"Champion '{champ_slug}' not found on OP.GG",
                    champ_slug=champ_slug,
                    filters=filters,
                )
            else:
                self._failure_count += 1
                logger.error(
                    "opgg_request_failed",
                    url=url,
                    status_code=response.status_code,
                )
                raise OPGGError(
                    f"OP.GG returned status {response.status_code}",
                    champ_slug=champ_slug,
                    filters=filters,
                )

        except OPGGRateLimitError:
            raise
        except OPGGNotFoundError:
            raise
        except httpx.RequestError as e:
            self._failure_count += 1
            logger.error("opgg_request_error", url=url, error=str(e))
            raise OPGGError(
                f"Request failed: {str(e)}",
                champ_slug=champ_slug,
                filters=filters,
            )

    def _build_url(
        self,
        champ_slug: str,
        region: str = "kr",
        queue: str = "RANKED_SOLO_5x5",
        tier: str = "overall",
        version: Optional[str] = None,
        role: str = "",
    ) -> str:
        """Build OP.GG URL for champion page."""
        base = self.BASE_URLS.get(region.lower(), self.BASE_URLS["kr"])

        # Build query params
        params = []
        if queue and queue != "RANKED_SOLO_5x5":
            queue_map = {
                "RANKED_FLEX_SR": "flex",
                "RANKED_TFT": "tft",
                "ARKANE": "aram",
            }
            params.append(f"queue={queue_map.get(queue, 'solo')}")
        else:
            params.append("queue=solo")

        if tier and tier != "overall":
            params.append(f"tier={tier}")
        if version:
            params.append(f"patch={version}")
        if role:
            params.append(f"role={role}")

        param_str = "&".join(params) if params else ""
        return f"{base}/champions/{champ_slug}/build?{param_str}"

    def _build_vs_url(
        self,
        champ_slug: str,
        region: str = "kr",
        queue: str = "RANKED_SOLO_5x5",
        tier: str = "overall",
    ) -> str:
        """Build OP.GG URL for champion vs page (counters)."""
        base = self.BASE_URLS.get(region.lower(), self.BASE_URLS["kr"])

        params = []
        if queue and queue != "RANKED_SOLO_5x5":
            queue_map = {
                "RANKED_FLEX_SR": "flex",
                "RANKED_TFT": "tft",
                "ARKANE": "aram",
            }
            params.append(f"queue={queue_map.get(queue, 'solo')}")
        else:
            params.append("queue=solo")

        if tier and tier != "overall":
            params.append(f"tier={tier}")

        param_str = "&".join(params) if params else ""
        return f"{base}/champions/{champ_slug}/vs?{param_str}"

    def _parse_win_rate(self, text: str) -> Optional[float]:
        """Parse win rate from text like '51.32%' or '51.3%'."""
        if not text:
            return None
        # Remove % and whitespace
        cleaned = text.strip().replace("%", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _parse_build_page(self, html: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Parse champion build page HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        result = {
            "champion_name": filters.get("champ_slug", ""),
            "win_rate": None,
            "pick_rate": None,
            "games_played": None,
            "roles": [],
            "items": {"start": [], "core": [], "final": []},
            "skills": [],
            "runes": [],
            "matchups": {"counters": [], "countered_by": []},
            "last_updated": datetime.now().isoformat(),
            "source": "op.gg",
            **filters,
        }

        # Try to find win rate - multiple selectors for robustness
        win_rate_selectors = [
            ".champion-stats-trend-rate",
            ".win-rate",
            '[class*="win"]',
            ".stats-value",
        ]
        for selector in win_rate_selectors:
            win_elem = soup.select_one(selector)
            if win_elem:
                text = win_elem.get_text()
                result["win_rate"] = self._parse_win_rate(text)
                if result["win_rate"]:
                    break

        # Try to find pick rate
        pick_selectors = [".pick-rate", '[class*="pick"]', ".ban-rate"]
        for selector in pick_selectors:
            pick_elem = soup.select_one(selector)
            if pick_elem:
                text = pick_elem.get_text()
                result["pick_rate"] = self._parse_win_rate(text)
                if result["pick_rate"]:
                    break

        # Find games played
        games_selectors = [".games", '[class*="games"]', ".matches"]
        for selector in games_selectors:
            games_elem = soup.select_one(selector)
            if games_elem:
                text = games_elem.get_text()
                # Extract number
                numbers = re.findall(r"[\d,]+", text)
                if numbers:
                    try:
                        result["games_played"] = int(numbers[0].replace(",", ""))
                        break
                    except ValueError:
                        pass

        # Parse item builds
        # Look for item slots - typically in order: starting items, core items, final items
        item_slot_selectors = [
            ".item-set[data-type='starting']",
            ".item-set[data-type='core']",
            ".item-set[data-type='final']",
            ".build-section",
            ".item-build",
        ]

        all_items = []
        item_elements = soup.select(".item-image, .item-slot img, [class*='item'] img")
        for item in item_elements[:12]:  # Limit to reasonable number
            item_name = item.get("alt") or item.get("title") or ""
            item_id = item.get("data-item-id", "")
            if item_name and item_name not in all_items:
                all_items.append({
                    "id": str(item_id),
                    "name": item_name.strip(),
                })

        # Split items into categories based on position
        if len(all_items) >= 3:
            result["items"]["core"] = all_items[:3]
            result["items"]["final"] = all_items[3:9] if len(all_items) > 3 else []
            result["items"]["start"] = all_items[9:12] if len(all_items) > 9 else []

        # Parse skill order (e.g., Q > W > E)
        skill_selectors = [".skill-order", ".skill-sequence", '[class*="skill"]']
        for selector in skill_selectors:
            skill_elem = soup.select_one(selector)
            if skill_elem:
                text = skill_elem.get_text()
                # Extract pattern like Q>W>E
                matches = re.findall(r"[QWER]\s*[>→]\s*[QWER]", text)
                if matches:
                    result["skills"] = matches[:1]  # Take first match
                    break

        # Parse runes
        rune_elements = soup.select(".rune-image, .rune-item img, [class*='rune'] img")
        runes = []
        for rune in rune_elements[:6]:
            rune_name = rune.get("alt") or rune.get("title") or rune.get_text()
            if rune_name and rune_name not in [r["name"] for r in runes]:
                runes.append({"name": rune_name.strip()})
        result["runes"] = runes

        # Parse role/build info
        role_selectors = [".role-badge", ".position", '[class*="role"]', '[class*="position"]']
        for selector in role_selectors:
            role_elems = soup.select(selector)
            for role_elem in role_elems:
                role_text = role_elem.get_text().strip()
                if role_text and role_text not in result["roles"]:
                    result["roles"].append(role_text)

        return result

    def _parse_vs_page(self, html: str, filters: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Parse champion vs (counters) page HTML.

        Returns dict with 'counters' (champions that beat this champ, win_rate < 50%)
        and 'countered_by' (champions this champ beats, win_rate >= 50%).
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        # Look for counter table/list
        counter_selectors = [
            ".counter-list .counter-item",
            ".versus-table tr",
            '[class*="counter"]',
            ".matchup-list .matchup",
        ]

        counter_items = soup.select(", ".join(counter_selectors[:1]))  # Use first matching selector

        if not counter_items:
            # Try alternative: find all table rows
            counter_items = soup.select("table tbody tr, .champion-vs tr")

        counters = []      # Champions that BEAT this champ (win_rate < 50% from this champ's perspective)
        countered_by = []  # Champions this champ BEATS (win_rate >= 50% from this champ's perspective)

        for item in counter_items[:15]:  # Get more to split later
            champ_name = ""
            win_rate = None
            games = 0

            # Try to extract champion name
            name_elem = item.select_one(".champion-name, .name, [class*='champion']")
            if name_elem:
                champ_name = name_elem.get_text().strip()

            # Try to extract win rate
            wr_elem = item.select_one(".win-rate, .wr, [class*='win']")
            if wr_elem:
                win_rate = self._parse_win_rate(wr_elem.get_text())

            # Try to extract games
            games_elem = item.select_one(".games, .matches, [class*='games']")
            if games_elem:
                numbers = re.findall(r"[\d,]+", games_elem.get_text())
                if numbers:
                    try:
                        games = int(numbers[0].replace(",", ""))
                    except ValueError:
                        pass

            if champ_name and win_rate is not None:
                advantage = win_rate - 50.0  # Positive means this champ wins
                entry = {
                    "champion_name": champ_name,
                    "win_rate": win_rate,
                    "games": games,
                    "advantage": advantage,
                }
                # Champions with win_rate < 50% are counters (they beat this champ)
                # Champions with win_rate >= 50% are countered_by (this champ beats them)
                if win_rate < 50:
                    counters.append(entry)
                else:
                    countered_by.append(entry)

        # Sort each list by advantage (most extreme first)
        counters.sort(key=lambda x: x["advantage"])  # Most negative first (strongest counters)
        countered_by.sort(key=lambda x: x["advantage"], reverse=True)  # Most positive first (strongest countered)

        return {
            "counters": counters[:10],  # Top 10 hardest counters
            "countered_by": countered_by[:10],  # Top 10 most countered
        }

    async def get_champion_build(
        self,
        champ_slug: str,
        region: str = "kr",
        queue: str = "RANKED_SOLO_5x5",
        tier: str = "overall",
        version: Optional[str] = None,
        role: str = "",
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Get champion build data from OP.GG.

        Args:
            champ_slug: Champion URL slug (e.g., 'ahri', 'zed')
            region: Server region (kr, na, euw, etc.)
            queue: Queue type (RANKED_SOLO_5x5, RANKED_FLEX_SR, etc.)
            tier: Rank filter (overall, diamond, platinum, gold, etc.)
            version: Patch version filter
            use_cache: Whether to use cached data if available

        Returns:
            Dict containing build data with win_rate, items, skills, runes, etc.
        """
        filters = {
            "champ_slug": champ_slug,
            "region": region,
            "queue": queue,
            "tier": tier,
            "version": version,
            "role": role,
        }

        cache_key = self._get_cache_key(champ_slug, filters)

        # Check cache first
        if use_cache:
            cached = await self._get_from_cache(cache_key)
            if cached:
                self._cache_hit_count += 1
                cached["cached"] = True
                return cached

        url = self._build_url(champ_slug, region, queue, tier, version, role)

        try:
            html = await self._fetch_page(url, champ_slug, filters)
            data = self._parse_build_page(html, filters)

            # Try to also get counters (both directions)
            vs_url = self._build_vs_url(champ_slug, region, queue, tier)
            try:
                vs_html = await self._fetch_page(vs_url, champ_slug, filters)
                matchups = self._parse_vs_page(vs_html, filters)
                data["matchups"] = {
                    "counters": matchups.get("counters", []),
                    "countered_by": matchups.get("countered_by", []),
                }
            except Exception as e:
                logger.warning("opgg_vs_page_parse_failed", champ_slug=champ_slug, error=str(e))
                data["matchups"] = {"counters": [], "countered_by": []}

            # Cache the result
            if use_cache:
                await self._set_cache(cache_key, data)

            data["cached"] = False
            return data

        except OPGGRateLimitError:
            # Try to return stale cache on rate limit
            if use_cache:
                stale = await self._get_from_cache(cache_key, stale=True)
                if stale:
                    stale["cached"] = True
                    stale["stale"] = True
                    stale["cache_error"] = "rate_limited"
                    return stale
            raise
        except (OPGGNotFoundError, OPGGParseError, OPGGError):
            raise

    async def _get_from_cache(self, key: str, stale: bool = False) -> Optional[Dict[str, Any]]:
        """Get data from Redis cache."""
        try:
            import redis.asyncio as redis
            from app.core.config import settings

            client = redis.from_url(settings.redis_url)
            if stale:
                cache_key = f"{key}:stale"
            else:
                cache_key = key

            data = await client.get(cache_key)
            if data:
                import json
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning("opgg_cache_get_failed", key=key, error=str(e))
            return None

    async def _set_cache(self, key: str, data: Dict[str, Any]) -> None:
        """Set data in Redis cache with TTL."""
        try:
            import redis.asyncio as redis
            import json
            from app.core.config import settings

            client = redis.from_url(settings.redis_url)
            await client.setex(
                key,
                self.cache_ttl,
                json.dumps(data),
            )
            # Also set stale cache (longer TTL for fallback)
            await client.setex(f"{key}:stale", self.cache_ttl * 2, json.dumps(data))
        except Exception as e:
            logger.warning("opgg_cache_set_failed", key=key, error=str(e))

    def get_metrics(self) -> Dict[str, Any]:
        """Get scraper metrics for observability."""
        total = self._success_count + self._failure_count
        return {
            "requests_total": total,
            "requests_success": self._success_count,
            "requests_failure": self._failure_count,
            "cache_hits": self._cache_hit_count,
            "cache_hit_rate": (
                self._cache_hit_count / total if total > 0 else 0
            ),
        }


# Singleton instance with default settings
_default_scraper: Optional[OPGGScraper] = None


def get_opgg_scraper() -> OPGGScraper:
    """Get or create default OPGGScraper instance."""
    global _default_scraper
    if _default_scraper is None:
        _default_scraper = OPGGScraper(
            timeout=settings.opgg_timeout if hasattr(settings, 'opgg_timeout') else 30,
            rate_limit_per_second=settings.opgg_rate_limit_per_second if hasattr(settings, 'opgg_rate_limit_per_second') else 2,
            cache_ttl=settings.opgg_cache_ttl if hasattr(settings, 'opgg_cache_ttl') else 21600,
        )
    return _default_scraper