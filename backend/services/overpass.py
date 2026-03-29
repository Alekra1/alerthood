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
    We extract outer ways, chain them into closed rings, and
    assemble them into a proper MultiPolygon.
    """
    outer_ways: list[list[list[float]]] = []
    for member in element.get("members", []):
        if member.get("role") == "outer" and member.get("geometry"):
            coords = [
                [pt["lon"], pt["lat"]]
                for pt in member["geometry"]
            ]
            if len(coords) >= 2:
                outer_ways.append(coords)

    if not outer_ways:
        return None

    rings = _chain_ways_into_rings(outer_ways)

    if not rings:
        return None

    polygons = [[ring] for ring in rings]

    return {
        "type": "MultiPolygon",
        "coordinates": polygons,
    }


def _chain_ways_into_rings(ways: list[list[list[float]]]) -> list[list[list[float]]]:
    """Stitch OSM ways into closed rings by matching endpoints.

    OSM splits administrative boundaries into multiple ways.
    Each way's end should connect to another way's start/end.
    We greedily chain them until we form a closed ring, then
    start the next ring with remaining ways.
    """
    EPSILON = 1e-9
    remaining = list(ways)
    rings: list[list[list[float]]] = []

    while remaining:
        # Start a new ring with the first remaining way
        current_ring = list(remaining.pop(0))
        changed = True

        while changed:
            changed = False
            i = 0
            while i < len(remaining):
                way = remaining[i]
                way_start = way[0]
                way_end = way[-1]
                ring_start = current_ring[0]
                ring_end = current_ring[-1]

                # Try to append: does this way's start match our ring's end?
                if _pts_equal(ring_end, way_start, EPSILON):
                    current_ring.extend(way[1:])
                    remaining.pop(i)
                    changed = True
                    continue

                # Try to append reversed: does this way's end match our ring's end?
                if _pts_equal(ring_end, way_end, EPSILON):
                    current_ring.extend(reversed(way[:-1]))
                    remaining.pop(i)
                    changed = True
                    continue

                # Try to prepend: does this way's end match our ring's start?
                if _pts_equal(ring_start, way_end, EPSILON):
                    current_ring = way[:-1] + current_ring
                    remaining.pop(i)
                    changed = True
                    continue

                # Try to prepend reversed: does this way's start match our ring's start?
                if _pts_equal(ring_start, way_start, EPSILON):
                    current_ring = list(reversed(way[1:])) + current_ring
                    remaining.pop(i)
                    changed = True
                    continue

                i += 1

        # Only accept closed rings (first point == last point)
        if len(current_ring) >= 4 and _pts_equal(current_ring[0], current_ring[-1], EPSILON):
            rings.append(current_ring)

    return rings


def _pts_equal(a: list[float], b: list[float], eps: float) -> bool:
    """Check if two coordinate points are approximately equal."""
    return abs(a[0] - b[0]) < eps and abs(a[1] - b[1]) < eps
