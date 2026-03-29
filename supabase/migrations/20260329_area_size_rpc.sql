-- RPC: get area size in km² from boundary polygon
CREATE OR REPLACE FUNCTION public.area_size_km2(target_area_id uuid)
RETURNS TABLE (area_km2 double precision)
LANGUAGE sql STABLE AS $$
  SELECT
    CASE
      WHEN a.boundary IS NOT NULL
      THEN extensions.st_area(a.boundary::extensions.geography) / 1e6
      ELSE NULL
    END AS area_km2
  FROM public.areas a
  WHERE a.id = target_area_id;
$$;
