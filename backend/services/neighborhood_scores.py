import logging
import math
from datetime import datetime, timezone, timedelta

from db import get_supabase

logger = logging.getLogger(__name__)


async def compute_area_crime_stats(area_id: str, radius_km: float = 5.0) -> dict:
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
    area_km2 = math.pi * radius_km**2
    crime_rate = crime_count / area_km2 if area_km2 > 0 else 0

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


async def refresh_all_scores() -> int:
    """Recompute safety scores for all active areas. Returns count updated."""
    sb = get_supabase()

    areas = (
        sb.table("areas")
        .select("id, name, radius_km, poverty_index")
        .eq("is_active", True)
        .execute()
    )

    if not areas.data:
        return 0

    stats = []
    for area in areas.data:
        s = await compute_area_crime_stats(area["id"], float(area.get("radius_km", 5)))
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
