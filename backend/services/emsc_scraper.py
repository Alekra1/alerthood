"""EMSC European earthquake scraper.

Fetches recent earthquakes from the EMSC FDSN Event Service.
No auth required. Better European coverage than USGS with lower
magnitude threshold.

https://www.seismicportal.eu/fdsnws/event/1/
"""

import logging
from datetime import datetime, timezone, timedelta

import httpx

from db import get_supabase
from services.insert_events import insert_events_batch

logger = logging.getLogger(__name__)

EMSC_API_URL = "https://www.seismicportal.eu/fdsnws/event/1/query"

# European bounding box
MIN_LAT = 35
MAX_LAT = 72
MIN_LON = -25
MAX_LON = 45


def _mag_to_severity(mag: float) -> str:
    """Map earthquake magnitude to severity level."""
    if mag >= 5.0:
        return "critical"
    if mag >= 4.0:
        return "high"
    if mag >= 2.0:
        return "medium"
    return "low"


async def fetch_emsc_earthquakes() -> list[dict]:
    """Fetch recent European earthquakes from the EMSC FDSN service."""
    start_time = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")

    params = {
        "format": "json",
        "start": start_time,
        "minmag": "1.0",
        "limit": "500",
        "minlat": str(MIN_LAT),
        "maxlat": str(MAX_LAT),
        "minlon": str(MIN_LON),
        "maxlon": str(MAX_LON),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(EMSC_API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    features = data.get("features", [])
    events = []

    for feature in features:
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates", [])
        props = feature.get("properties", {})

        if len(coords) < 2:
            continue

        lng = coords[0]
        lat = coords[1]
        depth = coords[2] if len(coords) > 2 else None

        mag = props.get("mag")
        if mag is None:
            continue

        try:
            mag = float(mag)
        except (ValueError, TypeError):
            continue

        place = props.get("flynn_region", "Unknown region")
        time_str = props.get("time", "")
        unid = props.get("unid", "")
        source_id = props.get("source_id", "")

        # Parse occurred_at
        try:
            occurred_at = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            occurred_at = datetime.now(timezone.utc)

        # Build source_url
        source_url = source_id if source_id else f"emsc:{unid}"
        if not source_url:
            continue

        severity = _mag_to_severity(mag)
        depth_str = f", depth {depth:.1f} km" if depth is not None else ""

        events.append({
            "title": f"Earthquake M{mag:.1f}: {place}",
            "description": f"Magnitude {mag:.1f} earthquake{depth_str}. Region: {place}.",
            "threat_type": "natural",
            "severity": severity,
            "occurred_at": occurred_at.isoformat(),
            "location": f"SRID=4326;POINT({lng} {lat})",
            "location_label": place,
            "source_type": "emsc",
            "source_url": source_url,
            "relevance_score": min(100, int(mag * 20)),
            "_lat": lat,
            "_lng": lng,
        })

    logger.info("Fetched %d earthquakes from EMSC", len(events))
    return events


async def run_emsc_scraper():
    """Fetch latest EMSC earthquakes and insert into Supabase."""
    db = get_supabase()

    try:
        events = await fetch_emsc_earthquakes()
    except httpx.HTTPStatusError as e:
        logger.error("EMSC returned HTTP %d: %s", e.response.status_code, e.request.url)
        return
    except httpx.RequestError as e:
        logger.error("Network error fetching EMSC data: %s", e)
        return

    if not events:
        logger.info("No new earthquakes from EMSC")
        return

    # Match events to nearest area in a single batch RPC call
    points = [{"lat": e["_lat"], "lng": e["_lng"]} for e in events]
    batch_result = db.rpc("find_nearest_area_batch", {"points": points}).execute()
    area_by_idx = {row["idx"]: row["area_id"] for row in (batch_result.data or []) if row["area_id"]}

    matched = []
    for i, event in enumerate(events):
        area_id = area_by_idx.get(i)
        if area_id:
            event["area_id"] = area_id
            del event["_lat"]
            del event["_lng"]
            matched.append(event)

    if not matched:
        logger.info("No EMSC earthquakes matched any monitored area")
        return

    logger.info("Matched %d/%d earthquakes to areas", len(matched), len(events))

    inserted = insert_events_batch(db, matched, "EMSC")

    logger.info("Inserted %d/%d EMSC earthquakes into Supabase", inserted, len(matched))
