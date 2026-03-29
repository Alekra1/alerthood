-- Update find_nearest_area to use boundary polygons
CREATE OR REPLACE FUNCTION public.find_nearest_area(
  user_point extensions.geometry
)
RETURNS TABLE (
  id uuid,
  name text,
  city text,
  slug text,
  distance_km double precision
) LANGUAGE sql STABLE AS $$
  SELECT
    a.id, a.name,
    COALESCE(p.name, a.city) AS city,
    a.slug,
    extensions.st_distance(
      a.boundary::extensions.geography,
      user_point::extensions.geography
    ) / 1000.0 AS distance_km
  FROM public.areas a
  LEFT JOIN public.areas p ON p.id = a.parent_id
  WHERE a.is_active = true
    AND a.boundary IS NOT NULL
    AND extensions.st_contains(a.boundary, user_point)
  ORDER BY extensions.st_distance(
    a.boundary::extensions.geography,
    user_point::extensions.geography
  )
  LIMIT 1;
$$;

-- Update find_nearest_area_batch to use boundary polygons
CREATE OR REPLACE FUNCTION public.find_nearest_area_batch(
  points jsonb
)
RETURNS TABLE (
  idx integer,
  area_id uuid
) LANGUAGE sql STABLE AS $$
  SELECT
    (p.ordinality - 1)::integer AS idx,
    (
      SELECT a.id
      FROM public.areas a
      WHERE a.is_active = true
        AND a.boundary IS NOT NULL
        AND extensions.st_contains(
          a.boundary,
          extensions.st_setsrid(extensions.st_point(
            (p.value->>'lng')::double precision,
            (p.value->>'lat')::double precision
          ), 4326)
        )
      ORDER BY extensions.st_distance(
        a.boundary::extensions.geography,
        extensions.st_setsrid(extensions.st_point(
          (p.value->>'lng')::double precision,
          (p.value->>'lat')::double precision
        ), 4326)::extensions.geography
      )
      LIMIT 1
    ) AS area_id
  FROM jsonb_array_elements(points) WITH ORDINALITY AS p(value, ordinality)
$$;

-- Update events_in_area to use boundary
CREATE OR REPLACE FUNCTION public.events_in_area(target_area_id uuid)
RETURNS TABLE (
  id uuid,
  title text,
  threat_type public.threat_type,
  severity public.severity_level,
  occurred_at timestamptz,
  lat double precision,
  lng double precision,
  relevance_score integer
) LANGUAGE sql STABLE AS $$
  SELECT
    e.id, e.title, e.threat_type, e.severity, e.occurred_at,
    extensions.st_y(e.location) AS lat,
    extensions.st_x(e.location) AS lng,
    e.relevance_score
  FROM public.events e
  JOIN public.areas a ON a.id = target_area_id
  WHERE e.status = 'active'
    AND a.boundary IS NOT NULL
    AND extensions.st_contains(a.boundary, e.location)
  ORDER BY e.occurred_at DESC
  LIMIT 500;
$$;
