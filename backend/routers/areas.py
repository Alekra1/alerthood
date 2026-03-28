import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from auth import get_current_user
from db import get_supabase
from models.schemas import NotificationPrefsUpdate, SubscribeRequest, SubscribeResponse
from services.geocoding import detect_area_from_coords

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["areas"])

MAX_FREE_SUBSCRIPTIONS = 2


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
