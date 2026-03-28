"""USGS Earthquake scraper.

Fetches recent earthquakes from the USGS GeoJSON feed.
Free, no auth required. Updates every few minutes.
https://earthquake.usgs.gov/fdsnws/event/1/
"""

import logging
from datetime import datetime, timezone, timedelta

import httpx

from db import get_supabase

logger = logging.getLogger(__name__)

USGS_API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

MAGNITUDE_TO_SEVERITY = [
    (6.0, "critical"),
    (5.0, "high"),
    (3.0, "medium"),
    (0.0, "low"),
]


def _mag_to_severity(mag: float) -> str:
    for threshold, level in MAGNITUDE_TO_SEVERITY:
        if mag >= threshold:
            return level
    return "low"


async def fetch_usgs_earthquakes(hours_back: int = 24, min_magnitude: float = 2.5) -> list[dict]:
    """Fetch recent earthquakes from USGS."""
    since = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%S")

    params = {
        "format": "geojson",
        "starttime": since,
        "minmagnitude": min_magnitude,
        "orderby": "time",
        "limit": 200,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(USGS_API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    features = data.get("features", [])
    events = []

    for f in features:
        props = f.get("properties", {})
        coords = f.get("geometry", {}).get("coordinates", [])

        if len(coords) < 2:
            continue

        lng, lat = coords[0], coords[1]
        mag = props.get("mag", 0) or 0
        place = props.get("place", "Unknown location")
        time_ms = props.get("time")

        occurred_at = (
            datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc).isoformat()
            if time_ms
            else datetime.now(timezone.utc).isoformat()
        )

        events.append({
            "title": f"Earthquake M{mag:.1f}: {place}",
            "description": f"Magnitude {mag:.1f} earthquake. {props.get('type', 'earthquake').title()}. Source: USGS",
            "threat_type": "natural",
            "severity": _mag_to_severity(mag),
            "occurred_at": occurred_at,
            "location": f"SRID=4326;POINT({lng} {lat})",
            "location_label": place,
            "source_type": "usgs",
            "source_url": props.get("url"),
            "relevance_score": min(100, int(mag * 15)),
            "_lat": lat,
            "_lng": lng,
        })

    logger.info("Fetched %d earthquakes from USGS (M%.1f+ in last %dh)", len(events), min_magnitude, hours_back)
    return events


async def run_usgs_scraper():
    """Fetch earthquakes and insert into Supabase."""
    db = get_supabase()

    try:
        events = await fetch_usgs_earthquakes()
    except httpx.HTTPError as e:
        logger.error("USGS API error: %s", e)
        return
    except Exception as e:
        logger.error("USGS scraper failed: %s", e)
        return

    if not events:
        logger.info("No new earthquakes from USGS")
        return

    matched = []
    for event in events:
        result = db.rpc("find_nearest_area", {"lat": event["_lat"], "lng": event["_lng"]}).execute()
        area_id = result.data
        if area_id:
            event["area_id"] = area_id
            del event["_lat"]
            del event["_lng"]
            matched.append(event)
        else:
            del event["_lat"]
            del event["_lng"]

    if not matched:
        logger.info("No USGS earthquakes matched any monitored area")
        return

    inserted = 0
    for event in matched:
        try:
            db.table("events").insert(event).execute()
            inserted += 1
        except Exception as e:
            logger.warning("Failed to insert USGS event: %s", type(e).__name__)

    logger.info("Inserted %d/%d USGS earthquakes", inserted, len(matched))
