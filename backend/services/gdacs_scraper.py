"""GDACS multi-hazard scraper.

Fetches flood, wildfire, earthquake, and volcano alerts from the
Global Disaster Alert and Coordination System (GDACS) REST API.
Free, no auth required.
https://www.gdacs.org/gdacsapi/
"""

import logging
from datetime import datetime, timezone, timedelta

import httpx

from db import get_supabase
from services.insert_events import insert_events_batch

logger = logging.getLogger(__name__)

GDACS_API_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"

# European bounding box
LAT_MIN, LAT_MAX = 35, 72
LNG_MIN, LNG_MAX = -25, 45

# Alert level → severity
ALERT_TO_SEVERITY: dict[str, str] = {
    "Red": "critical",
    "Orange": "high",
    "Green": "medium",
}

# Alert level → relevance score
ALERT_TO_RELEVANCE: dict[str, int] = {
    "Red": 95,
    "Orange": 80,
    "Green": 60,
}

# Event type code → display name
EVENT_TYPE_NAMES: dict[str, str] = {
    "EQ": "Earthquake",
    "FL": "Flood",
    "TC": "Tropical Cyclone",
    "VO": "Volcanic Eruption",
    "WF": "Wildfire",
    "DR": "Drought",
}


async def run_gdacs_scraper():
    """Fetch recent GDACS disaster alerts and upsert into Supabase."""
    db = get_supabase()

    now = datetime.now(timezone.utc)
    from_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    to_date = now.strftime("%Y-%m-%d")

    params = {
        "eventlist": "EQ;FL;VO;WF",
        "fromdate": from_date,
        "todate": to_date,
        "alertlevel": "Green;Orange;Red",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                GDACS_API_URL,
                params=params,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("GDACS API returned HTTP %d", e.response.status_code)
            return
        except httpx.RequestError as e:
            logger.error("Network error fetching GDACS data: %s", e)
            return

    try:
        data = resp.json()
    except Exception:
        logger.exception("Failed to parse GDACS response as JSON")
        return

    features = data.get("features", [])
    if not features:
        logger.info("No features returned from GDACS")
        return

    events: list[dict] = []

    for feature in features:
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates", [])

        if not coords or len(coords) < 2:
            continue

        lng, lat = float(coords[0]), float(coords[1])

        # Filter to European bounding box
        if not (LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX):
            continue

        event_type = props.get("eventtype", "")
        alert_level = props.get("alertlevel", "Green")
        name = props.get("name") or props.get("eventname") or "Unknown"
        country = props.get("country", "")
        description = props.get("description", "")
        event_id = props.get("eventid", "")
        from_date_str = props.get("fromdate", "")

        type_name = EVENT_TYPE_NAMES.get(event_type, event_type)
        severity = ALERT_TO_SEVERITY.get(alert_level, "medium")
        relevance = ALERT_TO_RELEVANCE.get(alert_level, 60)

        # Parse occurred_at
        try:
            occurred_at = datetime.fromisoformat(from_date_str).isoformat()
        except (ValueError, TypeError):
            occurred_at = now.isoformat()

        title = f"{type_name}: {name}"[:255]
        source_url = f"https://www.gdacs.org/report.aspx?eventid={event_id}&eventtype={event_type}"

        location_label = country if country else name

        events.append({
            "title": title,
            "description": description[:2000] if description else f"GDACS {type_name} alert ({alert_level})",
            "threat_type": "natural",
            "severity": severity,
            "occurred_at": occurred_at,
            "location": f"SRID=4326;POINT({lng} {lat})",
            "location_label": location_label,
            "source_type": "gdacs",
            "source_url": source_url,
            "relevance_score": relevance,
            "_lat": lat,
            "_lng": lng,
        })

    if not events:
        logger.info("No GDACS events in European bounding box")
        return

    logger.info("Parsed %d GDACS events in Europe", len(events))

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
        logger.info("No GDACS events matched any monitored area")
        return

    logger.info("Matched %d/%d GDACS events to areas", len(matched), len(events))

    inserted = insert_events_batch(db, matched, "GDACS")

    logger.info("GDACS scraper: inserted %d/%d events", inserted, len(matched))
