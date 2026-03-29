-- Drop legacy circle-based columns now that all areas have boundary polygons.
-- All 723 active areas have been verified to have non-null boundary values.
--
-- NOTE: We keep the `city` column for now because it carries denormalized city
-- names used by scrapers (uk_police, meteoalarm) and the frontend ProfileView.
-- It should be dropped in a future migration once parent_id hierarchy is
-- fully established (i.e., city parent areas exist with parent_id set).

-- 1. Update RPCs to remove center/radius_km fallback logic
-- ─────────────────────────────────────────────────────────

-- find_nearest_area: boundary-only (no center+radius fallback)
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

-- find_nearest_area_batch: boundary-only
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
          extensions.st_point(
            (p.value->>'lng')::double precision,
            (p.value->>'lat')::double precision
          )
        )
      ORDER BY extensions.st_distance(
        a.boundary::extensions.geography,
        extensions.st_point(
          (p.value->>'lng')::double precision,
          (p.value->>'lat')::double precision
        )::extensions.geography
      )
      LIMIT 1
    ) AS area_id
  FROM jsonb_array_elements(points) WITH ORDINALITY AS p(value, ordinality)
$$;

-- events_in_area: boundary-only
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

-- area_size_km2: boundary-only (remove radius_km fallback)
CREATE OR REPLACE FUNCTION public.area_size_km2(target_area_id uuid)
RETURNS TABLE (area_km2 double precision)
LANGUAGE sql STABLE AS $$
  SELECT
    extensions.st_area(a.boundary::extensions.geography) / 1e6 AS area_km2
  FROM public.areas a
  WHERE a.id = target_area_id
    AND a.boundary IS NOT NULL;
$$;

-- area_center_coords: use boundary centroid instead of center column
CREATE OR REPLACE FUNCTION public.area_center_coords(area_id uuid)
RETURNS TABLE (lat double precision, lng double precision)
LANGUAGE sql STABLE AS $$
  SELECT
    extensions.st_y(extensions.st_centroid(a.boundary)) AS lat,
    extensions.st_x(extensions.st_centroid(a.boundary)) AS lng
  FROM public.areas a
  WHERE a.id = area_center_coords.area_id
    AND a.boundary IS NOT NULL;
$$;

-- 2. Drop the old GiST index on center
-- ─────────────────────────────────────
DROP INDEX IF EXISTS areas_center_gix;

-- 3. Drop legacy columns
-- ──────────────────────
ALTER TABLE public.areas DROP COLUMN IF EXISTS center;
ALTER TABLE public.areas DROP COLUMN IF EXISTS radius_km;
