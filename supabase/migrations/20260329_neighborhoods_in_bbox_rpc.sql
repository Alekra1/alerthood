-- RPC: get neighborhoods as GeoJSON within a bounding box
CREATE OR REPLACE FUNCTION public.neighborhoods_in_bbox(
  min_lat double precision,
  min_lng double precision,
  max_lat double precision,
  max_lng double precision,
  zoom_level integer DEFAULT 14,
  target_area_type public.area_type DEFAULT 'neighborhood'
)
RETURNS TABLE (
  id uuid,
  name text,
  slug text,
  area_type public.area_type,
  safety_score numeric,
  safety_color text,
  event_count_90d integer,
  parent_name text,
  geojson text
) LANGUAGE sql STABLE AS $$
  SELECT
    a.id, a.name, a.slug, a.area_type,
    a.safety_score, a.safety_color,
    a.crime_count AS event_count_90d,
    p.name AS parent_name,
    extensions.st_asgeojson(
      extensions.st_simplifypreservetopology(
        a.boundary,
        CASE
          WHEN zoom_level >= 15 THEN 0.00001
          WHEN zoom_level >= 12 THEN 0.0001
          WHEN zoom_level >= 10 THEN 0.001
          ELSE 0.005
        END
      )
    ) AS geojson
  FROM public.areas a
  LEFT JOIN public.areas p ON p.id = a.parent_id
  WHERE a.is_active = true
    AND a.boundary IS NOT NULL
    AND a.area_type = target_area_type
    AND extensions.st_intersects(
      a.boundary,
      extensions.st_makeenvelope(min_lng, min_lat, max_lng, max_lat, 4326)
    );
$$;
