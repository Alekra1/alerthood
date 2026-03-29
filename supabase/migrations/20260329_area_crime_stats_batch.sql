-- Batch RPC: return crime counts and area sizes for all active areas in one query.
-- Optimized to avoid grouping by large polygon boundaries which causes OOM/Timeouts
CREATE OR REPLACE FUNCTION public.area_crime_stats_batch(
  since_days int DEFAULT 90
)
RETURNS TABLE (
  area_id uuid,
  crime_count bigint,
  area_km2 double precision
) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  WITH crime_counts AS (
    SELECT
      e.area_id,
      COUNT(e.id) AS crime_count
    FROM public.events e
    WHERE e.threat_type = 'crime'
      AND e.occurred_at >= (now() - (since_days || ' days')::interval)
    GROUP BY e.area_id
  )
  SELECT
    a.id AS area_id,
    COALESCE(c.crime_count, 0) AS crime_count,
    COALESCE(
      CASE
        WHEN a.boundary IS NOT NULL
        -- Cast to geography to get area in square meters, divide by 1M for km²
        THEN extensions.st_area(a.boundary::extensions.geography) / 1000000.0
        ELSE NULL
      END,
      1.0
    ) AS area_km2
  FROM public.areas a
  LEFT JOIN crime_counts c ON c.area_id = a.id
  WHERE a.is_active = true;
$$;

GRANT EXECUTE ON FUNCTION public.area_crime_stats_batch(int) TO anon, authenticated;
