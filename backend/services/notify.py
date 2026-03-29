"""Notification dispatch service.

Called after each scraper cycle. Looks for high/critical-severity events
inserted in the last `since_minutes` minutes, finds users subscribed to
those areas, and inserts one notification per (user, event) pair.

The notifications table has a unique index on (user_id, event_id), so
this is safe to call multiple times — duplicates are silently ignored.
"""

import logging
from datetime import datetime, timezone, timedelta

from db import get_supabase

logger = logging.getLogger(__name__)


async def dispatch_recent_notifications(since_minutes: int = 20) -> None:
    """Find high/critical events inserted recently and notify subscribed users."""
    db = get_supabase()

    since = (datetime.now(timezone.utc) - timedelta(minutes=since_minutes)).isoformat()

    # Find recent high/critical events that belong to a monitored area
    result = db.table("events") \
        .select("id, title, severity, area_id, threat_type") \
        .gte("created_at", since) \
        .eq("severity", "critical") \
        .eq("status", "active") \
        .not_.is_("area_id", "null") \
        .execute()

    notable = result.data or []
    if not notable:
        logger.info("dispatch_recent_notifications: no critical events in last %dm", since_minutes)
        return

    # Group by area
    area_to_events: dict[str, list[dict]] = {}
    for e in notable:
        area_to_events.setdefault(e["area_id"], []).append(e)

    # Find subscribed users for those areas
    area_ids = list(area_to_events.keys())
    subs_result = db.table("user_area_subscriptions") \
        .select("user_id, area_id") \
        .in_("area_id", area_ids) \
        .execute()

    notifications: list[dict] = []
    for sub in (subs_result.data or []):
        for event in area_to_events.get(sub["area_id"], []):
            notifications.append({
                "user_id": sub["user_id"],
                "event_id": event["id"],
                "title": event["title"],
                "body": (
                    f"{event.get('severity', '').upper()} severity "
                    f"{event.get('threat_type', 'event').replace('_', ' ')} in your monitored area"
                ),
            })

    if not notifications:
        logger.info("dispatch_recent_notifications: no subscribed users for %d notable events", len(notable))
        return

    # Upsert with ON CONFLICT DO NOTHING (requires unique index on user_id, event_id)
    inserted = 0
    for i in range(0, len(notifications), 50):
        chunk = notifications[i : i + 50]
        try:
            db.table("notifications").upsert(
                chunk, on_conflict="user_id,event_id", ignore_duplicates=True
            ).execute()
            inserted += len(chunk)
        except Exception:
            logger.exception("Failed to insert notifications chunk %d-%d", i, i + len(chunk))

    logger.info(
        "dispatch_recent_notifications: %d notifications for %d events across %d areas",
        inserted,
        len(notable),
        len(area_to_events),
    )
