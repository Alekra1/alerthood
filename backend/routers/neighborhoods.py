"""Neighborhood boundaries API — returns GeoJSON for map rendering."""

import json
import logging

from fastapi import APIRouter, Query

from db import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["neighborhoods"])


@router.get("/neighborhoods")
async def get_neighborhoods(
    min_lat: float = Query(ge=-90, le=90),
    min_lng: float = Query(ge=-180, le=180),
    max_lat: float = Query(ge=-90, le=90),
    max_lng: float = Query(ge=-180, le=180),
    zoom: int = Query(ge=1, le=20, default=14),
):
    """Return GeoJSON FeatureCollection of neighborhoods in viewport."""
    sb = get_supabase()

    # Show cities at low zoom, neighborhoods at high zoom
    area_type = "city" if zoom < 10 else "neighborhood"

    result = sb.rpc("neighborhoods_in_bbox", {
        "min_lat": min_lat,
        "min_lng": min_lng,
        "max_lat": max_lat,
        "max_lng": max_lng,
        "zoom_level": zoom,
        "target_area_type": area_type,
    }).execute()

    features = []
    for row in (result.data or []):
        if not row.get("geojson"):
            continue
        features.append({
            "type": "Feature",
            "geometry": json.loads(row["geojson"]),
            "properties": {
                "id": row["id"],
                "name": row["name"],
                "slug": row["slug"],
                "area_type": row["area_type"],
                "safety_score": float(row["safety_score"]) if row["safety_score"] else 0,
                "safety_color": row["safety_color"] or "#22c55e",
                "event_count_90d": row["event_count_90d"] or 0,
                "parent_name": row["parent_name"],
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }
