import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

from postgrest.exceptions import APIError

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


def _fetch_per_area_sync(sb, areas_data: list, poverty_by_id: dict) -> list:
    """Fallback: compute crime stats one area at a time (original approach)."""
    since = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    rates = []
    for area in areas_data:
        area_id = area["id"]
        result = (
            sb.table("events")
            .select("id", count="exact")
            .eq("area_id", area_id)
            .eq("threat_type", "crime")
            .gte("occurred_at", since)
            .execute()
        )
        crime_count = result.count or 0
        area_result = sb.rpc("area_size_km2", {"target_area_id": area_id}).execute()
        area_km2 = (area_result.data[0]["area_km2"] if area_result.data else 0) or 1.0
        rates.append((area_id, crime_count, crime_count / area_km2))
    return rates


def _fetch_all_scores_sync() -> int:
    """
    Synchronous core of refresh_all_scores.

    Tries the batch RPC first (2 total HTTP calls). If the migration hasn't
    been applied yet (PGRST202), falls back to the original per-area approach
    so the scraper keeps running.
    """
    sb = get_supabase()

    _PAGE = 1000  # Supabase server-side row cap per request

    def _fetch_all_pages(query_fn):
        """Paginate through all rows, respecting the server's 1000-row cap."""
        rows = []
        page = 0
        while True:
            resp = query_fn(page * _PAGE, (page + 1) * _PAGE - 1)
            if not resp.data:
                break
            rows.extend(resp.data)
            if len(resp.data) < _PAGE:
                break
            page += 1
        return rows

    # 1. Fetch poverty_index for ALL active areas (paginated)
    all_areas = _fetch_all_pages(
        lambda lo, hi: sb.table("areas")
            .select("id, poverty_index")
            .eq("is_active", True)
            .range(lo, hi)
            .execute()
    )
    if not all_areas:
        return 0

    poverty_by_id = {
        a["id"]: float(a.get("poverty_index") or 0)
        for a in all_areas
    }

    # 2a. Try the fast batch RPC (paginated)
    try:
        all_stats = _fetch_all_pages(
            lambda lo, hi: sb.rpc("area_crime_stats_batch", {"since_days": 90})
                .range(lo, hi)
                .execute()
        )
        if not all_stats:
            logger.warning("area_crime_stats_batch returned no data")
            return 0
        rates = [
            (row["area_id"], int(row["crime_count"] or 0),
             int(row["crime_count"] or 0) / float(row["area_km2"] or 1.0))
            for row in all_stats
        ]
    except APIError as e:
        if e.code == "PGRST202":
            # Migration not yet applied — fall back gracefully
            logger.warning(
                "area_crime_stats_batch RPC not found; run migration "
                "20260329_area_crime_stats_batch.sql. Falling back to per-area queries."
            )
            rates = _fetch_per_area_sync(sb, all_areas, poverty_by_id)
        else:
            raise

    max_rate = max((r for _, _, r in rates), default=1.0) or 1.0
    now = datetime.now(timezone.utc).isoformat()

    # Only update areas we know exist in the DB (avoid INSERT attempts that
    # would violate NOT NULL constraints on other columns like `name`).
    known_ids = set(poverty_by_id.keys())

    rows = []
    for area_id, crime_count, crime_rate in rates:
        if area_id not in known_ids:
            continue
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

    if not rows:
        logger.warning("No valid areas to update after filtering")
        return 0

    # Use UPDATE (not upsert) so we never INSERT rows — that would violate
    # NOT NULL constraints on columns we don't own (e.g. `name`).
    # Run concurrently to keep total time reasonable for large area counts.
    _WORKERS = 20

    def _do_update(row: dict) -> bool:
        _sb = get_supabase()
        area_id = row["id"]
        payload = {k: v for k, v in row.items() if k != "id"}
        try:
            _sb.table("areas").update(payload).eq("id", area_id).execute()
            return True
        except Exception as exc:
            logger.debug("Score update failed for area %s: %s", area_id, exc)
            return False

    updated = 0
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        futures = {pool.submit(_do_update, row): row["id"] for row in rows}
        for future in as_completed(futures):
            if future.result():
                updated += 1

    logger.info("Refreshed safety scores for %d areas", updated)
    return updated


async def refresh_all_scores() -> int:
    """Recompute safety scores for all active areas. Returns count updated."""
    return await asyncio.to_thread(_fetch_all_scores_sync)
