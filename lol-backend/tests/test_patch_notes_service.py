"""Tests for League of Legends patch note parsing."""

import pytest

from app.services.patch_notes import PatchNotesService
from app.services import patch_notes as patch_notes_module


PATCH_INDEX_HTML = """
<html>
  <body>
    <a href="/zh-tw/news/game-updates/league-of-legends-patch-26-10-notes/">
      <span>遊戲更新</span>
      <time datetime="2026-05-12T18:00:00.000Z"></time>
      <h2>《英雄聯盟》26.10版本更新公告</h2>
      <p>26.10版本登場，群魔繼續亂舞！</p>
    </a>
    <a href="/zh-tw/news/game-updates/league-of-legends-patch-26-9-notes/">
      <h2>《英雄聯盟》26.9版本更新公告</h2>
    </a>
  </body>
</html>
"""

PATCH_ARTICLE_HTML = """
<html>
  <body>
    <article>
      <h1>《英雄聯盟》26.10版本更新公告</h1>
      <p>26.10版本登場，群魔繼續亂舞！</p>
      <time datetime="2026-05-12T18:00:00.000Z"></time>
      <blockquote>
        <p>我們針對近期第二賽季的改動做了一些後續調整。</p>
      </blockquote>
      <h2>版本概要</h2>
      <p>「牧雨歌僮 埃爾文」與「菁英計畫 葵恩」將於2026年5月13日登場。</p>
      <h2>英雄</h2>
      <h3>安比薩</h3>
      <ul>
        <li>目標最大生命傷害：2 / 3 / 4 / 5 / 6% ⇒ 4 / 4.5 / 5 / 5.5 / 6%</li>
      </ul>
      <h2>道具</h2>
      <h3>多蘭之弓</h3>
      <ul>
        <li>物攻：6 ⇒ 8</li>
      </ul>
    </article>
  </body>
</html>
"""


def test_parse_latest_patch_note_index_finds_first_official_patch_note():
    service = PatchNotesService()

    latest = service.parse_latest_patch_note_index(PATCH_INDEX_HTML)

    assert latest["title"] == "《英雄聯盟》26.10版本更新公告"
    assert latest["version"] == "26.10"
    assert latest["published_at"] == "2026-05-12T18:00:00.000Z"
    assert latest["url"] == (
        "https://www.leagueoflegends.com/zh-tw/news/game-updates/"
        "league-of-legends-patch-26-10-notes/"
    )


def test_parse_patch_note_article_builds_announcement_analysis():
    service = PatchNotesService()
    latest = service.parse_latest_patch_note_index(PATCH_INDEX_HTML)

    announcement = service.parse_patch_note_article(PATCH_ARTICLE_HTML, latest)

    assert announcement["version"] == "26.10"
    assert announcement["summary"] == "26.10版本登場，群魔繼續亂舞！"
    assert "第二賽季" in announcement["overview"]
    assert announcement["analysis"]["headline"] == "26.10 版本重點解析"
    assert "版本概要" in announcement["analysis"]["sections"]
    assert "英雄" in announcement["analysis"]["sections"]
    assert "details" in announcement["analysis"]
    assert "英雄" in announcement["analysis"]["details"]
    assert any("安比薩" in item for item in announcement["analysis"]["details"]["英雄"])
    hero_takeaway = next(
        item for item in announcement["analysis"]["takeaways"] if item.startswith("英雄 安比薩：")
    )
    assert "⇒" in hero_takeaway
    assert any(item.startswith("版本概要：") for item in announcement["analysis"]["takeaways"])


@pytest.mark.asyncio
async def test_fetch_latest_uses_index_then_article(monkeypatch):
    service = PatchNotesService()
    calls = []

    async def fake_fetch_html(url: str) -> str:
        calls.append(url)
        if url.endswith("/patch-notes/"):
            return PATCH_INDEX_HTML
        return PATCH_ARTICLE_HTML

    monkeypatch.setattr(service, "_fetch_html", fake_fetch_html)

    announcement = await service.fetch_latest()

    assert calls == [
        "https://www.leagueoflegends.com/zh-tw/news/tags/patch-notes/",
        "https://www.leagueoflegends.com/zh-tw/news/game-updates/league-of-legends-patch-26-10-notes/",
    ]
    assert announcement["title"] == "《英雄聯盟》26.10版本更新公告"


@pytest.mark.asyncio
async def test_fetch_latest_returns_cached_payload(monkeypatch):
    service = PatchNotesService()
    cached = {
        "version": "26.10",
        "title": "《英雄聯盟》26.10版本更新公告",
        "url": "https://www.leagueoflegends.com/zh-tw/news/game-updates/league-of-legends-patch-26-10-notes/",
        "published_at": "2026-05-12T18:00:00.000Z",
        "summary": "26.10版本登場，群魔繼續亂舞！",
        "overview": "cached",
        "analysis": {"headline": "26.10 版本重點解析", "sections": [], "takeaways": [], "details": {}},
    }

    async def fake_get(_key: str):
        return cached

    async def fail_fetch(_url: str) -> str:
        raise AssertionError("network fetch should not happen on cache hit")

    monkeypatch.setattr(patch_notes_module.redis_client, "get", fake_get)
    monkeypatch.setattr(service, "_fetch_html", fail_fetch)

    announcement = await service.fetch_latest()

    assert announcement == cached


@pytest.mark.asyncio
async def test_fetch_latest_writes_payload_to_cache(monkeypatch):
    service = PatchNotesService()
    calls = []
    cache_writes = []

    async def fake_fetch_html(url: str) -> str:
        calls.append(url)
        if url.endswith("/patch-notes/"):
            return PATCH_INDEX_HTML
        return PATCH_ARTICLE_HTML

    async def fake_get(_key: str):
        return None

    async def fake_set(key: str, value, ttl=None):
        cache_writes.append((key, value, ttl))
        return True

    monkeypatch.setattr(service, "_fetch_html", fake_fetch_html)
    monkeypatch.setattr(patch_notes_module.redis_client, "get", fake_get)
    monkeypatch.setattr(patch_notes_module.redis_client, "set", fake_set)

    announcement = await service.fetch_latest()

    assert calls == [
        "https://www.leagueoflegends.com/zh-tw/news/tags/patch-notes/",
        "https://www.leagueoflegends.com/zh-tw/news/game-updates/league-of-legends-patch-26-10-notes/",
    ]
    assert announcement["version"] == "26.10"
    assert len(cache_writes) == 1
    assert cache_writes[0][0] == "patch_notes:latest:zh-tw"
