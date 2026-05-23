"""Fetch and parse official League of Legends patch notes."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

PATCH_NOTES_INDEX_URL = "https://www.leagueoflegends.com/zh-tw/news/tags/patch-notes/"
PATCH_NOTE_BASE_URL = "https://www.leagueoflegends.com"


class PatchNotesError(Exception):
    """Raised when official patch notes cannot be fetched or parsed."""


class PatchNotesService:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def fetch_latest(self) -> dict[str, Any]:
        index_html = await self._fetch_html(PATCH_NOTES_INDEX_URL)
        latest = self.parse_latest_patch_note_index(index_html)
        article_html = await self._fetch_html(latest["url"])
        return self.parse_patch_note_article(article_html, latest)

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
        section_set = set(sections)
        for heading in article.find_all(["h2", "h3"]):
            title = _clean_text(heading.get_text(" ", strip=True))
            if not title:
                continue
            body = self._first_meaningful_text_after_heading(heading, section_set)
            if body:
                takeaways.append(f"{title}：{body}")
        return takeaways

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
