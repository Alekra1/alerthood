"""Ingest neighborhood boundaries from OSM into the areas table."""

import asyncio
import logging

from db import get_supabase
from services.overpass import fetch_city_boundary, fetch_neighborhoods_in_bbox

logger = logging.getLogger(__name__)

OVERPASS_RATE_LIMIT_SECONDS = 5


def _geojson_to_ewkt(geojson: dict) -> str:
    """Convert GeoJSON MultiPolygon to EWKT for PostGIS insertion."""
    coords = geojson["coordinates"]
    polygons = []
    for polygon in coords:
        rings = []
        for ring in polygon:
            points = ", ".join(f"{lng} {lat}" for lng, lat in ring)
            rings.append(f"({points})")
        polygons.append(f"({', '.join(rings)})")
    return f"SRID=4326;MULTIPOLYGON({', '.join(polygons)})"


async def ingest_city(city_name: str, country_code: str, slug_prefix: str) -> str | None:
    """Fetch and upsert a city boundary. Returns the area ID or None."""
    sb = get_supabase()

    city_data = await fetch_city_boundary(city_name, country_code)
    if not city_data:
        logger.warning("No city boundary found for %s (%s)", city_name, country_code)
        return None

    slug = f"{slug_prefix}-{city_name.lower().replace(' ', '-')}"
    ewkt = _geojson_to_ewkt(city_data["boundary_geojson"])

    row = {
        "name": city_data["name"],
        "slug": slug,
        "osm_id": city_data["osm_id"],
        "area_type": "city",
        "country_code": country_code.upper(),
        "boundary": ewkt,
        "is_active": True,
    }

    result = (
        sb.table("areas")
        .upsert(row, on_conflict="osm_id")
        .execute()
    )

    if result.data:
        city_id = result.data[0]["id"]
        logger.info("Upserted city: %s (id=%s)", city_name, city_id)
        return city_id

    return None


async def ingest_neighborhoods_for_city(city_id: str, country_code: str) -> int:
    """Fetch and upsert all neighborhoods within a city's boundary. Returns count."""
    sb = get_supabase()

    # Get city boundary bbox
    bbox_result = sb.rpc("area_bbox", {"target_area_id": city_id}).execute()
    if not bbox_result.data or not bbox_result.data[0]:
        logger.warning("Could not compute bbox for city %s", city_id)
        return 0

    bbox = bbox_result.data[0]
    min_lat, min_lng = bbox["min_lat"], bbox["min_lng"]
    max_lat, max_lng = bbox["max_lat"], bbox["max_lng"]

    await asyncio.sleep(OVERPASS_RATE_LIMIT_SECONDS)

    neighborhoods = await fetch_neighborhoods_in_bbox(
        min_lat, min_lng, max_lat, max_lng, country_code
    )

    count = 0
    for nb in neighborhoods:
        slug = f"{country_code.lower()}-{nb['name'].lower().replace(' ', '-')}-{nb['osm_id']}"
        ewkt = _geojson_to_ewkt(nb["boundary_geojson"])

        row = {
            "name": nb["name"],
            "slug": slug,
            "osm_id": nb["osm_id"],
            "area_type": "neighborhood",
            "parent_id": city_id,
            "country_code": country_code.upper(),
            "boundary": ewkt,
            "is_active": True,
        }

        try:
            sb.table("areas").upsert(row, on_conflict="osm_id").execute()
            count += 1
        except Exception as e:
            logger.error("Failed to upsert neighborhood %s: %s", nb["name"], e)

    logger.info("Ingested %d neighborhoods for city %s", count, city_id)
    return count


async def ingest_cities_from_existing() -> dict[str, str]:
    """Extract unique (city_name, country_code) from existing seed areas and
    create proper city-level entries with real OSM boundaries.

    Returns {city_name: city_id} for successful ingests.
    """
    sb = get_supabase()

    areas = (
        sb.table("areas")
        .select("name, country_code")
        .eq("is_active", True)
        .execute()
    )

    # Extract unique city names from "City - Neighborhood" format
    city_map: dict[str, str] = {}  # city_name → country_code
    for area in (areas.data or []):
        parts = area["name"].split(" - ")
        city_name = parts[0].strip() if len(parts) > 1 else area["name"].strip()
        cc = (area.get("country_code") or "").strip()
        if city_name and cc:
            city_map[city_name] = cc

    logger.info("Found %d unique cities from existing areas", len(city_map))

    results: dict[str, str] = {}
    for city_name, cc in sorted(city_map.items()):
        logger.info("Ingesting city: %s (%s)", city_name, cc)
        city_id = await ingest_city(city_name, cc, slug_prefix=cc.lower())
        if city_id:
            results[city_name] = city_id
        await asyncio.sleep(OVERPASS_RATE_LIMIT_SECONDS)

    logger.info("Successfully ingested %d / %d cities", len(results), len(city_map))
    return results


async def ingest_all_cities() -> dict[str, int]:
    """Ingest boundaries for all active city-level areas. Returns {city_name: neighborhood_count}."""
    sb = get_supabase()

    cities = (
        sb.table("areas")
        .select("id, name, country_code")
        .eq("area_type", "city")
        .eq("is_active", True)
        .execute()
    )

    results = {}
    for city in (cities.data or []):
        cc = city.get("country_code", "")
        if not cc:
            continue

        count = await ingest_neighborhoods_for_city(city["id"], cc)
        results[city["name"]] = count
        await asyncio.sleep(OVERPASS_RATE_LIMIT_SECONDS)

    return results
