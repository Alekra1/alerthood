-- Deduplicate events by source_url (keep oldest per source_url)
DELETE FROM events
WHERE id NOT IN (
  SELECT DISTINCT ON (source_url) id
  FROM events
  WHERE source_url IS NOT NULL
  ORDER BY source_url, created_at ASC
)
AND source_url IS NOT NULL;

-- Deduplicate UK Police events (same title + area + day)
DELETE FROM events
WHERE source_type = 'uk_police'
AND id NOT IN (
  SELECT DISTINCT ON (title, area_id, date_trunc('day', occurred_at)) id
  FROM events
  WHERE source_type = 'uk_police'
  ORDER BY title, area_id, date_trunc('day', occurred_at), created_at ASC
);

-- Prevent future duplicates via unique partial index
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_source_url_unique
ON events (source_url)
WHERE source_url IS NOT NULL;
