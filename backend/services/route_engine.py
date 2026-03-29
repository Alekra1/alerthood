import logging
import math

from fastapi import HTTPException

from db import get_supabase
from models.schemas import RouteRequest, RouteWaypoint, SafeRouteResponse

logger = logging.getLogger(__name__)


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in km between two points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def _build_google_maps_url(waypoints: list[RouteWaypoint], avoided: int) -> str:
    """Build a Google Maps directions URL with waypoints."""
    if len(waypoints) < 2:
        return ""
    origin = f"{waypoints[0].lat},{waypoints[0].lng}"
    destination = f"{waypoints[-1].lat},{waypoints[-1].lng}"
    
    # If no threats avoided, just route directly
    if avoided == 0:
        return f"https://www.google.com/maps/dir/{origin}/{destination}/data=!4m2!4m1!3e2"

    url = f"https://www.google.com/maps/dir/{origin}"
    
    # Downsample intermediate waypoints to max 2 points to avoid forcing 10 mandatory stops
    mid_points = waypoints[1:-1]
    if len(mid_points) > 2:
        step = max(1, len(mid_points) // 3)
        mid_points = [mid_points[step], mid_points[step * 2]]
        
    for wp in mid_points:
        url += f"/{wp.lat},{wp.lng}"
        
    url += f"/{destination}/data=!4m2!4m1!3e2"
    return url


SEVERITY_DANGER_RADIUS_KM = {
    "low": 0.1,
    "medium": 0.3,
    "high": 0.5,
    "critical": 0.8,
}


async def calculate_safe_route(req: RouteRequest) -> SafeRouteResponse:
    sb = get_supabase()

    # Bounding box with padding
    min_lat = min(req.origin_lat, req.dest_lat) - 0.02
    max_lat = max(req.origin_lat, req.dest_lat) + 0.02
    min_lng = min(req.origin_lng, req.dest_lng) - 0.02
    max_lng = max(req.origin_lng, req.dest_lng) + 0.02

    # Cap bounding box size to prevent continent-sized scans
    if (max_lat - min_lat) > 1.0 or (max_lng - min_lng) > 1.0:
        raise HTTPException(
            status_code=400,
            detail="Route distance too large for safe-route calculation",
        )

    # Fetch active events in bounding box
    try:
        result = sb.rpc(
            "events_in_bbox",
            {
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_lng": min_lng,
                "max_lng": max_lng,
            },
        ).execute()
    except Exception as e:
        logger.error(f"Failed to fetch events for safe route: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Unable to check for safety events along this route. Please try again later.",
        )

    if result.data is None:
        logger.error("events_in_bbox RPC returned None — possible DB function error")
        raise HTTPException(
            status_code=503,
            detail="Safety data is temporarily unavailable. Please try again later.",
        )

    events = result.data

    # Generate waypoints along direct path
    num_points = 10
    waypoints: list[RouteWaypoint] = []
    avoided = 0

    for i in range(num_points + 1):
        t = i / num_points
        lat = req.origin_lat + t * (req.dest_lat - req.origin_lat)
        lng = req.origin_lng + t * (req.dest_lng - req.origin_lng)

        # Check proximity to dangerous events
        for ev in events:
            ev_lat = ev.get("lat", 0)
            ev_lng = ev.get("lng", 0)
            severity = ev.get("severity", "medium")
            danger_radius = SEVERITY_DANGER_RADIUS_KM.get(severity, 0.3)

            dist = _haversine(lat, lng, ev_lat, ev_lng)
            if dist < danger_radius:
                # Shift perpendicular to route direction
                # Route direction vector: (dx, dy); perpendicular: (-dy, dx)
                dx = req.dest_lng - req.origin_lng
                dy = req.dest_lat - req.origin_lat
                length = math.sqrt(dx * dx + dy * dy) or 1
                offset = 0.005  # ~500m
                lat += -dy / length * offset
                lng += dx / length * offset
                avoided += 1
                break

        waypoints.append(RouteWaypoint(lat=round(lat, 6), lng=round(lng, 6)))

    total_distance = sum(
        _haversine(
            waypoints[i].lat, waypoints[i].lng,
            waypoints[i + 1].lat, waypoints[i + 1].lng,
        )
        for i in range(len(waypoints) - 1)
    )

    return SafeRouteResponse(
        waypoints=waypoints,
        google_maps_url=_build_google_maps_url(waypoints, avoided),
        avoided_events=avoided,
        distance_km=round(total_distance, 2),
    )
