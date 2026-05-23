"""Fetch and parse official League of Legends patch notes."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag
from app.core.config import settings
from app.core.logging import get_logger
from app.db.redis import redis_client

PATCH_NOTES_INDEX_URL = "https://www.leagueoflegends.com/zh-tw/news/tags/patch-notes/"
PATCH_NOTE_BASE_URL = "https://www.leagueoflegends.com"
PREVIEW_SECTION_PRIORITY = ("英雄", "道具", "符文", "系統", "系統調整", "版本概要")
PATCH_NOTES_CACHE_KEY = "patch_notes:latest:zh-tw"
logger = get_logger(__name__)


class PatchNotesError(Exception):
    """Raised when official patch notes cannot be fetched or parsed."""


class PatchNotesService:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def fetch_latest(self, use_cache: bool = True) -> dict[str, Any]:
        if use_cache:
            cached = await redis_client.get(PATCH_NOTES_CACHE_KEY)
            if isinstance(cached, dict) and cached.get("version") and cached.get("analysis"):
                return cached

        index_html = await self._fetch_html(PATCH_NOTES_INDEX_URL)
        latest = self.parse_latest_patch_note_index(index_html)
        article_html = await self._fetch_html(latest["url"])
        parsed = self.parse_patch_note_article(article_html, latest)
        if use_cache:
            ok = await redis_client.set(
                PATCH_NOTES_CACHE_KEY,
                parsed,
                ttl=settings.cache_ttl_patch_notes,
            )
            if not ok:
                logger.warning("patch_notes_cache_set_failed", key=PATCH_NOTES_CACHE_KEY)
        return parsed

    async def _fetch_html(self, url: str) -> str:
        headers = {
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.7",
            "User-Agent": "recaplol/1.0 patch-note-fetcher",
        }
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text

    def parse_latest_patch_note_index(self, html: str) -> dict[str, str | None]:
        soup = BeautifulSoup(html, "lxml")
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href") or "")
            text = _clean_text(anchor.get_text(" ", strip=True))
            if "patch" not in href or "版本更新公告" not in text:
                continue

            title = self._extract_title(anchor, text)
            version = self._extract_version(title)
            published_at = self._extract_datetime(anchor)
            return {
                "version": version,
                "title": title,
                "url": urljoin(PATCH_NOTE_BASE_URL, href),
                "published_at": published_at,
                "summary": self._extract_summary(anchor, title),
            }

        raise PatchNotesError("Could not find latest League of Legends patch note")

    def parse_patch_note_article(
        self, html: str, latest: dict[str, str | None]
    ) -> dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")
        article = soup.find("article") or soup.body or soup
        title = _clean_text(_first_text(article, ["h1"])) or str(latest["title"])
        summary = str(latest.get("summary") or "")
        if not summary:
            summary = _clean_text(_first_text_after(article, "h1", "p"))
        overview = _clean_text(_first_text(article, ["blockquote"])) or summary
        version = str(latest.get("version") or self._extract_version(title))
        sections = self._extract_sections(article)
        takeaways = self._extract_takeaways(article, sections)
        details = self._extract_details(article, sections)

        return {
            "version": version,
            "title": title,
            "url": str(latest["url"]),
            "published_at": latest.get("published_at") or self._extract_datetime(article),
            "summary": summary,
            "overview": overview,
            "analysis": {
                "headline": f"{version} 版本重點解析",
                "sections": sections[:6],
                "takeaways": takeaways[:5],
                "details": details,
            },
        }

    def _extract_title(self, anchor: Tag, fallback: str) -> str:
        for selector in ["h1", "h2", "h3"]:
            title = _clean_text(_first_text(anchor, [selector]))
            if title:
                return title
        match = re.search(r"(《?英雄聯盟》?\s*)?\d+(?:\.\d+)+版本更新公告", fallback)
        return _clean_text(match.group(0)) if match else fallback

    def _extract_version(self, text: str) -> str:
        match = re.search(r"(\d+(?:\.\d+)+)", text)
        if not match:
            raise PatchNotesError(f"Could not extract patch version from {text!r}")
        return match.group(1)

    def _extract_datetime(self, node: Tag) -> str | None:
        time_node = node.find("time")
        if isinstance(time_node, Tag):
            value = time_node.get("datetime")
            if value:
                return str(value)
        text = node.get_text(" ", strip=True)
        match = re.search(r"\d{4}-\d{2}-\d{2}T[\d:.]+Z", text)
        return match.group(0) if match else None

    def _extract_summary(self, anchor: Tag, title: str) -> str:
        for paragraph in anchor.find_all("p"):
            text = _clean_text(paragraph.get_text(" ", strip=True))
            if text and text != title and "版本更新公告" not in text:
                return text

        text = _clean_text(anchor.get_text(" ", strip=True))
        remainder = text.replace(title, "", 1)
        remainder = re.sub(r"遊戲更新|\d{4}-\d{2}-\d{2}T[\d:.]+Z", " ", remainder)
        return _clean_text(remainder)

    def _extract_sections(self, article: Tag) -> list[str]:
        sections: list[str] = []
        for heading in article.find_all(["h2"]):
            text = _clean_text(heading.get_text(" ", strip=True))
            if text and text not in sections:
                sections.append(text)
        return sections

    def _extract_takeaways(self, article: Tag, sections: list[str]) -> list[str]:
        takeaways: list[str] = []
        used: set[str] = set()
        section_nodes = article.find_all("h2")
        prioritized = sorted(
            section_nodes,
            key=lambda node: _section_priority(_clean_text(node.get_text(" ", strip=True))),
        )

        for section in prioritized:
            section_title = _clean_text(section.get_text(" ", strip=True))
            if not section_title:
                continue
            for item in self._extract_section_takeaways(section, section_title):
                normalized = _clean_text(item)
                if normalized and normalized not in used:
                    used.add(normalized)
                    takeaways.append(normalized)
                if len(takeaways) >= 8:
                    return takeaways
        return takeaways

    def _extract_section_takeaways(self, section_h2: Tag, section_title: str) -> list[str]:
        results: list[str] = []
        subjects: list[str] = []
        per_subject: dict[str, list[str]] = {}
        overview_fallback = ""
        general_fallback = ""
        next_h2 = section_h2.find_next("h2")
        current_subject = ""

        for node in section_h2.next_elements:
            if node is section_h2:
                continue
            if next_h2 and node is next_h2:
                break
            if not isinstance(node, Tag):
                continue

            if node.name == "h3":
                current_subject = _clean_text(node.get_text(" ", strip=True))
                if current_subject and current_subject not in subjects:
                    subjects.append(current_subject)
                    per_subject[current_subject] = []
                continue

            if node.name == "li":
                text = _clean_text(node.get_text(" ", strip=True))
                if not text:
                    continue
                if current_subject:
                    per_subject[current_subject].append(text)
                elif not general_fallback:
                    general_fallback = text
                continue

            if node.name in {"p", "blockquote"}:
                text = _clean_text(node.get_text(" ", strip=True))
                if not text:
                    continue
                if section_title == "版本概要" and not overview_fallback:
                    overview_fallback = text
                if current_subject and not per_subject.get(current_subject):
                    per_subject[current_subject] = [text]
                elif not general_fallback:
                    general_fallback = text

        for subject in subjects[:2]:
            values = per_subject.get(subject) or []
            best = next((value for value in values if _looks_like_balance_change(value)), None)
            chosen = best or (values[0] if values else "")
            if chosen:
                results.append(
                    f"{section_title} {subject}：{_truncate(_compact_preview_text(chosen), 48)}"
                )

        if not results and overview_fallback:
            results.append(f"{section_title}：{_truncate(_compact_preview_text(overview_fallback), 48)}")
        if not results and general_fallback:
            results.append(f"{section_title}：{_truncate(_compact_preview_text(general_fallback), 48)}")
        if not results:
            fallback = self._first_meaningful_text_after_heading(section_h2, set())
            if fallback:
                results.append(f"{section_title}：{fallback}")
        return results[:2]

    def _extract_details(self, article: Tag, sections: list[str]) -> dict[str, list[str]]:
        details: dict[str, list[str]] = {}
        section_nodes = article.find_all("h2")
        for section_node in section_nodes:
            section_title = _clean_text(section_node.get_text(" ", strip=True))
            if not section_title:
                continue
            items = self._extract_section_details(section_node)
            if items:
                details[section_title] = items[:20]

        # Ensure surfaced sections always exist in details when possible.
        for section_title in sections:
            details.setdefault(section_title, [])
        return details

    def _extract_section_details(self, section_h2: Tag) -> list[str]:
        results: list[str] = []
        next_h2 = section_h2.find_next("h2")
        current_subject = ""

        for node in section_h2.next_elements:
            if node is section_h2:
                continue
            if next_h2 and node is next_h2:
                break
            if not isinstance(node, Tag):
                continue

            if node.name == "h3":
                current_subject = _clean_text(node.get_text(" ", strip=True))
                continue

            if node.name == "li":
                text = _clean_text(node.get_text(" ", strip=True))
                if not text:
                    continue
                if current_subject:
                    results.append(f"{current_subject}：{_truncate(text, 120)}")
                else:
                    results.append(_truncate(text, 120))
                continue

            if node.name in {"p", "blockquote"} and not results:
                text = _clean_text(node.get_text(" ", strip=True))
                if text:
                    results.append(_truncate(text, 120))

        # Deduplicate while keeping order.
        unique: list[str] = []
        seen: set[str] = set()
        for item in results:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique

    def _first_meaningful_text_after_heading(
        self, heading: Tag, section_set: set[str]
    ) -> str:
        for sibling in heading.find_next_siblings():
            if not isinstance(sibling, Tag):
                continue
            if sibling.name == "h2":
                return ""
            if sibling.name in {"p", "blockquote"}:
                text = _clean_text(sibling.get_text(" ", strip=True))
                if text:
                    return _truncate(text)
            if sibling.name in {"ul", "ol"}:
                item = sibling.find("li")
                text = _clean_text(item.get_text(" ", strip=True)) if item else ""
                if text:
                    return _truncate(text)
            if sibling.name == "h3":
                text = _clean_text(sibling.get_text(" ", strip=True))
                if text and text not in section_set:
                    return text
        return ""


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _truncate(value: str, limit: int = 120) -> str:
    return value if len(value) <= limit else f"{value[:limit].rstrip()}..."


def _looks_like_balance_change(text: str) -> bool:
    markers = ("⇒", "->", "→", "增加", "降低", "提升", "削弱", "Buff", "Nerf")
    return any(marker in text for marker in markers)


def _compact_preview_text(text: str) -> str:
    value = _clean_text(text)
    sentences = [item.strip() for item in re.split(r"[。！？]", value) if item.strip()]
    if not sentences:
        return value
    for sentence in sentences:
        if _looks_like_balance_change(sentence):
            return sentence
    for sentence in sentences:
        if "：" in sentence and any(ch.isdigit() for ch in sentence):
            return sentence
    return sentences[0]


def _section_priority(title: str) -> int:
    for idx, key in enumerate(PREVIEW_SECTION_PRIORITY):
        if key in title:
            return idx
    return len(PREVIEW_SECTION_PRIORITY)


def _first_text(node: Tag, selectors: list[str]) -> str:
    for selector in selectors:
        found = node.find(selector)
        if found:
            return found.get_text(" ", strip=True)
    return ""


def _first_text_after(node: Tag, heading_name: str, target_name: str) -> str:
    heading = node.find(heading_name)
    if not heading:
        return ""
    target = heading.find_next(target_name)
    return target.get_text(" ", strip=True) if target else ""
