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
        usgs_id = f.get("id", "")

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
            "_dedup_key": f"usgs:{usgs_id}",
        })

    logger.info("Fetched %d earthquakes from USGS (M%.1f+ in last %dh)", len(events), min_magnitude, hours_back)
    return events


async def run_usgs_scraper():
    """Fetch earthquakes and insert into Supabase."""
    db = get_supabase()

    try:
        events = await fetch_usgs_earthquakes()
    except httpx.HTTPStatusError as e:
        logger.error("USGS API returned HTTP %d: %s", e.response.status_code, e.request.url)
        return
    except httpx.RequestError as e:
        logger.error("Network error fetching USGS data: %s", e)
        return

    if not events:
        logger.info("No new earthquakes from USGS")
        return

    matched = []
    for event in events:
        try:
            result = db.rpc("find_nearest_area", {"lat": event["_lat"], "lng": event["_lng"]}).execute()
        except Exception:
            logger.exception("Area matching failed for USGS event")
            continue
        area_id = result.data
        if area_id:
            event["area_id"] = area_id
            del event["_lat"]
            del event["_lng"]
            event.pop("_dedup_key")
            # Dedup check
            existing = db.table("events").select("id", count="exact").eq("source_type", "usgs").eq("source_url", event.get("source_url", "")).execute()
            if existing.count and existing.count > 0:
                continue
            matched.append(event)

    if not matched:
        logger.info("No USGS earthquakes matched any monitored area")
        return

    inserted = 0
    for i in range(0, len(matched), 50):
        chunk = matched[i : i + 50]
        try:
            db.table("events").insert(chunk).execute()
            inserted += len(chunk)
        except Exception:
            logger.exception("Failed to insert USGS events chunk %d-%d", i, i + len(chunk))

    logger.info("Inserted %d/%d USGS earthquakes", inserted, len(matched))
