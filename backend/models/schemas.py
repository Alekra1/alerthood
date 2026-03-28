from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ThreatType(str, Enum):
    crime = "crime"
    infrastructure = "infrastructure"
    disturbance = "disturbance"
    natural = "natural"


class SeverityLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TimeBucket(str, Enum):
    morning = "morning"
    afternoon = "afternoon"
    evening = "evening"
    night = "night"
    all = "all"


# --- Events ---


class EventCreate(BaseModel):
    title: str
    description: str | None = None
    threat_type: ThreatType
    severity: SeverityLevel = SeverityLevel.medium
    occurred_at: datetime
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    location_label: str | None = None
    source_type: str = "news"
    source_url: str | None = None
    area_id: str | None = None


class EventResponse(BaseModel):
    id: str
    created_at: datetime


class HeatmapCell(BaseModel):
    lat: float
    lng: float
    weight: float = Field(ge=0.0, le=1.0)
    event_count: int


class HeatmapResponse(BaseModel):
    cells: list[HeatmapCell]
    time_bucket: TimeBucket
    generated_at: datetime


# --- Subscriptions ---


class SubscribeRequest(BaseModel):
    area_id: str
    label: str = "Home"


class SubscribeResponse(BaseModel):
    subscription_id: str


class NotificationPrefsUpdate(BaseModel):
    notification_crime: bool | None = None
    notification_infrastructure: bool | None = None
    notification_natural: bool | None = None
    notification_disturbance: bool | None = None
    min_severity: SeverityLevel | None = None


# --- Routes ---


class RouteRequest(BaseModel):
    origin_lat: float = Field(ge=-90, le=90)
    origin_lng: float = Field(ge=-180, le=180)
    dest_lat: float = Field(ge=-90, le=90)
    dest_lng: float = Field(ge=-180, le=180)


class RouteWaypoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class SafeRouteResponse(BaseModel):
    waypoints: list[RouteWaypoint] = Field(min_length=2)
    google_maps_url: str
    avoided_events: int = Field(ge=0)
    distance_km: float = Field(ge=0)


# --- Neighborhood Scores ---


class NeighborhoodScore(BaseModel):
    area_id: str
    area_name: str
    crime_count: int = Field(ge=0)
    crime_rate_per_km2: float = Field(ge=0)
    poverty_index: float = Field(ge=0, le=50)
    safety_score: float = Field(ge=0, le=100)
    score_updated_at: datetime | None


class NeighborhoodScoresResponse(BaseModel):
    scores: list[NeighborhoodScore]
    computed_at: datetime
