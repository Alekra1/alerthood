"""One-off script to replace synthetic circle areas with real OSM boundaries.

Run: python3 -m reingest_boundaries
"""

import asyncio
import logging

from db import get_supabase
from services.boundary_ingestion import (
    ingest_cities_from_existing,
    ingest_neighborhoods_for_city,
    OVERPASS_RATE_LIMIT_SECONDS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main():
    sb = get_supabase()

    # Step 1: Create proper city entries from existing area names
    logger.info("=== Step 1: Ingesting city boundaries from OSM ===")
    city_ids = await ingest_cities_from_existing()

    if not city_ids:
        logger.warning("No cities ingested — aborting")
        return

    # Step 2: Ingest neighborhoods for each city
    logger.info("=== Step 2: Ingesting neighborhood boundaries for %d cities ===", len(city_ids))
    total_neighborhoods = 0
    for city_name, city_id in city_ids.items():
        # Determine country code from the city entry
        city_row = (
            sb.table("areas")
            .select("country_code")
            .eq("id", city_id)
            .single()
            .execute()
        )
        cc = city_row.data["country_code"]
        if not cc:
            logger.warning("No country_code for city %s — skipping neighborhoods", city_name)
            continue

        count = await ingest_neighborhoods_for_city(city_id, cc)
        total_neighborhoods += count
        logger.info("  %s: %d neighborhoods", city_name, count)
        await asyncio.sleep(OVERPASS_RATE_LIMIT_SECONDS)

    logger.info("Ingested %d total neighborhoods", total_neighborhoods)

    # Step 3: Cleanup — nullify event references to old areas, then delete old areas
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
        .neq("id", "00000000-0000-0000-0000-000000000000")
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
