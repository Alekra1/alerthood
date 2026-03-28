import logging
from datetime import datetime, timezone, timedelta

import httpx

from config import get_settings
from db import get_supabase

logger = logging.getLogger(__name__)

ACLED_API_URL = "https://api.acleddata.com/acled/read"

ACLED_TO_THREAT_TYPE = {
    "Battles": "crime",
    "Violence against civilians": "crime",
    "Explosions/Remote violence": "crime",
    "Riots": "disturbance",
    "Protests": "disturbance",
    "Strategic developments": "infrastructure",
}

ACLED_SEVERITY_MAP = {
    0: "low",
    1: "medium",
    2: "medium",
    3: "high",
    4: "high",
    5: "critical",
}


async def import_acled_data(
    country: str = "United States",
    days_back: int = 90,
    limit: int = 500,
) -> int:
    """Bulk import historical events from ACLED API."""
    sb = get_supabase()
    settings = get_settings()

    # Skip if already imported
    existing = (
        sb.table("events")
        .select("id", count="exact")
        .eq("source_type", "acled")
        .execute()
    )
    if existing.count and existing.count > 0:
        logger.info(f"ACLED data already imported ({existing.count} events), skipping")
        return 0

    # Skip if no API credentials configured
    if not settings.acled_api_key or not settings.acled_api_email:
        logger.warning("ACLED API credentials not configured, skipping historical import")
        return 0

    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")

    params = {
        "key": settings.acled_api_key,
        "email": settings.acled_api_email,
        "country": country,
        "event_date": f"{since}|{now.strftime('%Y-%m-%d')}",
        "event_date_where": "BETWEEN",
        "limit": limit,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(ACLED_API_URL, params=params)
        if resp.status_code != 200:
            body = resp.text[:500]
            logger.error(f"ACLED API error {resp.status_code}: {body}")
            raise httpx.HTTPStatusError(
                f"ACLED API returned {resp.status_code}",
                request=resp.request,
                response=resp,
            )

        try:
            body = resp.json()
        except ValueError:
            logger.error(f"ACLED API returned non-JSON response: {resp.text[:200]}")
            raise

        if not body.get("success", True):
            msg = body.get("message", "unknown error")
            logger.error(f"ACLED API rejected request: {msg}")
            raise RuntimeError(f"ACLED API error: {msg}")

        data = body.get("data", [])

    imported = 0
    consecutive_failures = 0
    last_error = None

    for event in data:
        lat = event.get("latitude")
        lng = event.get("longitude")
        if not lat or not lng:
            continue

        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except (ValueError, TypeError):
            continue

        event_type = event.get("event_type", "")
        threat_type = ACLED_TO_THREAT_TYPE.get(event_type, "disturbance")

        try:
            fatalities = int(event.get("fatalities", 0))
        except (ValueError, TypeError):
            fatalities = 0

        severity = ACLED_SEVERITY_MAP.get(min(fatalities, 5), "medium")
        event_date = event.get("event_date", now.isoformat())

        title = event.get("event_type", "Incident")
        notes = event.get("notes", "")
        description = notes[:500] if notes else None

        # Find matching area
        area_id = None
        try:
            area_result = sb.rpc(
                "find_nearest_area",
                {"user_point": f"SRID=4326;POINT({lng_f} {lat_f})"},
            ).execute()
            if area_result.data and len(area_result.data) > 0:
                area_id = area_result.data[0].get("id")
        except Exception as e:
            logger.warning(f"Area detection failed for ({lat_f}, {lng_f}): {e}")

        row = {
            "title": title[:200],
            "description": description,
            "threat_type": threat_type,
            "severity": severity,
            "status": "active",
            "occurred_at": event_date,
            "location": f"SRID=4326;POINT({lng_f} {lat_f})",
            "location_label": event.get("location", None),
            "source_type": "acled",
            "source_url": None,
            "relevance_score": min(50 + fatalities * 10, 100),
            "area_id": area_id,
        }

        try:
            sb.table("events").insert(row).execute()
            imported += 1
            consecutive_failures = 0
        except Exception as e:
            consecutive_failures += 1
            last_error = e
            logger.warning(f"Failed to insert ACLED event: {type(e).__name__}")
            if consecutive_failures >= 10:
                logger.error(
                    f"Aborting ACLED import: {consecutive_failures} consecutive failures. "
                    f"Last error: {last_error}"
                )
                break

    if imported == 0 and len(data) > 0:
        logger.error(f"ACLED import: 0 of {len(data)} events imported. Last error: {last_error}")
    else:
        logger.info(f"Imported {imported} ACLED events")

    return imported
