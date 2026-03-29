"""Shared event insertion helper with dedup handling.

When a batch insert fails due to duplicate source_url, falls back to
inserting events one by one so non-duplicate rows still get inserted.
"""

import logging

from supabase import Client

logger = logging.getLogger(__name__)


def insert_events_batch(db: Client, events: list[dict], source_name: str, chunk_size: int = 50) -> int:
    """Insert events in chunks, falling back to individual inserts on conflict."""
    inserted = 0
    for i in range(0, len(events), chunk_size):
        chunk = events[i : i + chunk_size]
        try:
            result = db.table("events").insert(chunk).execute()
            inserted += len(result.data) if result.data else 0
        except Exception as exc:
            if "duplicate" in str(exc).lower() or "23505" in str(exc):
                # Batch had duplicates — insert individually to save non-dupes
                for event in chunk:
                    try:
                        db.table("events").insert(event).execute()
                        inserted += 1
                    except Exception as inner_exc:
                        if "duplicate" in str(inner_exc).lower() or "23505" in str(inner_exc):
                            continue
                        logger.debug("Failed to insert single %s event: %s", source_name, inner_exc)
            else:
                logger.exception("Failed to insert %s events chunk %d-%d", source_name, i, i + len(chunk))
    return inserted
