from fastapi import APIRouter, Depends

from auth import get_current_user
from models.schemas import RouteRequest, SafeRouteResponse
from services.route_engine import calculate_safe_route

router = APIRouter(prefix="/api/routes", tags=["routes"])


@router.post("/safe", response_model=SafeRouteResponse)
async def get_safe_route(req: RouteRequest, user_id: str = Depends(get_current_user)):
    return await calculate_safe_route(req)
