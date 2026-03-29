"""GDELT-based event scraper.

Fetches the latest events from GDELT's public GKG (Global Knowledge Graph)
export files and inserts relevant geolocated events into Supabase.

GDELT updates every 15 minutes with a new CSV export at:
  https://data.gdeltproject.org/gdeltv2/lastupdate.txt
"""

import csv
import io
import logging
import urllib.parse
import zipfile
from datetime import datetime, timezone

import httpx
from supabase import Client

from db import get_supabase
from services.insert_events import insert_events_batch

logger = logging.getLogger(__name__)

GDELT_LAST_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"

# CAMEO event codes we care about → our threat_type mapping
# See: https://www.gdeltproject.org/data/lookups/CAMEO.eventcodes.txt
CAMEO_TO_THREAT: dict[str, str] = {
    # Crime / violence
    "18": "crime",       # Assault
    "180": "crime",
    "181": "crime",      # Abduct
    "182": "crime",      # Sexually assault
    "183": "crime",      # Torture
    "184": "crime",      # Kill
    "185": "crime",      # Injure
    "19": "crime",       # Fight
    "190": "crime",
    "193": "crime",      # Destroy property
    "194": "crime",      # Use unconventional violence
    "195": "crime",      # Armed attack
    "20": "crime",       # Unconventional mass violence
    # Protests / disturbance
    "14": "disturbance", # Protest
    "140": "disturbance",
    "141": "disturbance", # Demonstrate
    "142": "disturbance", # Hunger strike
    "143": "disturbance", # Strike
    "144": "disturbance", # Obstruct passage
    "145": "disturbance", # Protest violently / riot
    # Infrastructure / coerce
    "17": "infrastructure",  # Coerce (sanctions, embargoes)
    "175": "infrastructure", # Seize or damage property
}

# Minimum Goldstein scale magnitude to include (filters out low-impact events)
MIN_GOLDSTEIN_MAGNITUDE = -2.0

# GDELT CSV column indices
class _Col:
    GLOBAL_EVENT_ID = 0
    SQLDATE = 1
    EVENT_CODE = 26
    GOLDSTEIN_SCALE = 30
    ACTION_GEO_FULLNAME = 52
    ACTION_GEO_LAT = 56
    ACTION_GEO_LONG = 57
    SOURCE_URL = 60


def _goldstein_to_severity(score: float) -> str:
    """Map GDELT Goldstein scale (-10 to +10) to our severity levels."""
    if score <= -8:
        return "critical"
    if score <= -5:
        return "high"
    if score <= -2:
        return "medium"
    return "low"


def _validate_gdelt_url(url: str) -> None:
    """Validate that a URL points to the GDELT domain over HTTPS."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc.endswith("gdeltproject.org"):
        raise ValueError(f"Untrusted GDELT export URL: {url}")


async def fetch_latest_gdelt_events() -> list[dict]:
    """Fetch and parse the latest GDELT v2 event export."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(GDELT_LAST_UPDATE_URL)
        resp.raise_for_status()

        lines = resp.text.strip().split("\n")
        if not lines:
            logger.warning("GDELT lastupdate.txt was empty")
            return []

        export_url = lines[0].split()[-1]
        _validate_gdelt_url(export_url)

        zip_resp = await client.get(export_url)
        zip_resp.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
            csv_filename = zf.namelist()[0]
            csv_data = zf.read(csv_filename).decode("utf-8", errors="replace")

    events = []
    reader = csv.reader(io.StringIO(csv_data), delimiter="\t")

    for row in reader:
        if len(row) < 58:
            continue

        event_code = row[_Col.EVENT_CODE]
        threat_type = CAMEO_TO_THREAT.get(event_code)
        if not threat_type:
            continue

        try:
            lat = float(row[_Col.ACTION_GEO_LAT])
            lng = float(row[_Col.ACTION_GEO_LONG])
        except (ValueError, IndexError):
            continue

        if lat == 0.0 and lng == 0.0:
            continue

        try:
            goldstein = float(row[_Col.GOLDSTEIN_SCALE]) if row[_Col.GOLDSTEIN_SCALE] else 0.0
        except ValueError:
            continue

        if goldstein > MIN_GOLDSTEIN_MAGNITUDE:
            continue

        try:
            date_str = row[_Col.SQLDATE]
            occurred_at = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
        except (ValueError, IndexError):
            logger.debug("Skipping GDELT event with unparseable date: %s", row[_Col.GLOBAL_EVENT_ID])
            continue

        location_label = row[_Col.ACTION_GEO_FULLNAME] if len(row) > _Col.ACTION_GEO_FULLNAME else None
        source_url = row[_Col.SOURCE_URL] if len(row) > _Col.SOURCE_URL else None

        events.append({
            "title": f"{threat_type.title()}: {location_label or 'Unknown location'}",
            "description": f"Source: GDELT event {row[_Col.GLOBAL_EVENT_ID]}. Goldstein scale: {goldstein}",
            "threat_type": threat_type,
            "severity": _goldstein_to_severity(goldstein),
            "occurred_at": occurred_at.isoformat(),
            "location": f"SRID=4326;POINT({lng} {lat})",
            "location_label": location_label,
            "source_type": "news",
            "source_url": source_url,
            "_lat": lat,  # used by run_scraper for area matching, removed before insert
            "_lng": lng,
        })

    logger.info("Fetched %d relevant events from GDELT", len(events))
    return events


async def run_scraper():
    """Fetch latest GDELT events and insert into Supabase."""
    db: Client = get_supabase()

    try:
        events = await fetch_latest_gdelt_events()
    except httpx.HTTPStatusError as e:
        logger.error("GDELT returned HTTP %d: %s", e.response.status_code, e.request.url)
        return
    except httpx.RequestError as e:
        logger.error("Network error fetching GDELT data: %s", e)
        return
    except zipfile.BadZipFile:
        logger.error("GDELT export file was corrupted")
        return
    except ValueError as e:
        logger.error("GDELT URL validation failed: %s", e)
        return

    if not events:
        logger.info("No new events from GDELT")
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
        logger.info("No GDELT events matched any monitored area")
        return

    logger.info("Matched %d/%d events to areas", len(matched), len(events))

    inserted = insert_events_batch(db, matched, "GDELT")

    logger.info("Inserted %d/%d events into Supabase", inserted, len(matched))
