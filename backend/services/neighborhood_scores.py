import logging
from datetime import datetime, timezone, timedelta

from db import get_supabase

logger = logging.getLogger(__name__)


async def compute_area_crime_stats(area_id: str) -> dict:
    """Count crimes in an area and compute crime rate per km²."""
    sb = get_supabase()

    since = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()

    result = (
        sb.table("events")
        .select("id", count="exact")
        .eq("area_id", area_id)
        .eq("threat_type", "crime")
        .gte("occurred_at", since)
        .execute()
    )

    crime_count = result.count or 0

    # Get area in km² from PostGIS boundary
    area_result = sb.rpc("area_size_km2", {"target_area_id": area_id}).execute()
    area_km2 = (area_result.data[0]["area_km2"] if area_result.data else 0) or 1.0

    crime_rate = crime_count / area_km2

    return {
        "crime_count": crime_count,
        "crime_rate_per_km2": round(crime_rate, 2),
    }


def compute_safety_score(
    crime_rate_per_km2: float,
    poverty_index: float,
    max_crime_rate: float = 10.0,
) -> float:
    """
    Composite safety score 0-100 (higher = safer).

    Formula: 100 - (crime_rate_pct * 0.7 + poverty_pct * 0.3)
    """
    crime_rate_pct = min(crime_rate_per_km2 / max_crime_rate, 1.0) * 100
    poverty_pct = min(poverty_index / 50.0, 1.0) * 100

    score = 100 - (crime_rate_pct * 0.7 + poverty_pct * 0.3)
    return round(max(0, min(100, score)), 2)


def _score_to_color(score: float) -> str:
    """Map safety score (0-100, higher=safer) to hex color."""
    danger = 100 - score  # invert: 0=safe, 100=dangerous
    if danger >= 81:
        return "#7f1d1d"
    if danger >= 61:
        return "#ef4444"
    if danger >= 41:
        return "#f97316"
    if danger >= 21:
        return "#eab308"
    return "#22c55e"


async def refresh_all_scores() -> int:
    """Recompute safety scores for all active areas. Returns count updated."""
    sb = get_supabase()

    areas = (
        sb.table("areas")
        .select("id, name, poverty_index")
        .eq("is_active", True)
        .execute()
    )

    if not areas.data:
        return 0

    stats = []
    for area in areas.data:
        s = await compute_area_crime_stats(area["id"])
        stats.append((area, s))

    max_rate = max((s["crime_rate_per_km2"] for _, s in stats), default=1.0) or 1.0

    now = datetime.now(timezone.utc).isoformat()

    rows = []
    for area, s in stats:
        score = compute_safety_score(
            s["crime_rate_per_km2"],
            float(area.get("poverty_index", 0)),
            max_crime_rate=max_rate,
        )
        rows.append({
            "id": area["id"],
            "crime_count": s["crime_count"],
            "crime_rate_per_km2": s["crime_rate_per_km2"],
            "safety_score": score,
            "safety_color": _score_to_color(score),
            "score_updated_at": now,
        })

    try:
        sb.table("areas").upsert(rows, on_conflict="id").execute()
        updated = len(rows)
    except Exception as e:
        logger.error(f"Failed to batch update safety scores: {e}", exc_info=True)
        updated = 0

    logger.info(f"Refreshed safety scores for {updated} areas")
    return updated
