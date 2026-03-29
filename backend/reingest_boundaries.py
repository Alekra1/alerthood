"""
One-off script: replace all existing areas with proper OSM boundaries.

Strategy:
  1. Load all active areas from DB, grouped by (city, country_code).
  2. Use Nominatim to look up each city's bounding box (reliable, purpose-built).
  3. Fetch all OSM neighborhoods within that bbox via Overpass.
  4. Match OSM results to existing DB areas by name (case-insensitive).
  5. UPDATE existing rows in-place (preserves FK links: events, subscriptions).
     New OSM areas with no DB match are inserted fresh.

Run from the backend/ directory:
    uv run python3 reingest_boundaries.py
"""

import asyncio
import logging
import sys
from collections import defaultdict
from unicodedata import normalize

import httpx

from db import get_supabase
from services.overpass import fetch_neighborhoods_in_bbox

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

RATE_LIMIT_SECONDS = 2       # between Nominatim calls (1 req/s policy)
OVERPASS_RATE_LIMIT = 6      # between Overpass calls
RETRY_AFTER_429 = 30
MAX_RETRIES = 3

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "alerthood-boundary-ingestion/1.0"}


def _normalise(name: str) -> str:
    n = normalize("NFKD", name).encode("ascii", "ignore").decode()
    return " ".join(n.lower().split())


def _geojson_to_ewkt(geojson: dict) -> str:
    coords = geojson["coordinates"]
    polygons = []
    for polygon in coords:
        rings = []
        for ring in polygon:
            points = ", ".join(f"{lng} {lat}" for lng, lat in ring)
            rings.append(f"({points})")
        polygons.append(f"({', '.join(rings)})")
    return f"SRID=4326;MULTIPOLYGON({', '.join(polygons)})"


async def nominatim_city_bbox(
    city_name: str, country_code: str
) -> tuple[float, float, float, float] | None:
    """
    Use Nominatim to get a city's bounding box.
    Returns (min_lat, min_lng, max_lat, max_lng) or None.
    """
    params = {
        "city": city_name,
        "country": country_code,
        "format": "json",
        "limit": 1,
        "featuretype": "city",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(NOMINATIM_URL, params=params, headers=NOMINATIM_HEADERS)
        resp.raise_for_status()

    results = resp.json()
    if not results:
        # fallback: try without featuretype constraint
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                NOMINATIM_URL,
                params={**params, "featuretype": "settlement"},
                headers=NOMINATIM_HEADERS,
            )
            resp.raise_for_status()
        results = resp.json()

    if not results:
        return None

    bb = results[0].get("boundingbox")  # [min_lat, max_lat, min_lng, max_lng]
    if not bb or len(bb) < 4:
        return None

    min_lat, max_lat, min_lng, max_lng = float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])
    # Add padding
    pad = 0.05
    return min_lat - pad, min_lng - pad, max_lat + pad, max_lng + pad


async def fetch_osm_with_retry(
    min_lat: float, min_lng: float, max_lat: float, max_lng: float, cc: str
) -> list[dict]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await fetch_neighborhoods_in_bbox(min_lat, min_lng, max_lat, max_lng, cc)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < MAX_RETRIES:
                logger.warning("  Overpass 429 — waiting %ds (attempt %d/%d)",
                               RETRY_AFTER_429, attempt, MAX_RETRIES)
                await asyncio.sleep(RETRY_AFTER_429)
            else:
                raise
    return []


async def reingest_city(
    city_name: str,
    country_code: str,
    existing_areas: list[dict],
) -> tuple[int, int]:
    sb = get_supabase()
    cc = country_code.upper()
    logger.info("── %s (%s)  [%d existing areas]", city_name, cc, len(existing_areas))

    await asyncio.sleep(RATE_LIMIT_SECONDS)
    bbox = await nominatim_city_bbox(city_name, cc)
    if not bbox:
        logger.warning("  Nominatim: no bbox found — skipping")
        return 0, 0

    min_lat, min_lng, max_lat, max_lng = bbox
    logger.info("  bbox: (%.2f,%.2f)→(%.2f,%.2f)", min_lat, min_lng, max_lat, max_lng)

    await asyncio.sleep(OVERPASS_RATE_LIMIT)
    osm_neighborhoods = await fetch_osm_with_retry(min_lat, min_lng, max_lat, max_lng, cc)
    logger.info("  Got %d OSM neighborhoods", len(osm_neighborhoods))

    if not osm_neighborhoods:
        return 0, 0

    existing_by_name = {_normalise(a["name"]): a for a in existing_areas}
    updated = 0
    inserted = 0

    for nb in osm_neighborhoods:
        ewkt = _geojson_to_ewkt(nb["boundary_geojson"])
        key = _normalise(nb["name"])

        if key in existing_by_name:
            area = existing_by_name[key]
            try:
                sb.table("areas").update({
                    "boundary": ewkt,
                    "osm_id": nb["osm_id"],
                }).eq("id", area["id"]).execute()
                logger.info("  ✓ updated  %s", nb["name"])
                updated += 1
            except Exception as e:
                logger.error("  ✗ update failed for %s: %s", nb["name"], e)
        else:
            slug = f"{cc.lower()}-{nb['name'].lower().replace(' ', '-')}-{nb['osm_id']}"
            row = {
                "name": nb["name"],
                "city": city_name,
                "slug": slug,
                "osm_id": nb["osm_id"],
                "area_type": "neighborhood",
                "country_code": cc,
                "boundary": ewkt,
                "is_active": True,
            }
            try:
                sb.table("areas").insert(row).execute()
                logger.info("  + inserted %s", nb["name"])
                inserted += 1
            except Exception as e:
                logger.debug("  ~ skip %s: %s", nb["name"], e)

    return updated, inserted


async def main() -> None:
    sb = get_supabase()

    result = (
        sb.table("areas")
        .select("id, name, city, country_code, area_type")
        .eq("is_active", True)
        .execute()
    )
    all_areas = result.data or []
    logger.info("Loaded %d active areas from DB", len(all_areas))

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for area in all_areas:
        city = (area.get("city") or "").strip()
        cc = (area.get("country_code") or "").strip()
        if city and cc:
            groups[(city, cc)].append(area)

    logger.info("Found %d city groups to process", len(groups))

    total_updated = 0
    total_inserted = 0

    for (city, cc), areas in groups.items():
        try:
            updated, inserted = await reingest_city(city, cc, areas)
            total_updated += updated
            total_inserted += inserted
        except Exception as e:
            logger.error("  !! city %s (%s) failed: %s", city, cc, e)

        await asyncio.sleep(OVERPASS_RATE_LIMIT)

    logger.info(
        "Done. %d areas updated with OSM boundaries, %d new areas inserted.",
        total_updated, total_inserted,
    )


if __name__ == "__main__":
    asyncio.run(main())
