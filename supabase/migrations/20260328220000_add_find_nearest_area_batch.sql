-- Batch version of find_nearest_area: accepts a JSONB array of {lat, lng} objects
-- and returns (idx, area_id) pairs, replacing N individual RPC calls with one.
create or replace function public.find_nearest_area_batch(
  points jsonb  -- e.g. [{"lat": 51.5, "lng": -0.1}, ...]
)
returns table (
  idx integer,
  area_id uuid
) language sql stable as $$
  select
    (p.ordinality - 1)::integer as idx,
    (
      select a.id
      from public.areas a
      where a.is_active = true
        and extensions.st_dwithin(
          a.center::extensions.geography,
          extensions.st_point(
            (p.value->>'lng')::double precision,
            (p.value->>'lat')::double precision
          )::extensions.geography,
          a.radius_km * 1000
        )
      order by extensions.st_distance(
        a.center::extensions.geography,
        extensions.st_point(
          (p.value->>'lng')::double precision,
          (p.value->>'lat')::double precision
        )::extensions.geography
      )
      limit 1
    ) as area_id
  from jsonb_array_elements(points) with ordinality as p(value, ordinality)
$$;
