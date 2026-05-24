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
    CACHE_SCHEMA_VERSION = "v2"

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
    UGG_DUOS_BASE = "https://stats2.u.gg/lol/1.5/duos/world"
    UGG_QUEUE = "ranked_solo_5x5"
    UGG_TIER = "emerald_plus"
    UGG_PATCH_REGION = "1.5.0.json"
    CDRAGON_CHAMPION_SUMMARY = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json"
    DDRAGON_VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
    SHARD_ID_TO_NAME = {
        5008: "自适应之力",
        5005: "攻击速度",
        5007: "冷却缩减",
        5002: "护甲",
        5003: "魔抗",
        5001: "生命值",
        5011: "移动速度",
    }

    # Default headers to mimic browser
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        # Brotli responses require optional decoder support in the runtime.
        # Prefer encodings that httpx can always decode in our container.
        "Accept-Encoding": "gzip, deflate",
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
        self._champion_id_to_name: Dict[int, str] = {}
        self._rune_id_to_name: Dict[int, str] = {}
        self._rune_meta_by_id: Dict[int, Dict[str, Any]] = {}

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

    def _ensure_client(self) -> None:
        """Lazily initialize HTTP client for singleton usage."""
        if self._client is not None:
            return
        self._client = httpx.AsyncClient(
            headers=self.HEADERS,
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
        )

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
        key_data = f"{self.CACHE_SCHEMA_VERSION}:{champ_slug}:{json.dumps(filters, sort_keys=True)}"
        return f"opgg:champion:{hashlib.md5(key_data.encode()).hexdigest()}"

    async def _fetch_page(self, url: str, champ_slug: str, filters: Dict[str, Any]) -> str:
        """Fetch a page with rate limiting and retry logic."""
        self._ensure_client()
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
        return f"{base}/lol/champions/{champ_slug}/counters?{param_str}"

    def _build_synergies_url(
        self,
        champ_slug: str,
        region: str = "kr",
        queue: str = "RANKED_SOLO_5x5",
        tier: str = "overall",
        role: str = "",
    ) -> str:
        """Build OP.GG URL for champion synergies page."""
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
        role_path = f"/{role}" if role else ""
        return f"{base}/lol/champions/{champ_slug}/synergies{role_path}?{param_str}"

    async def _fetch_synergies_with_fallbacks(
        self,
        champ_slug: str,
        filters: Dict[str, Any],
        region: str,
        queue: str,
        tier: str,
        role: str,
    ) -> List[Dict[str, Any]]:
        """Fetch synergies with fallback strategies when sample size is insufficient."""
        candidates = [
            self._build_synergies_url(champ_slug, region, queue, tier, role),
        ]
        if not role:
            candidates.append(self._build_synergies_url(champ_slug, region, queue, tier, "adc"))

        global_base = self.BASE_URLS["kr"]
        candidates.append(
            f"{global_base}/lol/champions/{champ_slug}/synergies?queue=solo&type=ranked&tier=emerald_plus&region=global"
        )
        candidates.append(
            f"{global_base}/lol/champions/{champ_slug}/synergies/adc?queue=solo&type=ranked&tier=emerald_plus&region=global"
        )

        seen = set()
        for url in candidates:
            if url in seen:
                continue
            seen.add(url)
            try:
                html = await self._fetch_page(url, champ_slug, filters)
                parsed = self._parse_synergies_page(html, filters)
                if parsed:
                    return parsed
            except Exception as e:
                logger.warning("opgg_synergies_fallback_failed", champ_slug=champ_slug, url=url, error=str(e))
                continue
        return []

    async def _fetch_ugg_synergies_fallback(self, champ_slug: str) -> List[Dict[str, Any]]:
        """Fallback synergy source from U.GG duos when OP.GG has no usable sample size."""
        champ_map = await self._get_champion_id_map()
        if not champ_map:
            return []

        champ_name = champ_slug.replace("-", " ").lower()
        target_ids = [cid for cid, name in champ_map.items() if name.lower() == champ_name]
        if not target_ids:
            return []
        target_id = target_ids[0]

        patch_candidates = await self._build_ugg_patch_candidates()
        for patch in patch_candidates:
            url = f"{self.UGG_DUOS_BASE}/{patch}/{self.UGG_QUEUE}/{self.UGG_TIER}/{self.UGG_PATCH_REGION}"
            try:
                payload = await self._fetch_json(url)
                parsed = self._parse_ugg_duos_payload(payload, target_id, champ_map)
                if parsed:
                    return parsed[:5]
            except Exception as e:
                logger.warning("ugg_synergies_fetch_failed", champ_slug=champ_slug, url=url, error=str(e))
        return []

    async def _fetch_json(self, url: str) -> Any:
        """Fetch JSON payload with shared client and timeout settings."""
        self._ensure_client()
        response = await self._client.get(url)
        response.raise_for_status()
        return response.json()

    async def _get_champion_id_map(self) -> Dict[int, str]:
        """Get champion ID -> canonical name mapping."""
        if self._champion_id_to_name:
            return self._champion_id_to_name
        try:
            payload = await self._fetch_json(self.CDRAGON_CHAMPION_SUMMARY)
            mapping: Dict[int, str] = {}
            for item in payload:
                try:
                    champ_id = int(item.get("id", 0))
                except (TypeError, ValueError):
                    continue
                name = str(item.get("name", "")).strip()
                if champ_id > 0 and name:
                    mapping[champ_id] = name
            self._champion_id_to_name = mapping
            return mapping
        except Exception as e:
            logger.warning("champion_id_map_fetch_failed", error=str(e))
            return {}

    async def _build_ugg_patch_candidates(self) -> List[str]:
        """Build likely U.GG patch paths like 16_10, with a small fallback window."""
        candidates: List[str] = []
        try:
            versions = await self._fetch_json("https://ddragon.leagueoflegends.com/api/versions.json")
            if versions and isinstance(versions, list):
                major_minor = str(versions[0]).split(".")
                if len(major_minor) >= 2:
                    major = int(major_minor[0])
                    minor = int(major_minor[1])
                    for delta in range(0, 4):
                        m = minor - delta
                        if m > 0:
                            candidates.append(f"{major}_{m}")
        except Exception as e:
            logger.warning("ugg_patch_discovery_failed", error=str(e))

        candidates.extend(["16_10", "16_9", "16_8"])
        seen = set()
        uniq: List[str] = []
        for patch in candidates:
            if patch in seen:
                continue
            seen.add(patch)
            uniq.append(patch)
        return uniq[:8]

    async def _get_rune_id_to_name_map(self) -> Dict[int, str]:
        """Get rune perk ID -> localized rune name mapping."""
        if self._rune_id_to_name:
            return self._rune_id_to_name

        def flatten_runes(payload: Any) -> Dict[int, Dict[str, Any]]:
            mapping: Dict[int, Dict[str, Any]] = {}
            if not isinstance(payload, list):
                return mapping
            for style in payload:
                style_id = style.get("id")
                for slot_index, slot in enumerate(style.get("slots", [])):
                    for perk in slot.get("runes", []):
                        perk_id = perk.get("id")
                        name = str(perk.get("name", "")).strip()
                        if isinstance(perk_id, int) and name:
                            mapping[perk_id] = {
                                "name": name,
                                "style_id": style_id,
                                "slot_index": slot_index,
                            }
            return mapping

        try:
            versions = await self._fetch_json(self.DDRAGON_VERSIONS_URL)
            latest = versions[0] if isinstance(versions, list) and versions else None
            if not latest:
                return {}

            zh_url = f"https://ddragon.leagueoflegends.com/cdn/{latest}/data/zh_CN/runesReforged.json"
            en_url = f"https://ddragon.leagueoflegends.com/cdn/{latest}/data/en_US/runesReforged.json"

            zh_payload = await self._fetch_json(zh_url)
            mapping = flatten_runes(zh_payload)

            if not mapping:
                en_payload = await self._fetch_json(en_url)
                mapping = flatten_runes(en_payload)

            self._rune_meta_by_id = mapping
            self._rune_id_to_name = {
                perk_id: meta.get("name", "")
                for perk_id, meta in mapping.items()
                if meta.get("name")
            }
            return self._rune_id_to_name
        except Exception as e:
            logger.warning("rune_id_map_fetch_failed", error=str(e))
            return {}

    def _select_best_rune_window_from_ids(
        self,
        rune_ids: List[int],
        rune_meta_by_id: Dict[int, Dict[str, Any]],
    ) -> List[int]:
        """Select first valid 4+2 rune combination from perk ids using style/slot metadata."""
        if len(rune_ids) < 6:
            return rune_ids[:6]

        for start_idx, start_id in enumerate(rune_ids):
            start_meta = rune_meta_by_id.get(start_id)
            if not start_meta:
                continue
            primary_style = start_meta.get("style_id")
            if primary_style is None:
                continue

            primary_by_slot: Dict[int, int] = {}
            primary_end_idx = start_idx
            for idx in range(start_idx, len(rune_ids)):
                perk_id = rune_ids[idx]
                meta = rune_meta_by_id.get(perk_id)
                if not meta or meta.get("style_id") != primary_style:
                    continue
                slot = meta.get("slot_index")
                if slot in {0, 1, 2, 3} and slot not in primary_by_slot:
                    primary_by_slot[slot] = perk_id
                    primary_end_idx = idx
                if len(primary_by_slot) == 4:
                    break

            if set(primary_by_slot.keys()) != {0, 1, 2, 3}:
                continue

            secondary_completion: Optional[tuple[int, List[int]]] = None
            secondary_slots_by_style: Dict[Any, Dict[int, int]] = {}

            for idx in range(primary_end_idx + 1, len(rune_ids)):
                perk_id = rune_ids[idx]
                meta = rune_meta_by_id.get(perk_id)
                if not meta:
                    continue
                style_id = meta.get("style_id")
                slot = meta.get("slot_index")
                if style_id is None or style_id == primary_style or slot not in {1, 2, 3}:
                    continue

                bucket = secondary_slots_by_style.setdefault(style_id, {})
                if slot not in bucket:
                    bucket[slot] = perk_id
                if len(bucket) >= 2:
                    ids = [bucket[k] for k in sorted(bucket.keys())[:2]]
                    secondary_completion = (idx, ids)
                    break

            if not secondary_completion:
                continue

            primary_ids = [primary_by_slot[0], primary_by_slot[1], primary_by_slot[2], primary_by_slot[3]]
            return primary_ids + secondary_completion[1]

        return rune_ids[:6]

    def _parse_ugg_duos_payload(
        self,
        payload: Any,
        target_id: int,
        champ_map: Dict[int, str],
    ) -> List[Dict[str, Any]]:
        """Parse U.GG duos payload into ChampionSynergy-compatible rows."""
        if not isinstance(payload, list) or not payload:
            return []
        results: List[Dict[str, Any]] = []
        seen: set[int] = set()

        # Current payload shape: [ {adc_supp:[...], jungle_supp:[...], ...}, "16_10", 0.0, ... ]
        groups = payload[0] if isinstance(payload[0], dict) else {}
        if not isinstance(groups, dict):
            return []

        for data in groups.values():
            if not isinstance(data, list):
                continue
            for row in data:
                if not isinstance(row, list) or len(row) < 10:
                    continue
                try:
                    champ_a = int(row[0])
                    champ_b = int(row[4])
                    duo_wins = float(row[8])
                    duo_games = int(row[9])
                except (TypeError, ValueError):
                    continue
                if duo_games <= 0:
                    continue
                if champ_a == target_id:
                    partner_id = champ_b
                elif champ_b == target_id:
                    partner_id = champ_a
                else:
                    continue
                if partner_id in seen:
                    continue
                partner_name = champ_map.get(partner_id)
                if not partner_name:
                    continue
                seen.add(partner_id)
                results.append({
                    "champion_name": partner_name,
                    "win_rate": round((duo_wins / duo_games) * 100, 2),
                    "pick_rate": None,
                    "games": duo_games,
                })
        results.sort(key=lambda item: (item.get("win_rate") or 0, item.get("games") or 0), reverse=True)
        return results[:5]

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
            "rune_setup": None,
            "rune_setup_valid": False,
            "matchups": {"counters": [], "countered_by": []},
            "synergies": [],
            "last_updated": datetime.now().isoformat(),
            "source": "op.gg",
            **filters,
        }

        # Parse headline stats from labeled rows (Win rate / Pick rate).
        for stat_row in soup.select("li"):
            label = stat_row.select_one("em")
            value = stat_row.select_one("b")
            if not label or not value:
                continue
            key = label.get_text(" ", strip=True).lower()
            parsed = self._parse_win_rate(value.get_text(" ", strip=True))
            if parsed is None:
                continue
            if key == "win rate" and result["win_rate"] is None:
                result["win_rate"] = parsed
            elif key == "pick rate" and result["pick_rate"] is None:
                result["pick_rate"] = parsed

        # Fallback selectors for older OP.GG layouts.
        if result["win_rate"] is None:
            for selector in [".champion-stats-trend-rate", ".win-rate", '[class*="win"]', ".stats-value"]:
                win_elem = soup.select_one(selector)
                if win_elem:
                    result["win_rate"] = self._parse_win_rate(win_elem.get_text())
                    if result["win_rate"] is not None:
                        break
        if result["pick_rate"] is None:
            for selector in [".pick-rate", '[class*="pick"]', ".ban-rate"]:
                pick_elem = soup.select_one(selector)
                if pick_elem:
                    result["pick_rate"] = self._parse_win_rate(pick_elem.get_text())
                    if result["pick_rate"] is not None:
                        break

        # Parse games played from strings like "95,557 Games".
        for games_elem in soup.find_all(string=re.compile(r"[\d,]+\s+Games", re.IGNORECASE)):
            numbers = re.findall(r"[\d,]+", str(games_elem))
            if not numbers:
                continue
            try:
                result["games_played"] = int(numbers[0].replace(",", ""))
                break
            except ValueError:
                continue
        if result["games_played"] is None:
            for selector in [".games", '[class*="games"]', ".matches"]:
                games_elem = soup.select_one(selector)
                if not games_elem:
                    continue
                numbers = re.findall(r"[\d,]+", games_elem.get_text())
                if not numbers:
                    continue
                try:
                    result["games_played"] = int(numbers[0].replace(",", ""))
                    break
                except ValueError:
                    continue

        table_by_header: Dict[str, Any] = {}
        for table in soup.select("table"):
            header = table.select_one("thead th")
            if not header:
                continue
            header_text = header.get_text(" ", strip=True).lower()
            if header_text:
                table_by_header[header_text] = table

        def extract_first_row_items(table: Any) -> List[Dict[str, str]]:
            first_row = table.select_one("tbody tr")
            if not first_row:
                return []
            items: List[Dict[str, str]] = []
            seen: set[str] = set()
            for img in first_row.select("td img[alt]"):
                name = img.get("alt", "").strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                item_id = ""
                src = img.get("src", "")
                match = re.search(r"/item/(\d+)\.png", src)
                if match:
                    item_id = match.group(1)
                items.append({"id": item_id, "name": name})
            return items

        starter_table = table_by_header.get("starter items")
        if starter_table:
            result["items"]["start"] = extract_first_row_items(starter_table)

        core_table = table_by_header.get("core builds")
        if core_table:
            result["items"]["core"] = extract_first_row_items(core_table)

        final_items: List[Dict[str, str]] = []
        for header in ("fourth item", "fifth item", "sixth item"):
            table = table_by_header.get(header)
            if not table:
                continue
            items = extract_first_row_items(table)
            if items:
                final_items.extend(items[:1])
        if final_items:
            dedup_final: List[Dict[str, str]] = []
            seen_final: set[str] = set()
            for item in final_items:
                name = item.get("name", "")
                if name in seen_final:
                    continue
                seen_final.add(name)
                dedup_final.append(item)
            result["items"]["final"] = dedup_final

        # Fallback for legacy markup where table headers are unavailable.
        if not result["items"]["core"]:
            all_items: List[Dict[str, str]] = []
            seen_names: set[str] = set()
            for item in soup.select(".item-image, .item-slot img, [class*='item'] img")[:18]:
                item_name = (item.get("alt") or item.get("title") or "").strip()
                if not item_name or item_name in seen_names:
                    continue
                seen_names.add(item_name)
                item_id = str(item.get("data-item-id", "")).strip()
                all_items.append({"id": item_id, "name": item_name})
            if len(all_items) >= 3:
                result["items"]["core"] = all_items[:3]
                if not result["items"]["final"]:
                    result["items"]["final"] = all_items[3:9] if len(all_items) > 3 else []
                if not result["items"]["start"]:
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

        # Parse raw perk ids from current OP.GG app-router script payload.
        perk_ids: List[int] = []
        for token in re.findall(r"/perk/(\d+)\.png", html):
            try:
                perk_id = int(token)
            except ValueError:
                continue
            perk_ids.append(perk_id)
            if len(perk_ids) >= 300:
                break
        if perk_ids:
            result["_perk_ids"] = perk_ids

        # Fallback for current OP.GG app-router pages where rune imgs are embedded in script payload.
        rune_ids: List[int] = []
        if not runes:
            for perk_id in perk_ids:
                if perk_id < 8000:  # Ignore non-rune assets.
                    continue
                if perk_id in rune_ids:
                    continue
                rune_ids.append(perk_id)
                if len(rune_ids) >= 80:
                    break
            if rune_ids:
                runes = [{"name": f"perk_{perk_id}"} for perk_id in rune_ids]
                result["_rune_ids"] = rune_ids

        result["runes"] = runes

        # Build a structured rune setup for downstream simulator usage.
        rune_names = [r.get("name", "").strip() for r in runes if r.get("name")]
        if len(rune_names) >= 4:
            primary = rune_names[:4]
            secondary = rune_names[4:6]
            if len(primary) == 4 and len(secondary) == 2:
                result["rune_setup"] = {
                    "primary_runes": primary,
                    "secondary_runes": secondary,
                }
                result["rune_setup_valid"] = True

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

        current_rows = []
        for row in soup.select("ul li"):
            image = row.select_one("img[alt]")
            if not image:
                continue
            champ_name = image.get("alt", "").strip()
            text = " ".join(row.get_text(" ", strip=True).split())
            if not champ_name or "%" not in text:
                continue
            rate_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
            if not rate_match:
                continue
            games = 0
            after_rate = text[rate_match.end():]
            games_match = re.search(r"([\d,]+)", after_rate)
            if games_match:
                try:
                    games = int(games_match.group(1).replace(",", ""))
                except ValueError:
                    games = 0
            win_rate = float(rate_match.group(1))
            current_rows.append({
                "champion_name": champ_name,
                "win_rate": win_rate,
                "games": games,
                "advantage": win_rate - 50.0,
            })

        if current_rows:
            counters = [entry for entry in current_rows if entry["win_rate"] < 50]
            countered_by = [entry for entry in current_rows if entry["win_rate"] >= 50]
            counters.sort(key=lambda x: x["advantage"])
            countered_by.sort(key=lambda x: x["advantage"], reverse=True)
            return {
                "counters": counters[:10],
                "countered_by": countered_by[:10],
            }

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

    def _parse_synergies_page(self, html: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse champion synergy page and return best lane partners."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        synergies: List[Dict[str, Any]] = []

        for row in soup.select("table tbody tr"):
            if "sample size is not large enough" in row.get_text(" ", strip=True).lower():
                continue
            image = row.select_one("img[alt]")
            if not image:
                continue
            champion_name = image.get("alt", "").strip()
            if not champion_name:
                continue

            rates = []
            for text in row.stripped_strings:
                parsed = self._parse_win_rate(text)
                if parsed is not None:
                    rates.append(parsed)

            pick_rate = rates[0] if len(rates) >= 1 else None
            win_rate = rates[1] if len(rates) >= 2 else None
            if pick_rate is None and win_rate is None:
                continue

            games = 0
            games_match = re.search(r"([\d,]+)\s+Games", row.get_text(" ", strip=True), re.IGNORECASE)
            if games_match:
                try:
                    games = int(games_match.group(1).replace(",", ""))
                except ValueError:
                    games = 0

            synergies.append({
                "champion_name": champion_name,
                "pick_rate": pick_rate,
                "win_rate": win_rate,
                "games": games,
            })

        synergies.sort(key=lambda item: item.get("win_rate") or 0, reverse=True)
        return synergies[:5]

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

            # Normalize fallback perk ids (e.g. perk_8112) into localized rune names.
            rune_ids = data.pop("_rune_ids", [])
            if rune_ids:
                rune_map = await self._get_rune_id_to_name_map()
                selected = self._select_best_rune_window_from_ids(rune_ids, self._rune_meta_by_id)
                resolved = [rune_map.get(perk_id, f"perk_{perk_id}") for perk_id in selected]
                data["runes"] = [{"name": name} for name in resolved]
                if len(resolved) >= 6:
                    data["rune_setup"] = {
                        "primary_runes": resolved[:4],
                        "secondary_runes": resolved[4:6],
                        "stat_shards": [],
                    }
                    data["rune_setup_valid"] = True

            shard_ids: List[int] = []
            perk_ids = data.pop("_perk_ids", [])
            if perk_ids:
                # Prefer shards that appear after the selected 6 runes in stream order.
                anchor = -1
                if rune_ids:
                    remaining = list(selected)
                    for idx, perk_id in enumerate(perk_ids):
                        if remaining and perk_id == remaining[0]:
                            remaining.pop(0)
                            anchor = idx
                            if not remaining:
                                break
                scan = perk_ids[anchor + 1:] if anchor >= 0 else perk_ids
                for perk_id in scan:
                    if perk_id not in self.SHARD_ID_TO_NAME:
                        continue
                    if perk_id in shard_ids:
                        continue
                    shard_ids.append(perk_id)
                    if len(shard_ids) >= 3:
                        break

            shard_names = [self.SHARD_ID_TO_NAME.get(shard_id) for shard_id in shard_ids]
            shard_names = [name for name in shard_names if name]
            if shard_names:
                if not data.get("rune_setup"):
                    data["rune_setup"] = {
                        "primary_runes": [],
                        "secondary_runes": [],
                        "stat_shards": shard_names[:3],
                    }
                else:
                    data["rune_setup"]["stat_shards"] = shard_names[:3]

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

            try:
                data["synergies"] = await self._fetch_synergies_with_fallbacks(
                    champ_slug=champ_slug,
                    filters=filters,
                    region=region,
                    queue=queue,
                    tier=tier,
                    role=role,
                )
                if not data["synergies"]:
                    data["synergies"] = await self._fetch_ugg_synergies_fallback(champ_slug)
            except Exception as e:
                logger.warning("opgg_synergies_page_parse_failed", champ_slug=champ_slug, error=str(e))
                data["synergies"] = []

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
        except Exception as e:
            logger.exception(
                "opgg_unhandled_exception",
                champ_slug=champ_slug,
                filters=filters,
                error=str(e),
            )
            raise OPGGError(
                f"Unhandled OP.GG scrape error: {str(e)}",
                champ_slug=champ_slug,
                filters=filters,
            )

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
