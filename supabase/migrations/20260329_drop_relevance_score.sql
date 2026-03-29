-- Drop relevance_score from events table and update all RPCs that reference it

-- 1. Update events_with_coords to remove relevance_score (keep expires_at from migration 7)
DROP FUNCTION IF EXISTS public.events_with_coords(int);
CREATE FUNCTION public.events_with_coords(
  max_rows int default 200
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
  created_at timestamptz
) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT
    e.id, e.area_id, e.title, e.description,
    e.threat_type, e.severity, e.status, e.occurred_at, e.expires_at,
    extensions.st_y(e.approx_center) AS lat,
    extensions.st_x(e.approx_center) AS lng,
    e.location_label, e.source_type, e.source_url,
    e.created_at
  FROM public.events e
  WHERE e.status NOT IN ('resolved', 'dismissed')
    AND e.expires_at > now()
  ORDER BY e.occurred_at DESC
  LIMIT max_rows;
$$;

GRANT EXECUTE ON FUNCTION public.events_with_coords(int) TO anon, authenticated;

-- 2. Update events_in_area to remove relevance_score
CREATE OR REPLACE FUNCTION public.events_in_area(target_area_id uuid)
RETURNS TABLE (
  id uuid,
  title text,
  threat_type public.threat_type,
  severity public.severity_level,
  occurred_at timestamptz,
  lat double precision,
  lng double precision
) LANGUAGE sql STABLE AS $$
  SELECT
    e.id, e.title, e.threat_type, e.severity, e.occurred_at,
    extensions.st_y(e.approx_center) AS lat,
    extensions.st_x(e.approx_center) AS lng
  FROM public.events e
  JOIN public.areas a ON a.id = target_area_id
  WHERE e.status NOT IN ('resolved', 'dismissed')
    AND a.boundary IS NOT NULL
    AND extensions.st_contains(a.boundary, e.approx_center)
  ORDER BY e.occurred_at DESC
  LIMIT 500;
$$;

-- 3. Drop the column from the events table
ALTER TABLE public.events DROP COLUMN IF EXISTS relevance_score;
