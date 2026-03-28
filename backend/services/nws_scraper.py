"""National Weather Service alerts scraper.

Fetches active weather alerts (tornados, floods, fires, etc.) from NWS.
Free, no auth required. US-only.
https://api.weather.gov/alerts
"""

import logging
from datetime import datetime, timezone

import httpx

from db import get_supabase

logger = logging.getLogger(__name__)

NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"

SEVERITY_MAP = {
    "Extreme": "critical",
    "Severe": "high",
    "Moderate": "medium",
    "Minor": "low",
    "Unknown": "low",
}

# NWS event types → our threat types
EVENT_TO_THREAT = {
    "Tornado": "natural",
    "Hurricane": "natural",
    "Earthquake": "natural",
    "Flood": "natural",
    "Flash Flood": "natural",
    "Severe Thunderstorm": "natural",
    "Winter Storm": "natural",
    "Blizzard": "natural",
    "Ice Storm": "natural",
    "Tsunami": "natural",
    "Wildfire": "natural",
    "Fire Weather": "natural",
    "Extreme Heat": "natural",
    "Excessive Heat": "natural",
    "Dense Fog": "infrastructure",
    "High Wind": "natural",
    "Dust Storm": "natural",
    "Avalanche": "natural",
}


async def fetch_nws_alerts() -> list[dict]:
    """Fetch active NWS alerts."""
    headers = {"User-Agent": "AlertHood/1.0 (safety-app)", "Accept": "application/geo+json"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(NWS_ALERTS_URL, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    features = data.get("features", [])
    events = []

    for f in features:
        props = f.get("properties", {})
        geometry = f.get("geometry")

        # NWS alerts often have polygon geometry, not points
        # Try to get a centroid from the geometry
        lat, lng = None, None

        if geometry and geometry.get("type") == "Point":
            coords = geometry.get("coordinates", [])
            if len(coords) >= 2:
                lng, lat = coords[0], coords[1]
        elif geometry and geometry.get("type") == "Polygon":
            coords = geometry["coordinates"][0]
            lat = sum(c[1] for c in coords) / len(coords)
            lng = sum(c[0] for c in coords) / len(coords)

        if lat is None or lng is None:
            continue

        event_type = props.get("event", "")
        threat_type = EVENT_TO_THREAT.get(event_type, "natural")
        severity = SEVERITY_MAP.get(props.get("severity", "Unknown"), "low")

        onset = props.get("onset") or props.get("sent") or datetime.now(timezone.utc).isoformat()
        headline = props.get("headline", event_type)
        description = (props.get("description", "") or "")[:500]

        events.append({
            "title": headline[:200],
            "description": description,
            "threat_type": threat_type,
            "severity": severity,
            "occurred_at": onset,
            "location": f"SRID=4326;POINT({lng} {lat})",
            "location_label": props.get("areaDesc", "")[:200] or None,
            "source_type": "nws",
            "source_url": props.get("@id"),
            "relevance_score": {"critical": 95, "high": 80, "medium": 60, "low": 40}.get(severity, 50),
            "_lat": lat,
            "_lng": lng,
        })

    logger.info("Fetched %d weather alerts from NWS", len(events))
    return events


async def run_nws_scraper():
    """Fetch NWS alerts and insert into Supabase."""
    db = get_supabase()

    try:
        events = await fetch_nws_alerts()
    except httpx.HTTPError as e:
        logger.error("NWS API error: %s", e)
        return
    except Exception as e:
        logger.error("NWS scraper failed: %s", e)
        return

    if not events:
        logger.info("No active NWS alerts")
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
        logger.info("No NWS alerts matched any monitored area")
        return

    inserted = 0
    for event in matched:
        try:
            db.table("events").insert(event).execute()
            inserted += 1
        except Exception as e:
            logger.warning("Failed to insert NWS alert: %s", type(e).__name__)

    logger.info("Inserted %d/%d NWS alerts", inserted, len(matched))
