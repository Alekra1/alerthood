"""Bulgarian news RSS scraper — main pipeline orchestrator.

Pipeline:
  RSS feeds → dedup against DB → Stage 1 AI title filter →
  fetch full article text → Stage 2 AI extraction + translation →
  Nominatim geocoding → find_nearest_area_batch → insert_events_batch
"""

import asyncio
import logging
from datetime import datetime, timezone

import feedparser

from db import get_supabase
from services.ai_extractor import extract_event, filter_relevant_titles
from services.article_fetcher import fetch_article_text
from services.geocoding import geocode_location
from services.insert_events import insert_events_batch

logger = logging.getLogger(__name__)

# RSS sources — URLs verified 2026-03-29
RSS_FEEDS = [
    "https://www.24chasa.bg/rss",                          # 200 OK — 100 entries, police blotter style
    "https://www.focus-news.net/rss.php",                   # 200 OK — 30 entries, police press releases
    "https://btvnovinite.bg/lbin/v3/rss.php",              # 200 OK — 10 entries, general news, filter strictly
    "https://www.novinite.com/services/news_rdf.php",       # 200 OK — 26 entries, EN, no translation needed
    "https://blitz.bg/rss",                                 # 200 OK — 50 entries, high-volume crime coverage
]

BATCH_SIZE = 20      # titles per Stage 1 call
REQUEST_DELAY_S = 2.0  # polite delay between article fetches

_SEVERITY_SCORE = {"low": 25, "medium": 50, "high": 75, "critical": 100}


def _parse_pub_date(entry) -> str:
    """Return ISO-8601 UTC string from a feedparser entry, falling back to now."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except (ValueError, TypeError):
            pass
    return datetime.now(timezone.utc).isoformat()


async def _fetch_feed(url: str) -> list[dict]:
    """Fetch and parse one RSS feed. Returns list of {url, title, pub_date}. Logs and returns [] on failure."""
    try:
        parsed = await asyncio.to_thread(feedparser.parse, url)
    except Exception as e:
        logger.warning("RSS fetch failed for %s: %s", url, e)
        return []

    if parsed.get("bozo") and not parsed.entries:
        logger.warning("RSS feed %s returned bozo error: %s", url, parsed.get("bozo_exception"))
        return []

    items = []
    for entry in parsed.entries:
        article_url = getattr(entry, "link", "")
        title = getattr(entry, "title", "").strip()
        if not article_url or not title:
            continue
        items.append({"url": article_url, "title": title, "pub_date": _parse_pub_date(entry)})

    logger.info("Feed %s: %d articles", url, len(items))
    return items


async def _dedup(db, items: list[dict]) -> list[dict]:
    """Drop articles whose source_url already exists in the events table."""
    if not items:
        return []

    urls = [i["url"] for i in items]
    try:
        result = db.table("events").select("source_url").in_("source_url", urls).execute()
        known = {row["source_url"] for row in (result.data or [])}
    except Exception as e:
        logger.error("Dedup query failed: %s — aborting to prevent duplicates", e)
        return []

    before = len(items)
    items = [i for i in items if i["url"] not in known]
    logger.info("Dedup: %d/%d articles are new", len(items), before)
    return items


async def run_bg_news_scraper() -> None:
    """Fetch Bulgarian news RSS feeds and insert relevant crime/safety events."""
    db = get_supabase()

    # 1. Fetch all feeds concurrently
    feed_results = await asyncio.gather(*[_fetch_feed(url) for url in RSS_FEEDS])
    all_items: list[dict] = [item for feed in feed_results for item in feed]
    logger.info("Total articles from all feeds: %d", len(all_items))

    if not all_items:
        return

    # 2. Deduplicate against DB
    all_items = await _dedup(db, all_items)
    if not all_items:
        logger.info("All articles already in DB — nothing to process")
        return

    # 3. Stage 1: filter titles in BATCH_SIZE chunks
    relevant_items: list[dict] = []
    for batch_start in range(0, len(all_items), BATCH_SIZE):
        batch = all_items[batch_start : batch_start + BATCH_SIZE]
        title_batch = [{"index": i, "title": item["title"]} for i, item in enumerate(batch)]
        relevant_indices = await filter_relevant_titles(title_batch)
        for idx in relevant_indices:
            if 0 <= idx < len(batch):
                relevant_items.append(batch[idx])

    logger.info("Stage 1 filter: %d/%d articles are relevant", len(relevant_items), len(all_items))
    if not relevant_items:
        return

    # 4. Fetch full article text + Stage 2 extraction for each relevant article
    extracted: list[dict] = []
    for i, item in enumerate(relevant_items):
        if i > 0:
            await asyncio.sleep(REQUEST_DELAY_S)

        text = await fetch_article_text(item["url"])
        if not text:
            continue

        event_data = await extract_event(item["title"], text)
        if not event_data:
            continue

        extracted.append({**item, **event_data})

    logger.info("Stage 2 extraction: %d/%d articles yielded structured data", len(extracted), len(relevant_items))
    if not extracted:
        return

    # 5. Geocode locations
    geocoded: list[dict] = []
    for item in extracted:
        coords = await geocode_location(item["location_text"], item["city"])
        if coords is None:
            logger.debug("No geocode result for %r, %r — skipping", item["location_text"], item["city"])
            continue
        lat, lng = coords
        geocoded.append({**item, "_lat": lat, "_lng": lng})

    logger.info("Geocoded %d/%d articles", len(geocoded), len(extracted))
    if not geocoded:
        return

    # 6. Batch area lookup
    points = [{"lat": e["_lat"], "lng": e["_lng"]} for e in geocoded]
    try:
        batch_result = db.rpc("find_nearest_area_batch", {"points": points}).execute()
        area_by_idx = {row["idx"]: row["area_id"] for row in (batch_result.data or []) if row.get("area_id")}
    except Exception as e:
        logger.error("find_nearest_area_batch RPC failed: %s — aborting insert", e)
        return

    # 7. Build final event payloads
    events: list[dict] = []
    for i, item in enumerate(geocoded):
        area_id = area_by_idx.get(i)
        if not area_id:
            logger.debug("No area match for %r — skipping", item["url"])
            continue

        severity = item["severity"]
        events.append({
            "title": item["title_en"],
            "description": item["summary_en"],
            "threat_type": item["threat_type"],
            "severity": severity,
            "occurred_at": item["pub_date"],
            "location": f"SRID=4326;POINT({item['_lng']} {item['_lat']})",
            "location_label": item["location_text"],
            "source_type": "news",
            "source_url": item["url"],
            "relevance_score": _SEVERITY_SCORE.get(severity, 50),
            "area_id": area_id,
        })

    logger.info("Matched %d/%d articles to monitored areas", len(events), len(geocoded))
    if not events:
        return

    inserted = insert_events_batch(db, events, "BG News")
    logger.info("BG News scraper: inserted %d/%d events", inserted, len(events))
