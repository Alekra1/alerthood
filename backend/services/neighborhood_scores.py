import asyncio
import logging
from datetime import datetime, timezone

from db import get_supabase

logger = logging.getLogger(__name__)


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


def _fetch_all_scores_sync() -> int:
    """
    Synchronous core of refresh_all_scores.

    Replaces N×2 individual Supabase HTTP calls (one events query + one
    area_size_km2 RPC per area) with two total calls:
      1. area_crime_stats_batch RPC — crime counts + km² for all areas in one SQL query
      2. areas.upsert — write all scores in one batch

    This prevents HTTP/2 connection pool exhaustion when there are many areas.
    """
    sb = get_supabase()

    # 1. Fetch poverty_index per area (lightweight, single request)
    areas_resp = (
        sb.table("areas")
        .select("id, poverty_index")
        .eq("is_active", True)
        .execute()
    )
    if not areas_resp.data:
        return 0

    poverty_by_id = {
        a["id"]: float(a.get("poverty_index") or 0)
        for a in areas_resp.data
    }

    # 2. Single batch RPC: crime counts + area sizes for all active areas
    stats_resp = sb.rpc("area_crime_stats_batch", {"since_days": 90}).execute()
    if not stats_resp.data:
        logger.warning("area_crime_stats_batch returned no data")
        return 0

    rates = []
    for row in stats_resp.data:
        area_km2 = float(row["area_km2"] or 1.0)
        crime_count = int(row["crime_count"] or 0)
        rates.append((row["area_id"], crime_count, crime_count / area_km2))

    max_rate = max((r for _, _, r in rates), default=1.0) or 1.0

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for area_id, crime_count, crime_rate in rates:
        score = compute_safety_score(
            crime_rate,
            poverty_by_id.get(area_id, 0.0),
            max_crime_rate=max_rate,
        )
        rows.append({
            "id": area_id,
            "crime_count": crime_count,
            "crime_rate_per_km2": round(crime_rate, 2),
            "safety_score": score,
            "safety_color": _score_to_color(score),
            "score_updated_at": now,
        })

    # 3. Single upsert for all areas
    try:
        sb.table("areas").upsert(rows, on_conflict="id").execute()
        updated = len(rows)
    except Exception as e:
        logger.error("Failed to batch update safety scores: %s", e, exc_info=True)
        updated = 0

    logger.info("Refreshed safety scores for %d areas", updated)
    return updated


async def refresh_all_scores() -> int:
    """Recompute safety scores for all active areas. Returns count updated."""
    return await asyncio.to_thread(_fetch_all_scores_sync)
