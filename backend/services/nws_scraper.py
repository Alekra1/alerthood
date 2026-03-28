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

        lat, lng = None, None

        if geometry and geometry.get("type") == "Point":
            coords = geometry.get("coordinates", [])
            if len(coords) >= 2:
                lng, lat = coords[0], coords[1]
        elif geometry and geometry.get("type") == "Polygon":
            try:
                coords = geometry["coordinates"][0]
                if not coords:
                    continue
                lat = sum(c[1] for c in coords) / len(coords)
                lng = sum(c[0] for c in coords) / len(coords)
            except (IndexError, TypeError, ZeroDivisionError):
                continue

        if lat is None or lng is None:
            continue

        event_type = props.get("event", "")
        threat_type = EVENT_TO_THREAT.get(event_type, "natural")
        severity = SEVERITY_MAP.get(props.get("severity", "Unknown"), "low")

        onset = props.get("onset") or props.get("sent") or datetime.now(timezone.utc).isoformat()
        headline = props.get("headline", event_type)
        description = (props.get("description", "") or "")[:500]
        alert_id = props.get("id", "")

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
            "_alert_id": alert_id,
        })

    logger.info("Fetched %d weather alerts from NWS", len(events))
    return events


async def run_nws_scraper():
    """Fetch NWS alerts and insert into Supabase."""
    db = get_supabase()

    try:
        events = await fetch_nws_alerts()
    except httpx.HTTPStatusError as e:
        logger.error("NWS API returned HTTP %d: %s", e.response.status_code, e.request.url)
        return
    except httpx.RequestError as e:
        logger.error("Network error fetching NWS data: %s", e)
        return

    if not events:
        logger.info("No active NWS alerts")
        return

    matched = []
    for event in events:
        try:
            result = db.rpc("find_nearest_area", {"lat": event["_lat"], "lng": event["_lng"]}).execute()
        except Exception:
            logger.exception("Area matching failed for NWS alert")
            continue
        area_id = result.data
        if area_id:
            event["area_id"] = area_id
            del event["_lat"]
            del event["_lng"]
            event.pop("_alert_id")
            # Dedup by source_url
            if event.get("source_url"):
                existing = db.table("events").select("id", count="exact").eq("source_type", "nws").eq("source_url", event["source_url"]).execute()
                if existing.count and existing.count > 0:
                    continue
            matched.append(event)

    if not matched:
        logger.info("No NWS alerts matched any monitored area")
        return

    inserted = 0
    for i in range(0, len(matched), 50):
        chunk = matched[i : i + 50]
        try:
            db.table("events").insert(chunk).execute()
            inserted += len(chunk)
        except Exception:
            logger.exception("Failed to insert NWS alerts chunk %d-%d", i, i + len(chunk))

    logger.info("Inserted %d/%d NWS alerts", inserted, len(matched))
