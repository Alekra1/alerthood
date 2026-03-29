-- Batch RPC: return crime counts and area sizes for all active areas in one query.
-- Replaces N×2 individual calls in refresh_all_scores().
CREATE OR REPLACE FUNCTION public.area_crime_stats_batch(
  since_days int DEFAULT 90
)
RETURNS TABLE (
  area_id uuid,
  crime_count bigint,
  area_km2 double precision
) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT
    a.id AS area_id,
    COUNT(e.id) AS crime_count,
    COALESCE(
      CASE
        WHEN a.boundary IS NOT NULL
        THEN extensions.st_area(a.boundary::extensions.geography) / 1e6
        ELSE NULL
      END,
      1.0
    ) AS area_km2
  FROM public.areas a
  LEFT JOIN public.events e
    ON e.area_id = a.id
    AND e.threat_type = 'crime'
    AND e.occurred_at >= (now() - (since_days || ' days')::interval)
  WHERE a.is_active = true
  GROUP BY a.id, a.boundary;
$$;

GRANT EXECUTE ON FUNCTION public.area_crime_stats_batch(int) TO anon, authenticated;
