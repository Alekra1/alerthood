import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from supabase import Client

from auth import get_current_user
from db import get_supabase
from models.schemas import NotificationPrefsUpdate, SubscribeRequest, SubscribeResponse
from services.geocoding import detect_area_from_coords
from services.ai_summary import generate_area_brief

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["areas"])

MAX_FREE_SUBSCRIPTIONS = 2


class AlertItem(BaseModel):
    title: str
    category: str
    severity: str


class IncidentItem(BaseModel):
    title: str
    category: str
    minutesAgo: int


class AreaSummaryRequest(BaseModel):
    area_id: str
    area_name: str
    safety_score: float
    risk_level: str
    crime_count: int = 0
    crime_rate_per_km2: float = 0.0
    score_updated_at: Optional[str] = None
    active_alerts: list[AlertItem] = []
    recent_incidents: list[IncidentItem] = []


def _crime_trends(db: Client, area_id: str) -> dict:
    """Return crime incident counts for 7, 30, and 90-day windows."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    windows = {"incidents_7d": 7, "incidents_30d": 30, "incidents_90d": 90}
    result = {}
    for key, days in windows.items():
        since = (now - timedelta(days=days)).isoformat()
        try:
            resp = (
                db.table("events")
                .select("id", count="exact")
                .eq("area_id", area_id)
                .eq("threat_type", "crime")
                .gte("occurred_at", since)
                .execute()
            )
            result[key] = resp.count or 0
        except Exception:
            result[key] = None
    return result


@router.get("/areas/detect")
async def detect_area(
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    user_id: str = Depends(get_current_user),
):
    """Auto-detect area from coordinates."""
    try:
        area = await detect_area_from_coords(lat, lng)
    except Exception as e:
        logger.error(f"Area detection failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Area detection temporarily unavailable")
    if not area:
        return {"area": None, "message": "No monitored area found near your location"}
    return {"area": area}


@router.post("/areas/summary")
async def area_summary(
    req: AreaSummaryRequest,
    user_id: str = Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Generate an AI safety brief for an area using the provided data."""
    trends = _crime_trends(db, req.area_id)
    brief = await generate_area_brief(
        area_name=req.area_name,
        safety_score=req.safety_score,
        risk_level=req.risk_level,
        crime_count=req.crime_count,
        crime_rate_per_km2=req.crime_rate_per_km2,
        score_updated_at=req.score_updated_at,
        active_alerts=[a.model_dump() for a in req.active_alerts],
        recent_incidents=[i.model_dump() for i in req.recent_incidents],
        trends=trends,
    )
    if brief is None:
        raise HTTPException(status_code=503, detail="AI summary temporarily unavailable")
    return {"brief": brief}


@router.post("/areas/subscribe", response_model=SubscribeResponse, status_code=201)
async def subscribe_to_area(
    req: SubscribeRequest,
    user_id: str = Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    existing = (
        db.table("user_area_subscriptions")
        .select("id")
        .eq("user_id", user_id)
        .execute()
    )
    if len(existing.data) >= MAX_FREE_SUBSCRIPTIONS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Free users can monitor at most {MAX_FREE_SUBSCRIPTIONS} areas",
        )

    result = (
        db.table("user_area_subscriptions")
        .insert({"user_id": user_id, "area_id": req.area_id, "label": req.label})
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Subscription insert returned no data")
    return SubscribeResponse(subscription_id=result.data[0]["id"])


@router.delete("/areas/{area_id}/subscribe", status_code=204)
async def unsubscribe_from_area(
    area_id: str,
    user_id: str = Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    db.table("user_area_subscriptions").delete().eq("user_id", user_id).eq("area_id", area_id).execute()


@router.patch("/subscriptions/{subscription_id}/notifications", status_code=204)
async def update_notification_prefs(
    subscription_id: str,
    prefs: NotificationPrefsUpdate,
    user_id: str = Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    try:
        sub = (
            db.table("user_area_subscriptions")
            .select("user_id")
            .eq("id", subscription_id)
            .single()
            .execute()
        )
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    if sub.data["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your subscription")

    updates = prefs.model_dump(exclude_none=True)
    if updates:
        db.table("user_area_subscriptions").update(updates).eq("id", subscription_id).execute()
