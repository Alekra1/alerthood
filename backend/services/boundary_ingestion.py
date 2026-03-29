"""Ingest neighborhood boundaries from OSM into the areas table."""

import json
import logging

from db import get_supabase
from services.overpass import fetch_city_boundary, fetch_neighborhoods_in_bbox

logger = logging.getLogger(__name__)


async def ingest_all_cities() -> dict:
    """Fetch boundaries for all cities in the DB and update them.

    Returns a summary dict with counts of updated/skipped cities.
    """
    sb = get_supabase()
    cities = (
        sb.table("areas")
        .select("id, name, country_code")
        .eq("area_type", "city")
        .eq("is_active", True)
        .execute()
    )

    updated = 0
    skipped = 0

    for city in (cities.data or []):
        cc = city.get("country_code", "")
        if not cc:
            logger.warning("City %s has no country_code — skipping", city["name"])
            skipped += 1
            continue

        boundary = await fetch_city_boundary(city["name"], cc)
        if not boundary:
            logger.warning("No boundary found for %s — skipping", city["name"])
            skipped += 1
            continue

        # Update city with osm_id and boundary geometry
        geojson_str = json.dumps(boundary["boundary_geojson"])
        (
            sb.table("areas")
            .update({
                "osm_id": boundary["osm_id"],
                "boundary": geojson_str,
            })
            .eq("id", city["id"])
            .execute()
        )
        updated += 1
        logger.info("Updated boundary for city %s (osm_id=%s)", city["name"], boundary["osm_id"])

    return {"updated": updated, "skipped": skipped, "total": len(cities.data or [])}


async def ingest_neighborhoods_for_city(city_id: str, country_code: str) -> int:
    """Fetch neighborhoods within a city's bounding box and upsert them.

    Returns the number of neighborhoods ingested.
    """
    sb = get_supabase()

    # Get the city's boundary bbox from the DB
    city_row = (
        sb.table("areas")
        .select("id, name, boundary")
        .eq("id", city_id)
        .single()
        .execute()
    )
    if not city_row.data or not city_row.data.get("boundary"):
        logger.warning("City %s has no boundary — cannot fetch neighborhoods", city_id)
        return 0

    # Use the bbox RPC to get the bounding box
    bbox_result = sb.rpc("area_bbox", {"area_id": city_id}).execute()
    if not bbox_result.data:
        logger.warning("No bbox for city %s", city_id)
        return 0

    bbox = bbox_result.data
    min_lat = bbox["min_lat"]
    min_lng = bbox["min_lng"]
    max_lat = bbox["max_lat"]
    max_lng = bbox["max_lng"]

    neighborhoods = await fetch_neighborhoods_in_bbox(
        min_lat, min_lng, max_lat, max_lng, country_code
    )

    if not neighborhoods:
        return 0

    city_name = city_row.data["name"]
    upserted = 0

    for nb in neighborhoods:
        slug = nb["name"].lower().replace(" ", "-").replace(",", "")
        geojson_str = json.dumps(nb["boundary_geojson"])

        try:
            (
                sb.table("areas")
                .upsert(
                    {
                        "osm_id": nb["osm_id"],
                        "name": nb["name"],
                        "slug": slug,
                        "area_type": "neighborhood",
                        "parent_id": city_id,
                        "country_code": country_code,
                        "city": city_name,
                        "boundary": geojson_str,
                        "is_active": True,
                    },
                    on_conflict="osm_id",
                )
                .execute()
            )
            upserted += 1
        except Exception:
            logger.exception("Failed to upsert neighborhood %s", nb["name"])

    logger.info("Ingested %d/%d neighborhoods for city %s", upserted, len(neighborhoods), city_name)
    return upserted
