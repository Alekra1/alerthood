"""UK Police street-level crime scraper.

Fetches street-level crime data from data.police.uk.
Free, no auth required. Updated monthly.
https://data.police.uk/docs/
"""

import logging
from datetime import datetime, timezone, timedelta

import httpx

from db import get_supabase

logger = logging.getLogger(__name__)

UK_POLICE_API_URL = "https://data.police.uk/api"

# UK Police crime categories → our threat types
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


async def fetch_uk_crimes_for_area(lat: float, lng: float, date: str | None = None) -> list[dict]:
    """Fetch street-level crimes near a point. Date format: YYYY-MM."""
    if date is None:
        # Use 2 months ago (latest available data is usually 1-2 months behind)
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

        month = crime.get("month", date)
        # UK police dates are YYYY-MM, use first of month
        occurred_at = f"{month}-01T00:00:00+00:00"

        street_name = street.get("name", "Unknown")

        events.append({
            "title": f"{category.replace('-', ' ').title()}: {street_name}",
            "description": f"UK Police report. Category: {category}. Outcome: {crime.get('outcome_status', {}).get('category', 'Unknown') if crime.get('outcome_status') else 'Under investigation'}",
            "threat_type": threat_type,
            "severity": severity,
            "occurred_at": occurred_at,
            "location": f"SRID=4326;POINT({clng} {clat})",
            "location_label": street_name,
            "source_type": "uk_police",
            "source_url": None,
            "relevance_score": {"high": 80, "medium": 60, "low": 40}.get(severity, 50),
        })

    return events


async def run_uk_police_scraper():
    """Fetch UK crime data for all UK-based monitored areas."""
    db = get_supabase()

    # Get all active UK areas
    areas = (
        db.table("areas")
        .select("id, name, city, radius_km")
        .eq("is_active", True)
        .execute()
    )

    if not areas.data:
        return

    # UK cities we know about
    uk_cities = {"London", "Manchester", "Edinburgh", "Birmingham", "Bristol", "Leeds", "Liverpool", "Glasgow", "Cardiff", "Belfast"}

    uk_areas = [a for a in areas.data if a.get("city") in uk_cities]
    if not uk_areas:
        logger.info("No UK areas found, skipping UK Police scraper")
        return

    total_inserted = 0

    for area in uk_areas:
        # Get area center coordinates
        center = db.rpc("area_center_coords", {"area_id": area["id"]}).execute()

        if not center.data or len(center.data) == 0:
            # Fallback: use the area's known city center
            continue

        lat = center.data[0].get("lat")
        lng = center.data[0].get("lng")

        if not lat or not lng:
            continue

        try:
            crimes = await fetch_uk_crimes_for_area(lat, lng)
        except httpx.HTTPError as e:
            logger.error("UK Police API error for %s: %s", area["name"], e)
            continue
        except Exception as e:
            logger.error("UK Police scraper failed for %s: %s", area["name"], e)
            continue

        if not crimes:
            continue

        logger.info("Fetched %d crimes for %s", len(crimes), area["name"])

        # Add area_id and insert
        inserted = 0
        for crime in crimes[:100]:  # Cap at 100 per area per cycle
            crime["area_id"] = area["id"]
            try:
                db.table("events").insert(crime).execute()
                inserted += 1
            except Exception as e:
                logger.warning("Failed to insert UK crime: %s", type(e).__name__)

        total_inserted += inserted

    logger.info("UK Police scraper: inserted %d crimes across %d UK areas", total_inserted, len(uk_areas))
