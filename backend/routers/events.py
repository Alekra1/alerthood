from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from supabase import Client

from auth import get_current_user
from db import get_supabase
from models.schemas import (
    EventCreate,
    EventResponse,
    HeatmapCell,
    HeatmapResponse,
    TimeBucket,
)
from services.safety_score import compute_heatmap

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(
    event: EventCreate,
    user_id: str = Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    row = {
        "title": event.title,
        "description": event.description,
        "threat_type": event.threat_type.value,
        "severity": event.severity.value,
        "occurred_at": event.occurred_at.isoformat(),
        "location": f"SRID=4326;POINT({event.lng} {event.lat})",
        "location_label": event.location_label,
        "source_type": event.source_type,
        "source_url": event.source_url,
        "area_id": event.area_id,
    }
    result = db.table("events").insert(row).execute()
    data = result.data[0]
    return EventResponse(id=data["id"], created_at=data["created_at"])


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    area_id: str,
    time_bucket: TimeBucket = TimeBucket.all,
    db: Client = Depends(get_supabase),
):
    cells = await compute_heatmap(db, area_id, time_bucket)
    return HeatmapResponse(
        cells=cells,
        time_bucket=time_bucket.value,
        generated_at=datetime.now(timezone.utc),
    )
