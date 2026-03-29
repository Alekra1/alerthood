"""Tests for gnews_scraper.py — unit tests for helpers and integration-style
test for run_gnews_scraper()."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from geopy.exc import GeopyError as GeocoderError

from services.gnews_scraper import (
    _build_event,
    _geocode_city,
    _parse_published,
    run_gnews_scraper,
)


# ---------------------------------------------------------------------------
# _parse_published
# ---------------------------------------------------------------------------


def test_parse_published_rfc2822():
    """Valid RFC 2822 date string is parsed to ISO-8601."""
    result = _parse_published("Sat, 29 Mar 2026 10:00:00 GMT")
    dt = datetime.fromisoformat(result)
    assert dt.year == 2026
    assert dt.month == 3
    assert dt.day == 29
    assert dt.hour == 10
    assert dt.minute == 0
    assert dt.second == 0
    assert dt.tzinfo is not None


def test_parse_published_iso():
    """Valid ISO-8601 date string is parsed to ISO-8601."""
    result = _parse_published("2026-03-29T10:00:00Z")
    dt = datetime.fromisoformat(result)
    assert dt.year == 2026
    assert dt.month == 3
    assert dt.day == 29
    assert dt.hour == 10
    assert dt.tzinfo is not None


def test_parse_published_none_returns_current_time():
    """None input returns a current-UTC-time ISO string."""
    before = datetime.now(timezone.utc)
    result = _parse_published(None)
    after = datetime.now(timezone.utc)

    dt = datetime.fromisoformat(result)
    assert before <= dt <= after


def test_parse_published_invalid_format_returns_current_time():
    """Unrecognised format falls back to current UTC time."""
    before = datetime.now(timezone.utc)
    result = _parse_published("not-a-date-at-all")
    after = datetime.now(timezone.utc)

    dt = datetime.fromisoformat(result)
    assert before <= dt <= after


# ---------------------------------------------------------------------------
# _build_event
# ---------------------------------------------------------------------------

_AREA = {"id": "area-001", "name": "Central Park", "city": "New York"}


def _base_article(**overrides):
    """Helper to build a minimal article dict with sensible defaults."""
    article = {
        "title": "Shooting reported downtown",
        "url": "https://news.example.com/shooting",
        "description": "Police are investigating a shooting incident.",
        "publisher": {"title": "Example News"},
        "published date": "Sat, 29 Mar 2026 10:00:00 GMT",
    }
    article.update(overrides)
    return article


def test_build_event_valid_input():
    """Valid article + area produces a correctly-shaped dict."""
    article = _base_article()
    result = _build_event(article, _AREA, "crime", "high", 40.71, -74.01)

    assert result is not None
    assert result["title"] == "Shooting reported downtown"
    assert result["threat_type"] == "crime"
    assert result["severity"] == "high"
    assert result["source_type"] == "gnews"
    assert result["source_url"] == "https://news.example.com/shooting"
    assert result["area_id"] == "area-001"
    assert result["location"] == "SRID=4326;POINT(-74.01 40.71)"
    assert result["location_label"] == "New York"
    assert "Example News" in result["description"]
    assert "2026-03-29" in result["occurred_at"]


def test_build_event_missing_title_returns_none():
    """Article with no title (or whitespace-only) returns None."""
    for title_value in (None, "", "   "):
        article = _base_article(title=title_value)
        result = _build_event(article, _AREA, "crime", "high", 40.71, -74.01)
        assert result is None, f"Expected None for title={title_value!r}"


def test_build_event_missing_both_url_and_link_returns_none():
    """Article with neither url nor link returns None."""
    article = _base_article()
    del article["url"]
    result = _build_event(article, _AREA, "crime", "high", 40.71, -74.01)
    assert result is None


def test_build_event_url_present_link_absent_uses_url():
    """When url is present and link is absent, source_url uses url."""
    article = _base_article()
    assert "link" not in article  # no link key
    result = _build_event(article, _AREA, "crime", "high", 40.71, -74.01)
    assert result["source_url"] == "https://news.example.com/shooting"


def test_build_event_url_absent_link_present_uses_link():
    """When url is absent but link is present, source_url uses link."""
    article = _base_article(url=None, link="https://news.example.com/alt-link")
    result = _build_event(article, _AREA, "crime", "high", 40.71, -74.01)
    assert result is not None
    assert result["source_url"] == "https://news.example.com/alt-link"


def test_build_event_long_title_truncated():
    """Title longer than 255 chars is truncated."""
    long_title = "A" * 300
    article = _base_article(title=long_title)
    result = _build_event(article, _AREA, "crime", "high", 40.71, -74.01)
    assert result is not None
    assert len(result["title"]) == 255


def test_build_event_long_description_truncated():
    """Description longer than 500 chars is truncated before the source suffix."""
    long_desc = "B" * 600
    article = _base_article(description=long_desc)
    result = _build_event(article, _AREA, "crime", "high", 40.71, -74.01)
    assert result is not None
    # The description field is "{truncated_desc}\nSource: {publisher}"
    raw_desc = result["description"]
    # The first 500 chars should be from the original (truncated), plus the source suffix
    assert raw_desc.startswith("B" * 500)


def test_build_event_publisher_dict_extracts_title():
    """When publisher is a dict, its 'title' value is used in the description."""
    article = _base_article(publisher={"title": "My Custom Outlet"})
    result = _build_event(article, _AREA, "crime", "high", 40.71, -74.01)
    assert result is not None
    assert "My Custom Outlet" in result["description"]


def test_build_event_publisher_string_uses_google_news():
    """When publisher is a string (not dict), defaults to 'Google News'."""
    article = _base_article(publisher="SomeStringOutlet")
    result = _build_event(article, _AREA, "crime", "high", 40.71, -74.01)
    assert result is not None
    assert "Google News" in result["description"]


def test_build_event_city_from_area_city():
    """location_label uses area['city'] when present."""
    article = _base_article()
    area = {"id": "area-002", "name": "Manhattan", "city": "New York City"}
    result = _build_event(article, area, "crime", "high", 40.71, -74.01)
    assert result["location_label"] == "New York City"


def test_build_event_city_falls_back_to_area_name():
    """When area['city'] is missing, location_label falls back to area['name']."""
    article = _base_article()
    area = {"id": "area-003", "name": "Manhattan"}
    result = _build_event(article, area, "crime", "high", 40.71, -74.01)
    assert result["location_label"] == "Manhattan"


# ---------------------------------------------------------------------------
# _geocode_city
# ---------------------------------------------------------------------------


def test_geocode_city_success():
    """Successful geocoding returns (lat, lng) tuple."""
    mock_location = MagicMock()
    mock_location.latitude = 42.6977
    mock_location.longitude = 23.3219

    with patch("services.gnews_scraper._geocoder.geocode", return_value=mock_location):
        result = _geocode_city("Sofia")

    assert result == (42.6977, 23.3219)


def test_geocode_city_not_found():
    """When Nominatim returns None, _geocode_city returns None."""
    with patch("services.gnews_scraper._geocoder.geocode", return_value=None):
        result = _geocode_city("NonexistentCityXYZ")

    assert result is None


def test_geocode_city_geocoder_error():
    """When Nominatim raises GeocoderError, returns None (no exception propagation)."""
    with patch("services.gnews_scraper._geocoder.geocode", side_effect=GeocoderError("service unavailable")):
        result = _geocode_city("Sofia")

    assert result is None


# ---------------------------------------------------------------------------
# run_gnews_scraper — integration-style pipeline test
# ---------------------------------------------------------------------------


async def test_run_gnews_scraper_full_pipeline():
    """Happy-path end-to-end: one area, one keyword query produces one event insertion."""
    area = {"id": "area-100", "name": "Sofia", "city": "Sofia"}

    # -- Supabase mock --
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [area]

    # -- Geocoding mock --
    mock_location = MagicMock()
    mock_location.latitude = 42.6977
    mock_location.longitude = 23.3219

    # -- GNews article mock --
    article = {
        "title": "Major flooding hits downtown Sofia",
        "url": "https://news.example.com/flood-sofia",
        "description": "Severe flooding reported after heavy rain.",
        "publisher": {"title": "Sofia News Agency"},
        "published date": "Sat, 29 Mar 2026 08:30:00 GMT",
    }

    def fake_geocode(city, timeout=10):
        return mock_location

    def fake_fetch_articles(query, max_results=10):
        # Only return articles for the first keyword query to keep test simple
        if "flood" in query:
            return [article]
        return []

    with (
        patch("services.gnews_scraper.get_supabase", return_value=mock_db),
        patch("services.gnews_scraper._geocoder.geocode", side_effect=fake_geocode),
        patch("services.gnews_scraper._fetch_articles", side_effect=fake_fetch_articles),
        patch("services.gnews_scraper.insert_events_batch", return_value=1) as mock_insert,
    ):
        await run_gnews_scraper()

    mock_insert.assert_called_once()
    inserted_events = mock_insert.call_args[0][1]
    assert len(inserted_events) >= 1

    event = inserted_events[0]
    assert event["title"] == "Major flooding hits downtown Sofia"
    assert event["threat_type"] == "natural"
    assert event["severity"] == "high"
    assert event["source_url"] == "https://news.example.com/flood-sofia"
    assert event["area_id"] == "area-100"
    assert event["location_label"] == "Sofia"
    assert event["source_type"] == "gnews"
    assert event["location"] == "SRID=4326;POINT(23.3219 42.6977)"


async def test_run_gnews_scraper_no_active_areas():
    """When there are no active areas, the scraper exits early with no inserts."""
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with (
        patch("services.gnews_scraper.get_supabase", return_value=mock_db),
        patch("services.gnews_scraper.insert_events_batch", return_value=0) as mock_insert,
    ):
        await run_gnews_scraper()

    mock_insert.assert_not_called()


async def test_run_gnews_scraper_geocode_failure_skips_area():
    """When geocoding fails for an area, it is skipped entirely."""
    area = {"id": "area-200", "name": "UnknownCity", "city": "UnknownCity"}

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [area]

    with (
        patch("services.gnews_scraper.get_supabase", return_value=mock_db),
        patch("services.gnews_scraper._geocoder.geocode", return_value=None),
        patch("services.gnews_scraper.insert_events_batch", return_value=0) as mock_insert,
    ):
        await run_gnews_scraper()

    mock_insert.assert_not_called()


async def test_run_gnews_scraper_deduplicates_urls():
    """When the same article URL appears across multiple keyword queries, it is inserted only once."""
    area = {"id": "area-300", "name": "London", "city": "London"}

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [area]

    mock_location = MagicMock()
    mock_location.latitude = 51.5074
    mock_location.longitude = -0.1278

    duplicate_article = {
        "title": "Big storm causes flooding in London",
        "url": "https://news.example.com/storm-london",
        "description": "A major storm hit London.",
        "publisher": {"title": "London Times"},
        "published date": "2026-03-29T12:00:00Z",
    }

    def fake_fetch_articles(query, max_results=10):
        # Return the same article for every keyword query
        return [duplicate_article]

    with (
        patch("services.gnews_scraper.get_supabase", return_value=mock_db),
        patch("services.gnews_scraper._geocoder.geocode", return_value=mock_location),
        patch("services.gnews_scraper._fetch_articles", side_effect=fake_fetch_articles),
        patch("services.gnews_scraper.insert_events_batch", return_value=1) as mock_insert,
    ):
        await run_gnews_scraper()

    mock_insert.assert_called_once()
    inserted_events = mock_insert.call_args[0][1]
    # Same URL across 4 keyword queries, but only one event should be inserted
    assert len(inserted_events) == 1
    assert inserted_events[0]["source_url"] == "https://news.example.com/storm-london"
