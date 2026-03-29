-- RPC: get bounding box of an area's boundary
CREATE OR REPLACE FUNCTION public.area_bbox(target_area_id uuid)
RETURNS TABLE (
  min_lat double precision,
  min_lng double precision,
  max_lat double precision,
  max_lng double precision
) LANGUAGE sql STABLE AS $$
  SELECT
    extensions.st_ymin(a.boundary::extensions.geometry) AS min_lat,
    extensions.st_xmin(a.boundary::extensions.geometry) AS min_lng,
    extensions.st_ymax(a.boundary::extensions.geometry) AS max_lat,
    extensions.st_xmax(a.boundary::extensions.geometry) AS max_lng
  FROM public.areas a
  WHERE a.id = target_area_id
    AND a.boundary IS NOT NULL;
$$;
