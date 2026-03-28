"""GDELT-based event scraper.

Fetches the latest events from GDELT's public GKG (Global Knowledge Graph)
export files and inserts relevant geolocated events into Supabase.

GDELT updates every 15 minutes with a new CSV export at:
  http://data.gdeltproject.org/gdeltv2/lastupdate.txt
"""

import csv
import io
import logging
import zipfile
from datetime import datetime, timezone

import httpx
from supabase import Client

from db import get_supabase

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
MIN_GOLDSTEIN_MAGNITUDE = -5.0


def _goldstein_to_severity(score: float) -> str:
    """Map GDELT Goldstein scale (-10 to +10) to our severity levels.
    More negative = more severe conflict.
    """
    if score <= -8:
        return "critical"
    elif score <= -5:
        return "high"
    elif score <= -2:
        return "medium"
    return "low"


async def fetch_latest_gdelt_events() -> list[dict]:
    """Fetch and parse the latest GDELT v2 event export."""
    async with httpx.AsyncClient(timeout=30) as client:
        # Get the URL of the latest export file
        resp = await client.get(GDELT_LAST_UPDATE_URL)
        resp.raise_for_status()

        # First line has the export CSV zip URL
        # Format: "SIZE MD5 URL"
        lines = resp.text.strip().split("\n")
        export_line = lines[0]  # The events export (first line)
        export_url = export_line.split()[-1]

        # Download the zip
        zip_resp = await client.get(export_url)
        zip_resp.raise_for_status()

        # Extract CSV from zip
        with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
            csv_filename = zf.namelist()[0]
            csv_data = zf.read(csv_filename).decode("utf-8", errors="replace")

    # Parse CSV (GDELT v2 export is tab-delimited, no header)
    events = []
    reader = csv.reader(io.StringIO(csv_data), delimiter="\t")

    for row in reader:
        if len(row) < 58:
            continue

        event_code = row[26]  # EventCode (CAMEO)
        threat_type = CAMEO_TO_THREAT.get(event_code)
        if not threat_type:
            continue

        # Must have geolocation
        try:
            lat = float(row[53])  # ActionGeo_Lat
            lng = float(row[54])  # ActionGeo_Long
        except (ValueError, IndexError):
            continue

        # Skip events with 0,0 coordinates (missing geolocation)
        if lat == 0.0 and lng == 0.0:
            continue

        goldstein = float(row[30]) if row[30] else 0.0
        if goldstein > MIN_GOLDSTEIN_MAGNITUDE:
            continue

        # Parse date (YYYYMMDD format)
        try:
            date_str = row[1]  # SQLDATE
            occurred_at = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
        except (ValueError, IndexError):
            occurred_at = datetime.now(timezone.utc)

        location_label = row[52] if len(row) > 52 else None  # ActionGeo_FullName
        source_url = row[57] if len(row) > 57 else None       # SOURCEURL

        events.append({
            "title": f"{threat_type.title()}: {location_label or 'Unknown location'}",
            "description": f"Source: GDELT event {row[0]}. Goldstein scale: {goldstein}",
            "threat_type": threat_type,
            "severity": _goldstein_to_severity(goldstein),
            "occurred_at": occurred_at.isoformat(),
            "location": f"SRID=4326;POINT({lng} {lat})",
            "location_label": location_label,
            "source_type": "news",
            "source_url": source_url,
            "relevance_score": min(100, int(abs(goldstein) * 10)),
        })

    logger.info("Fetched %d relevant events from GDELT", len(events))
    return events


async def run_scraper():
    """Fetch latest GDELT events and insert into Supabase."""
    db: Client = get_supabase()

    try:
        events = await fetch_latest_gdelt_events()
        if not events:
            logger.info("No new events from GDELT")
            return

        # Batch insert (Supabase handles duplicates gracefully)
        # Insert in chunks of 50
        for i in range(0, len(events), 50):
            chunk = events[i : i + 50]
            db.table("events").insert(chunk).execute()

        logger.info("Inserted %d events into Supabase", len(events))

    except Exception:
        logger.exception("Scraper failed")
