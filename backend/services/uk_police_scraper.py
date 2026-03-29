"""UK Police street-level crime scraper.

Fetches street-level crime data from data.police.uk.
Free, no auth required. Updated monthly.
https://data.police.uk/docs/
"""

import logging
from datetime import datetime, timezone, timedelta

import httpx

from db import get_supabase
from services.insert_events import insert_events_batch

logger = logging.getLogger(__name__)

UK_POLICE_API_URL = "https://data.police.uk/api"

CATEGORY_TO_THREAT = {
    "violent-crime": "crime",
    "robbery": "crime",
    "burglary": "crime",
    "theft-from-the-person": "crime",
    "shoplifting": "crime",
    "criminal-damage-arson": "crime",
    "drugs": "crime",
    "possession-of-weapons": "crime",
    "public-order": "disturbance",
    "anti-social-behaviour": "disturbance",
    "other-crime": "crime",
    "vehicle-crime": "crime",
    "bicycle-theft": "crime",
    "other-theft": "crime",
}

CATEGORY_TO_SEVERITY = {
    "violent-crime": "high",
    "robbery": "high",
    "possession-of-weapons": "high",
    "criminal-damage-arson": "medium",
    "burglary": "medium",
    "drugs": "medium",
    "theft-from-the-person": "medium",
    "shoplifting": "low",
    "public-order": "low",
    "anti-social-behaviour": "low",
    "vehicle-crime": "low",
    "bicycle-theft": "low",
    "other-theft": "low",
    "other-crime": "low",
}

# UK cities — case-insensitive matching
UK_CITIES = {
    "london", "manchester", "edinburgh", "birmingham", "bristol",
    "leeds", "liverpool", "glasgow", "cardiff", "belfast",
    "nottingham", "sheffield", "newcastle", "oxford", "cambridge",
    "brighton", "reading", "coventry", "leicester", "southampton",
}


async def fetch_uk_crimes_for_area(lat: float, lng: float, date: str | None = None) -> list[dict]:
    """Fetch street-level crimes near a point. Date format: YYYY-MM."""
    if date is None:
        d = datetime.now(timezone.utc) - timedelta(days=60)
        date = d.strftime("%Y-%m")

    url = f"{UK_POLICE_API_URL}/crimes-street/all-crime"
    params = {"lat": lat, "lng": lng, "date": date}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        if resp.status_code == 503:
            logger.warning("UK Police API rate limited or unavailable")
            return []
        resp.raise_for_status()
        data = resp.json()

    events = []
    for crime in data:
        location = crime.get("location", {})
        street = location.get("street", {})

        try:
            clat = float(location.get("latitude", 0))
            clng = float(location.get("longitude", 0))
        except (ValueError, TypeError):
            continue

        if clat == 0 and clng == 0:
            continue

        category = crime.get("category", "other-crime")
        threat_type = CATEGORY_TO_THREAT.get(category, "crime")
        severity = CATEGORY_TO_SEVERITY.get(category, "low")
        crime_id = crime.get("persistent_id", "")

        month = crime.get("month", date)
        occurred_at = f"{month}-01T00:00:00+00:00"
        street_name = street.get("name", "Unknown")

        events.append({
            "title": f"{category.replace('-', ' ').title()}: {street_name}",
            "description": f"UK Police report. Category: {category}.",
            "threat_type": threat_type,
            "severity": severity,
            "occurred_at": occurred_at,
            "location": f"SRID=4326;POINT({clng} {clat})",
            "location_label": street_name,
            "source_type": "uk_police",
            "source_url": crime_id if crime_id else None,
            "relevance_score": {"high": 80, "medium": 60, "low": 40}.get(severity, 50),
        })

    logger.info("Fetched %d crimes from UK Police for (%.4f, %.4f)", len(events), lat, lng)
    return events


async def run_uk_police_scraper():
    """Fetch UK crime data for all UK-based monitored areas."""
    db = get_supabase()

    try:
        areas = (
            db.table("areas")
            .select("id, name, city, radius_km")
            .eq("is_active", True)
            .execute()
        )
    except Exception:
        logger.exception("Failed to query areas for UK Police scraper")
        return

    if not areas.data:
        return

    uk_areas = [a for a in areas.data if a.get("city", "").lower() in UK_CITIES]
    if not uk_areas:
        logger.info("No UK areas found, skipping UK Police scraper")
        return

    # Check if we already imported this month's data
    d = datetime.now(timezone.utc) - timedelta(days=60)
    check_month = f"{d.strftime('%Y-%m')}-01T00:00:00+00:00"
    existing = db.table("events").select("id", count="exact").eq("source_type", "uk_police").gte("occurred_at", check_month).execute()
    if existing.count and existing.count > 0:
        logger.info("UK Police data already imported for this month (%d events), skipping", existing.count)
        return

    total_inserted = 0

    for area in uk_areas:
        try:
            center = db.rpc("area_center_coords", {"area_id": area["id"]}).execute()
        except Exception:
            logger.exception("Failed to get center for area %s", area["name"])
            continue

        if not center.data or len(center.data) == 0:
            continue

        lat = center.data[0].get("lat")
        lng = center.data[0].get("lng")
        if not lat or not lng:
            continue

        try:
            crimes = await fetch_uk_crimes_for_area(lat, lng)
        except httpx.HTTPStatusError as e:
            logger.error("UK Police API returned HTTP %d for %s", e.response.status_code, area["name"])
            continue
        except httpx.RequestError as e:
            logger.error("Network error fetching UK Police data for %s: %s", area["name"], e)
            continue

        if not crimes:
            continue

        # Cap at 100 per area and add area_id
        to_insert = crimes[:100]
        for crime in to_insert:
            crime["area_id"] = area["id"]

        inserted = insert_events_batch(db, to_insert, "UK Police")

        total_inserted += inserted

    logger.info("UK Police scraper: inserted %d crimes across %d UK areas", total_inserted, len(uk_areas))
