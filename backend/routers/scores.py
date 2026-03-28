import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from db import get_supabase
from models.schemas import NeighborhoodScore, NeighborhoodScoresResponse
from services.neighborhood_scores import refresh_all_scores

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scores", tags=["scores"])


@router.get("", response_model=NeighborhoodScoresResponse)
async def get_neighborhood_scores(user_id: str = Depends(get_current_user)):
    """Get safety scores for all active areas."""
    sb = get_supabase()

    try:
        result = (
            sb.table("areas")
            .select(
                "id, name, crime_count, crime_rate_per_km2, poverty_index, safety_score, score_updated_at"
            )
            .eq("is_active", True)
            .order("safety_score", desc=False)
            .execute()
        )
    except Exception as e:
        logger.error(f"Failed to fetch neighborhood scores: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Safety scores temporarily unavailable")

    scores = [
        NeighborhoodScore(
            area_id=row["id"],
            area_name=row["name"],
            crime_count=row.get("crime_count", 0),
            crime_rate_per_km2=float(row.get("crime_rate_per_km2", 0)),
            poverty_index=float(row.get("poverty_index", 0)),
            safety_score=float(row.get("safety_score", 50)),
            score_updated_at=row.get("score_updated_at"),
        )
        for row in (result.data or [])
    ]

    return NeighborhoodScoresResponse(
        scores=scores,
        computed_at=datetime.now(timezone.utc),
    )


@router.post("/refresh")
async def refresh_scores(user_id: str = Depends(get_current_user)):
    """Recompute all neighborhood safety scores."""
    try:
        count = await refresh_all_scores()
    except Exception as e:
        logger.error(f"Failed to refresh scores: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Score refresh failed")
    return {"updated": count}
