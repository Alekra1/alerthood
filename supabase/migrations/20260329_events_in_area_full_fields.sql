-- Extend events_in_area to return full fields matching events_with_coords
-- This allows the Area page to filter events strictly to the detected area.
CREATE OR REPLACE FUNCTION public.events_in_area(
  target_area_id uuid,
  max_rows int default 50
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
    e.threat_type, e.severity, e.status, e.occurred_at,
    extensions.st_y(e.location) AS lat,
    extensions.st_x(e.location) AS lng,
    e.location_label, e.source_type, e.source_url,
    e.relevance_score, e.created_at
  FROM public.events e
  JOIN public.areas a ON a.id = target_area_id
  WHERE e.status = 'active'
    AND a.boundary IS NOT NULL
    AND extensions.st_contains(a.boundary, e.location)
  ORDER BY e.occurred_at DESC
  LIMIT max_rows;
$$;

GRANT EXECUTE ON FUNCTION public.events_in_area(uuid, int) TO anon, authenticated;
