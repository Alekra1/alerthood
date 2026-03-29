"""Fetch administrative boundaries from OpenStreetMap Overpass API."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
REQUEST_TIMEOUT = 60

# Admin levels vary by country. These are the most common mappings.
COUNTRY_ADMIN_LEVELS: dict[str, dict[str, str]] = {
    "GB": {"city": "8", "neighborhood": "10"},
    "DE": {"city": "6", "neighborhood": "9,10"},
    "FR": {"city": "8", "neighborhood": "9,10"},
    "BG": {"city": "6", "neighborhood": "9"},
}
DEFAULT_ADMIN_LEVELS = {"city": "8", "neighborhood": "9,10"}


def _admin_levels(country_code: str, level_type: str) -> list[str]:
    """Get admin levels for a country and type."""
    levels = COUNTRY_ADMIN_LEVELS.get(
        country_code.upper(), DEFAULT_ADMIN_LEVELS
    )
    return levels.get(level_type, DEFAULT_ADMIN_LEVELS[level_type]).split(",")


async def fetch_neighborhoods_in_bbox(
    min_lat: float, min_lng: float,
    max_lat: float, max_lng: float,
    country_code: str = "",
) -> list[dict[str, Any]]:
    """Fetch neighborhood boundaries within a bounding box from Overpass API.

    Returns a list of dicts with keys: osm_id, name, boundary_geojson.
    """
    levels = _admin_levels(country_code, "neighborhood")
    level_filters = "".join(
        f'relation["boundary"="administrative"]["admin_level"="{lv}"]({min_lat},{min_lng},{max_lat},{max_lng});'
        for lv in levels
    )

    query = f"""
    [out:json][timeout:{REQUEST_TIMEOUT}];
    (
      {level_filters}
    );
    out geom;
    """

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT + 10) as client:
        resp = await client.post(OVERPASS_URL, data={"data": query})
        resp.raise_for_status()

    data = resp.json()
    results = []

    for element in data.get("elements", []):
        if element.get("type") != "relation":
            continue

        name = element.get("tags", {}).get("name")
        osm_id = element.get("id")
        if not name or not osm_id:
            continue

        geojson = _relation_to_multipolygon(element)
        if not geojson:
            continue

        results.append({
            "osm_id": osm_id,
            "name": name,
            "boundary_geojson": geojson,
        })

    logger.info("Fetched %d neighborhoods from Overpass for bbox (%.2f,%.2f)-(%.2f,%.2f)",
                len(results), min_lat, min_lng, max_lat, max_lng)
    return results


async def fetch_city_boundary(
    city_name: str, country_code: str
) -> dict[str, Any] | None:
    """Fetch a single city boundary by name and country."""
    levels = _admin_levels(country_code, "city")
    level_filter = levels[0]

    query = f"""
    [out:json][timeout:{REQUEST_TIMEOUT}];
    relation["boundary"="administrative"]["admin_level"="{level_filter}"]["name"="{city_name}"];
    out geom;
    """

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT + 10) as client:
        resp = await client.post(OVERPASS_URL, data={"data": query})
        resp.raise_for_status()

    data = resp.json()
    for element in data.get("elements", []):
        if element.get("type") != "relation":
            continue

        name = element.get("tags", {}).get("name")
        osm_id = element.get("id")
        if not name or not osm_id:
            continue

        geojson = _relation_to_multipolygon(element)
        if not geojson:
            continue

        return {
            "osm_id": osm_id,
            "name": name,
            "boundary_geojson": geojson,
        }

    return None


def _relation_to_multipolygon(element: dict) -> dict | None:
    """Convert an Overpass relation with geometry to a GeoJSON MultiPolygon.

    Overpass `out geom` returns members with geometry arrays.
    We extract outer ways and assemble them into polygon rings.
    """
    outer_ways = []
    for member in element.get("members", []):
        if member.get("role") == "outer" and member.get("geometry"):
            coords = [
                [pt["lon"], pt["lat"]]
                for pt in member["geometry"]
            ]
            if len(coords) >= 4:
                outer_ways.append(coords)

    if not outer_ways:
        return None

    # Each outer way becomes a polygon in the MultiPolygon
    polygons = [
        [ring]  # Each polygon is [outer_ring, ...holes] — no holes for now
        for ring in outer_ways
    ]

    return {
        "type": "MultiPolygon",
        "coordinates": polygons,
    }
