-- Add expires_at column, defaulting to 24 hours after created_at
ALTER TABLE public.events
  ADD COLUMN expires_at timestamptz NOT NULL DEFAULT now() + interval '24 hours';

-- Backfill existing rows
UPDATE public.events SET expires_at = created_at + interval '24 hours';

-- Index for fast expiry filtering
CREATE INDEX events_expires_at_idx ON public.events (expires_at);

-- Drop and recreate events_with_coords with expires_at in return type
DROP FUNCTION IF EXISTS public.events_with_coords(int);

CREATE FUNCTION public.events_with_coords(
  max_rows int DEFAULT 200
)
RETURNS TABLE (
  id uuid,
  area_id uuid,
  title text,
  description text,
  threat_type public.threat_type,
  severity public.severity_level,
  status public.event_status,
  occurred_at timestamptz,
  expires_at timestamptz,
  lat double precision,
  lng double precision,
  location_label text,
  source_type text,
  source_url text,
  relevance_score int,
  created_at timestamptz
) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT
    e.id, e.area_id, e.title, e.description,
    e.threat_type, e.severity, e.status, e.occurred_at, e.expires_at,
    extensions.st_y(e.location) AS lat,
    extensions.st_x(e.location) AS lng,
    e.location_label, e.source_type, e.source_url,
    e.relevance_score, e.created_at
  FROM public.events e
  WHERE e.status = 'active'
    AND e.expires_at > now()
  ORDER BY e.occurred_at DESC
  LIMIT max_rows;
$$;

GRANT EXECUTE ON FUNCTION public.events_with_coords(int) TO anon, authenticated;
