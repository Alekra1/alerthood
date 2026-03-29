"""Tests for bg_news_scraper.py — pipeline integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.bg_news_scraper import _dedup, _fetch_feed, _parse_pub_date


# ---------------------------------------------------------------------------
# _parse_pub_date
# ---------------------------------------------------------------------------


def test_parse_pub_date_returns_iso_from_parsed():
    """Valid published_parsed produces an ISO-8601 string."""
    entry = MagicMock()
    entry.published_parsed = (2026, 3, 29, 10, 0, 0)
    result = _parse_pub_date(entry)
    assert result.startswith("2026-03-29")


def test_parse_pub_date_falls_back_to_now_when_missing():
    """Missing published_parsed falls back to current UTC time."""
    entry = MagicMock()
    entry.published_parsed = None
    result = _parse_pub_date(entry)
    assert "2026" in result or "202" in result  # just verify it's a date string


# ---------------------------------------------------------------------------
# _fetch_feed
# ---------------------------------------------------------------------------


async def test_fetch_feed_returns_items_on_success():
    """feedparser returns entries → list of dicts with url, title, pub_date."""
    mock_entry = MagicMock()
    mock_entry.link = "https://example.bg/article/1"
    mock_entry.title = "Мъж е намушкан в София"
    mock_entry.published_parsed = (2026, 3, 29, 8, 0, 0)

    mock_parsed = MagicMock()
    mock_parsed.entries = [mock_entry]
    mock_parsed.get.return_value = False  # bozo = False

    with patch("services.bg_news_scraper.feedparser.parse", return_value=mock_parsed):
        result = await _fetch_feed("https://example.bg/rss")

    assert len(result) == 1
    assert result[0]["url"] == "https://example.bg/article/1"
    assert result[0]["title"] == "Мъж е намушкан в София"


async def test_fetch_feed_returns_empty_on_exception():
    """feedparser.parse raises → empty list, no propagation."""
    with patch("services.bg_news_scraper.asyncio.to_thread", side_effect=Exception("network error")):
        result = await _fetch_feed("https://broken.bg/rss")

    assert result == []


async def test_fetch_feed_skips_entries_without_link():
    """Entries with no link or title are silently skipped."""
    entry_no_link = MagicMock()
    entry_no_link.link = ""
    entry_no_link.title = "Some title"
    entry_no_link.published_parsed = None

    entry_no_title = MagicMock()
    entry_no_title.link = "https://example.bg/a"
    entry_no_title.title = "   "
    entry_no_title.published_parsed = None

    mock_parsed = MagicMock()
    mock_parsed.entries = [entry_no_link, entry_no_title]
    mock_parsed.get.return_value = False

    with patch("services.bg_news_scraper.feedparser.parse", return_value=mock_parsed):
        result = await _fetch_feed("https://example.bg/rss")

    assert result == []


# ---------------------------------------------------------------------------
# _dedup
# ---------------------------------------------------------------------------


async def test_dedup_removes_known_urls():
    """Articles whose source_url already exists in DB are dropped."""
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
        {"source_url": "https://example.bg/article/1"}
    ]

    items = [
        {"url": "https://example.bg/article/1", "title": "Known"},
        {"url": "https://example.bg/article/2", "title": "New"},
    ]
    result = await _dedup(mock_db, items)

    assert len(result) == 1
    assert result[0]["url"] == "https://example.bg/article/2"


async def test_dedup_returns_all_when_db_fails():
    """If the dedup query raises, all items are returned (safe fallback)."""
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.in_.return_value.execute.side_effect = Exception("DB error")

    items = [{"url": "https://example.bg/article/1", "title": "Title"}]
    result = await _dedup(mock_db, items)

    assert len(result) == 1


async def test_dedup_returns_empty_on_empty_input():
    """Empty input → empty output without hitting DB."""
    mock_db = MagicMock()
    result = await _dedup(mock_db, [])
    assert result == []
    mock_db.table.assert_not_called()


# ---------------------------------------------------------------------------
# run_bg_news_scraper — full pipeline with all mocks
# ---------------------------------------------------------------------------


async def test_run_scraper_skips_when_all_urls_known():
    """If all articles are duplicate, nothing is passed to AI or inserted."""
    mock_entry = MagicMock()
    mock_entry.link = "https://example.bg/article/1"
    mock_entry.title = "Known article"
    mock_entry.published_parsed = (2026, 3, 29, 9, 0, 0)

    mock_parsed = MagicMock()
    mock_parsed.entries = [mock_entry]
    mock_parsed.get.return_value = False

    mock_db = MagicMock()
    # Dedup returns all URLs as known
    mock_db.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
        {"source_url": "https://example.bg/article/1"}
    ]

    with (
        patch("services.bg_news_scraper.get_supabase", return_value=mock_db),
        patch("services.bg_news_scraper.feedparser.parse", return_value=mock_parsed),
        patch("services.bg_news_scraper.filter_relevant_titles", new=AsyncMock()) as mock_stage1,
    ):
        from services.bg_news_scraper import run_bg_news_scraper
        await run_bg_news_scraper()

    mock_stage1.assert_not_called()


async def test_run_scraper_inserts_events_end_to_end():
    """Full happy-path pipeline: one article goes through all stages and is inserted."""
    mock_entry = MagicMock()
    mock_entry.link = "https://example.bg/article/42"
    mock_entry.title = "Мъж е намушкан в Лозенец"
    mock_entry.published_parsed = (2026, 3, 29, 10, 0, 0)

    mock_parsed = MagicMock()
    mock_parsed.entries = [mock_entry]
    mock_parsed.get.return_value = False

    mock_db = MagicMock()
    # No known URLs → everything is new
    mock_db.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []
    # find_nearest_area_batch returns area for index 0
    mock_db.rpc.return_value.execute.return_value.data = [{"idx": 0, "area_id": "area-uuid-123"}]

    extracted = {
        "city": "Sofia",
        "location_text": "ул. Витоша 15, Лозенец",
        "threat_type": "crime",
        "severity": "high",
        "title_en": "Man stabbed in Lozenets",
        "summary_en": "A man was stabbed.",
    }

    with (
        patch("services.bg_news_scraper.get_supabase", return_value=mock_db),
        patch("services.bg_news_scraper.feedparser.parse", return_value=mock_parsed),
        patch("services.bg_news_scraper.filter_relevant_titles", new=AsyncMock(return_value=[0])),
        patch("services.bg_news_scraper.fetch_article_text", new=AsyncMock(return_value="Full article body")),
        patch("services.bg_news_scraper.extract_event", new=AsyncMock(return_value=extracted)),
        patch("services.bg_news_scraper.geocode_location", new=AsyncMock(return_value=(42.697, 23.321))),
        patch("services.bg_news_scraper.insert_events_batch", return_value=1) as mock_insert,
        patch("services.bg_news_scraper.asyncio.sleep", new=AsyncMock()),
    ):
        from services.bg_news_scraper import run_bg_news_scraper
        await run_bg_news_scraper()

    mock_insert.assert_called_once()
    events_inserted = mock_insert.call_args[0][1]
    assert len(events_inserted) == 1
    event = events_inserted[0]
    assert event["title"] == "Man stabbed in Lozenets"
    assert event["threat_type"] == "crime"
    assert event["severity"] == "high"
    assert event["area_id"] == "area-uuid-123"
    assert event["source_url"] == "https://example.bg/article/42"
    assert event["relevance_score"] == 75  # high → 75
