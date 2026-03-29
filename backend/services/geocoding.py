import asyncio
import logging

from geopy.exc import GeopyError
from geopy.geocoders import Nominatim

from db import get_supabase

logger = logging.getLogger(__name__)

_nominatim = Nominatim(user_agent="alerthood/1.0")


async def detect_area_from_coords(lat: float, lng: float) -> dict | None:
    """Find the nearest area to given coordinates, or return None."""
    sb = get_supabase()

    result = sb.rpc(
        "find_nearest_area",
        {"user_point": f"SRID=4326;POINT({lng} {lat})"},
    ).execute()

    if result.data and len(result.data) > 0:
        return result.data[0]
    return None


async def geocode_location(location_text: str, city: str) -> tuple[float, float] | None:
    """Convert a Bulgarian location string to lat/lng using Nominatim.

    Appends city and country to bias the query. Returns None if not found.
    """
    query = f"{location_text}, {city}, Bulgaria"
    try:
        result = await asyncio.to_thread(
            _nominatim.geocode, query, country_codes="bg", timeout=10
        )
    except GeopyError as e:
        logger.warning("Nominatim error for %r: %s", query, e)
        return None
    if result is None:
        logger.debug("No geocoding result for %r", query)
        return None
    return result.latitude, result.longitude
