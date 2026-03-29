import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import events, areas
from routers.neighborhoods import router as neighborhoods_router
from routers.routes import router as routes_router
from routers.scores import router as scores_router
from services.scraper import run_scraper
from services.uk_police_scraper import run_uk_police_scraper
from services.meteoalarm_scraper import run_meteoalarm_scraper
from services.emsc_scraper import run_emsc_scraper
from services.gdacs_scraper import run_gdacs_scraper
from services.bg_news_scraper import run_bg_news_scraper
from services.gnews_scraper import run_gnews_scraper
from services.neighborhood_scores import refresh_all_scores
from services.notify import dispatch_recent_notifications
from services.boundary_ingestion import ingest_all_cities, ingest_neighborhoods_for_city

from db import get_supabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OVERPASS_RATE_LIMIT_SECONDS = 5


async def scraper_loop():
    settings = get_settings()
    interval = settings.scraper_interval_minutes * 60

    # One-time: ingest neighborhood boundaries if none exist,
    # or ingest for cities missing neighborhoods
    try:
        sb = get_supabase()
        boundary_check = (
            sb.table("areas")
            .select("id", count="exact")
            .eq("area_type", "neighborhood")
            .not_.is_("boundary", "null")
            .limit(1)
            .execute()
        )
        if not boundary_check.count:
            logger.info("No neighborhood boundaries found — running full ingestion...")
            results = await ingest_all_cities()
            logger.info("Boundary ingestion complete: %s", results)
        else:
            # Check for cities with no neighborhoods and ingest them
            cities = (
                sb.table("areas")
                .select("id, name, country_code")
                .eq("area_type", "city")
                .eq("is_active", True)
                .execute()
            )
            for city in (cities.data or []):
                cc = city.get("country_code", "")
                if not cc:
                    continue
                child_check = (
                    sb.table("areas")
                    .select("id", count="exact")
                    .eq("parent_id", city["id"])
                    .limit(1)
                    .execute()
                )
                if not child_check.count:
                    logger.info("City %s has no neighborhoods — ingesting...", city["name"])
                    count = await ingest_neighborhoods_for_city(city["id"], cc)
                    logger.info("Ingested %d neighborhoods for %s", count, city["name"])
                    await asyncio.sleep(OVERPASS_RATE_LIMIT_SECONDS)
    except Exception:
        logger.exception("Boundary ingestion failed — will retry next startup")

    while True:
        try:
            logger.info("Running all scrapers...")
            results = await asyncio.gather(
                run_scraper(),
                run_uk_police_scraper(),
                run_meteoalarm_scraper(),
                run_emsc_scraper(),
                run_gdacs_scraper(),
                run_bg_news_scraper(),
                run_gnews_scraper(),
                return_exceptions=True,
            )
            names = ["GDELT", "UK Police", "MeteoAlarm", "EMSC", "GDACS", "BG News", "GNews"]
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error("%s scraper failed: %s", names[i], result, exc_info=result)
            await dispatch_recent_notifications(since_minutes=interval // 60 + 5)
            await refresh_all_scores()
        except Exception:
            logger.exception("Scraper loop iteration failed; will retry next cycle")
        await asyncio.sleep(interval)


def _scraper_task_done(task: asyncio.Task):
    if task.cancelled():
        logger.warning("Scraper task was cancelled")
    elif exc := task.exception():
        logger.critical("Scraper task died unexpectedly: %s", exc, exc_info=exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(scraper_loop())
    task.add_done_callback(_scraper_task_done)
    yield
    task.cancel()


app = FastAPI(title="AlertHood API", version="0.1.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(areas.router)
app.include_router(neighborhoods_router)
app.include_router(routes_router)
app.include_router(scores_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
