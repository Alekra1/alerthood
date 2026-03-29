"""One-off script to replace synthetic circle areas with real OSM boundaries.

Run: python3 -m reingest_boundaries
"""

import asyncio
import logging

from db import get_supabase
from services.boundary_ingestion import ingest_all_cities, ingest_neighborhoods_for_city

OVERPASS_RATE_LIMIT_SECONDS = 5

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main():
    sb = get_supabase()

    # Step 1: Fetch boundaries for all existing cities
    logger.info("=== Step 1: Ingesting city boundaries from OSM ===")
    results = await ingest_all_cities()
    logger.info("City ingestion results: %s", results)
    if not results.get("updated"):
        logger.warning("No cities updated — aborting")
        return

    # Step 2: Ingest neighborhoods for each city
    cities = (
        sb.table("areas")
        .select("id, name, country_code")
        .eq("area_type", "city")
        .eq("is_active", True)
        .execute()
    )
    logger.info("=== Step 2: Ingesting neighborhood boundaries for %d cities ===", len(cities.data or []))
    total_neighborhoods = 0
    for city in (cities.data or []):
        cc = city.get("country_code", "")
        if not cc:
            logger.warning("No country_code for city %s — skipping neighborhoods", city["name"])
            continue
        count = await ingest_neighborhoods_for_city(city["id"], cc)
        total_neighborhoods += count
        logger.info("  %s: %d neighborhoods", city["name"], count)
        await asyncio.sleep(OVERPASS_RATE_LIMIT_SECONDS)

    # Step 3: Cleanup — nullify event references, delete old areas
    logger.info("=== Step 3: Cleaning up old synthetic areas ===")
    # Nullify area_id on events pointing to old areas
    events_result = (
        sb.table("events")
        .update({"area_id": None})
        .is_("area_id", "not.null")
        .execute()
    )
    logger.info("Unlinked %d events from old areas", len(events_result.data or []))

    # Delete old subscriptions
    subs_result = (
        sb.table("user_area_subscriptions")
        .delete()
        .neq("id", "00000000-0000-0000-0000-000000000000000")
        .execute()
    )
    logger.info("Deleted %d old subscriptions", len(subs_result.data or []))

    # Delete old synthetic areas (no osm_id = not from OSM)
    old_areas = (
        sb.table("areas")
        .delete()
        .is_("osm_id", "null")
        .execute()
    )
    logger.info("Deleted %d old synthetic areas", len(old_areas.data or []))
    # Final stats
    cities_count = sb.table("areas").select("id", count="exact").eq("area_type", "city").execute()
    nhoods_count = sb.table("areas").select("id", count="exact").eq("area_type", "neighborhood").execute()
    logger.info("=== Done! Cities: %d, Neighborhoods: %d ===", cities_count.count, nhoods_count.count)


if __name__ == "__main__":
    asyncio.run(main())
