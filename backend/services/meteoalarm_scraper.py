"""MeteoAlarm severe weather alert scraper.

Fetches CAP 1.2 weather alerts from MeteoAlarm Atom feeds for European
countries and inserts geolocated events into Supabase.

feedparser extracts CAP fields (cap_severity, cap_event, cap_areadesc, etc.)
directly from the Atom entries. Since the feed does not include polygon
geometry, we match alerts to our monitored areas by checking if the area
description contains any of our city names, then use the area center as
the event's coordinates.

Feed URL pattern:
  https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-{country}
"""

import logging
from datetime import datetime, timezone

import feedparser
import httpx
from supabase import Client

from db import get_supabase
from services.insert_events import insert_events_batch

logger = logging.getLogger(__name__)

# Country slug → MeteoAlarm feed slug
COUNTRIES = {
    "germany": ["de"],
    "france": ["fr"],
    "bulgaria": ["bg"],
    "united-kingdom": ["gb"],
}

FEED_URL_TEMPLATE = "https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-{country}"

# Map CAP severity to our severity levels
CAP_SEVERITY_MAP: dict[str, str] = {
    "Extreme": "critical",
    "Severe": "high",
    "Moderate": "medium",
    "Minor": "low",
}

# Map country feed slugs to DB city patterns
COUNTRY_CITY_MAP = {
    "germany": {"berlin", "munich", "hamburg", "frankfurt", "cologne", "stuttgart",
                 "düsseldorf", "dortmund", "essen", "leipzig", "dresden", "nuremberg"},
    "france": {"paris", "marseille", "lyon", "toulouse", "bordeaux", "nice",
               "nantes", "strasbourg", "montpellier", "lille", "rennes", "grenoble"},
    "bulgaria": {"sofia", "plovdiv", "varna", "burgas", "ruse", "stara zagora",
                 "pleven", "sliven", "dobrich", "shumen", "blagoevgrad", "haskovo",
                 "veliko tarnovo", "gabrovo", "lovech", "smolyan", "razgrad",
                 "targovishte", "silistra", "yambol", "pernik", "kyustendil",
                 "montana", "vidin", "vratsa", "kardzhali", "pazardzhik",
                 "kazanlak", "karlovo", "troyan", "dupnitsa", "petrich",
                 "sandanski", "botevgrad", "berkovitsa", "lom", "sevlievo",
                 "gorna oryahovitsa", "dimitrovgrad", "panagyurishte",
                 "pomorie", "nessebar", "sozopol", "kavarna", "bansko"},
    "united-kingdom": {"london", "manchester", "edinburgh", "birmingham", "bristol",
                       "leeds", "liverpool", "glasgow", "cardiff", "nottingham",
                       "sheffield", "newcastle", "leicester"},
}


async def _load_area_centers(db: Client) -> dict[str, list[dict]]:
    """Load all active areas grouped by lowercase city name."""
    result = db.table("areas").select("id, name, city").eq("is_active", True).execute()
    by_city: dict[str, list[dict]] = {}
    for area in (result.data or []):
        city = area["city"].lower()
        by_city.setdefault(city, []).append(area)
    return by_city


def _match_area_to_alert(areadesc: str, country: str, areas_by_city: dict[str, list[dict]]) -> dict | None:
    """Try to match a MeteoAlarm area description to one of our monitored areas."""
    areadesc_lower = areadesc.lower()
    cities = COUNTRY_CITY_MAP.get(country, set())

    for city in cities:
        if city in areadesc_lower:
            areas = areas_by_city.get(city)
            if areas:
                return areas[0]  # Return first area in that city
    return None


async def fetch_and_insert_meteoalarm(country: str, db: Client, areas_by_city: dict[str, list[dict]]) -> int:
    """Fetch MeteoAlarm alerts for a country, match to areas, and insert."""
    feed_url = FEED_URL_TEMPLATE.format(country=country)

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(feed_url)
        resp.raise_for_status()

    feed = feedparser.parse(resp.text)
    events = []
    seen: set[str] = set()

    for entry in feed.entries:
        cap_severity = entry.get("cap_severity", "")
        cap_event = entry.get("cap_event", "Weather Alert")
        cap_areadesc = entry.get("cap_areadesc", "")
        cap_onset = entry.get("cap_onset", "")
        alert_id = entry.get("id", "")
        title = entry.get("title", f"{cap_event} - {cap_areadesc}")

        if not cap_areadesc:
            continue

        severity = CAP_SEVERITY_MAP.get(cap_severity, "low")

        # Deduplicate by event type + area within this fetch
        dedup_key = f"{cap_event}|{cap_areadesc}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Match to our monitored areas
        area = _match_area_to_alert(cap_areadesc, country, areas_by_city)
        if area is None:
            continue

        # Get area center coordinates
        try:
            center = db.rpc("area_center_coords", {"area_id": area["id"]}).execute()
        except Exception:
            continue
        if not center.data or len(center.data) == 0:
            continue

        lat = center.data[0].get("lat")
        lng = center.data[0].get("lng")
        if not lat or not lng:
            continue

        try:
            occurred_at = datetime.fromisoformat(cap_onset).isoformat() if cap_onset else datetime.now(timezone.utc).isoformat()
        except ValueError:
            occurred_at = datetime.now(timezone.utc).isoformat()

        events.append({
            "title": title[:255],
            "description": f"MeteoAlarm: {cap_event} in {cap_areadesc}. Severity: {cap_severity}.",
            "threat_type": "natural",
            "severity": severity,
            "occurred_at": occurred_at,
            "location": f"SRID=4326;POINT({lng} {lat})",
            "location_label": cap_areadesc,
            "source_type": "meteoalarm",
            "source_url": alert_id,
            "area_id": area["id"],
        })

    if not events:
        logger.info("No MeteoAlarm alerts matched monitored areas for %s", country)
        return 0

    logger.info("Matched %d MeteoAlarm alerts for %s", len(events), country)

    inserted = insert_events_batch(db, events, "MeteoAlarm")

    return inserted


async def run_meteoalarm_scraper():
    """Fetch MeteoAlarm alerts for all configured countries and insert into Supabase."""
    db: Client = get_supabase()

    # Load area centers once
    areas_by_city = await _load_area_centers(db)

    total_inserted = 0
    for country in COUNTRIES:
        try:
            inserted = await fetch_and_insert_meteoalarm(country, db, areas_by_city)
            total_inserted += inserted
        except httpx.HTTPStatusError as e:
            logger.error("MeteoAlarm returned HTTP %d for %s", e.response.status_code, country)
        except httpx.RequestError as e:
            logger.error("Network error fetching MeteoAlarm for %s: %s", country, e)
        except Exception:
            logger.exception("Unexpected error in MeteoAlarm scraper for %s", country)

    logger.info("MeteoAlarm scraper: inserted %d events total", total_inserted)
