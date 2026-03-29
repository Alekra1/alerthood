"""Google News scraper using the GNews Python package.

For each monitored area, searches Google News for threat-related keywords
combined with the area's city name. Geocodes the city once with Nominatim
to get coordinates for the location field, then inserts matching articles
as events.

No API key required — GNews fetches Google News RSS under the hood.
"""

import asyncio
import logging
from datetime import datetime, timezone

from geopy.geocoders import Nominatim
from geopy.exc import GeopyError
from gnews import GNews

from db import get_supabase
from services.insert_events import insert_events_batch

logger = logging.getLogger(__name__)

# (keyword string, threat_type, severity)
THREAT_QUERIES: list[tuple[str, str, str]] = [
    ("shooting stabbing murder robbery assault attack", "crime", "high"),
    ("flood earthquake storm tornado wildfire hurricane", "natural", "high"),
    ("protest riot unrest demonstration", "disturbance", "medium"),
    ("power outage blackout gas leak explosion", "infrastructure", "medium"),
]

_geocoder = Nominatim(user_agent="alerthood/1.0")


def _geocode_city(city: str) -> tuple[float, float] | None:
    """Return (lat, lng) for a city name, or None if not found."""
    try:
        location = _geocoder.geocode(city, timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except GeopyError as e:
        logger.warning("Geocoding failed for '%s': %s", city, e)
    return None


def _fetch_articles(query: str, max_results: int = 10) -> list[dict]:
    """Synchronous GNews fetch — called via run_in_executor."""
    gn = GNews(language="en", period="1d", max_results=max_results)
    return gn.get_news(query) or []


def _parse_published(pub_date: str | None) -> str:
    """Parse GNews published date string to ISO format."""
    if not pub_date:
        return datetime.now(timezone.utc).isoformat()
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(pub_date, fmt).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return datetime.now(timezone.utc).isoformat()


def _build_event(
    article: dict,
    area: dict,
    threat_type: str,
    severity: str,
    lat: float,
    lng: float,
) -> dict | None:
    title = (article.get("title") or "").strip()
    source_url = article.get("url") or article.get("link")
    if not title or not source_url:
        return None

    description = (article.get("description") or "")[:500]
    publisher = article.get("publisher", {})
    publisher_name = publisher.get("title", "Google News") if isinstance(publisher, dict) else "Google News"
    occurred_at = _parse_published(article.get("published date"))
    city = (area.get("city") or area.get("name") or "").strip()

    return {
        "title": title[:255],
        "description": f"{description}\nSource: {publisher_name}".strip(),
        "threat_type": threat_type,
        "severity": severity,
        "occurred_at": occurred_at,
        "location": f"SRID=4326;POINT({lng} {lat})",
        "location_label": city,
        "source_type": "gnews",
        "source_url": source_url,
        "area_id": area["id"],
    }


async def run_gnews_scraper() -> None:
    """Fetch Google News threat articles per monitored area and insert into Supabase."""
    db = get_supabase()

    areas_result = db.table("areas").select("id, name, city").eq("is_active", True).execute()
    areas = areas_result.data or []

    if not areas:
        logger.info("GNews scraper: no active areas, skipping")
        return

    loop = asyncio.get_running_loop()
    events_to_insert: list[dict] = []
    seen_urls: set[str] = set()

    # Group areas by unique city — geocode and query once per city, not per area
    city_to_areas: dict[str, list[dict]] = {}
    for area in areas:
        city = (area.get("city") or area.get("name") or "").strip()
        if city:
            city_to_areas.setdefault(city, []).append(area)

    city_coords: dict[str, tuple[float, float]] = {}
    for city in city_to_areas:
        coords = await loop.run_in_executor(None, _geocode_city, city)
        if coords:
            city_coords[city] = coords
        else:
            logger.warning("GNews scraper: could not geocode '%s', skipping", city)
        await asyncio.sleep(1.1)  # Nominatim policy: max 1 req/s

    for city, city_areas in city_to_areas.items():
        if city not in city_coords:
            continue
        lat, lng = city_coords[city]
        representative_area = city_areas[0]  # use first area for event; area_id set below

        for keyword_str, threat_type, severity in THREAT_QUERIES:
            query = f"{city} {keyword_str}"
            try:
                articles = await loop.run_in_executor(None, _fetch_articles, query)
            except Exception:
                logger.exception("GNews fetch failed for query: %s", query)
                continue

            for article in articles:
                event = _build_event(article, representative_area, threat_type, severity, lat, lng)
                if not event:
                    continue
                url = event["source_url"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                events_to_insert.append(event)

    if not events_to_insert:
        logger.info("GNews scraper: no articles found")
        return

    logger.info("GNews scraper: %d articles across %d unique cities", len(events_to_insert), len(city_coords))

    inserted = insert_events_batch(db, events_to_insert, "GNews")
    logger.info("GNews scraper: inserted %d/%d events", inserted, len(events_to_insert))
