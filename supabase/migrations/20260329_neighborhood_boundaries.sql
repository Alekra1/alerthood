-- Add area_type enum
DO $$ BEGIN
  CREATE TYPE public.area_type AS ENUM ('city', 'neighborhood');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Add new columns to areas
ALTER TABLE public.areas
  ADD COLUMN IF NOT EXISTS area_type public.area_type NOT NULL DEFAULT 'neighborhood',
  ADD COLUMN IF NOT EXISTS parent_id uuid REFERENCES public.areas(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS osm_id bigint,
  ADD COLUMN IF NOT EXISTS country_code char(2),
  ADD COLUMN IF NOT EXISTS boundary extensions.geometry(MultiPolygon, 4326),
  ADD COLUMN IF NOT EXISTS safety_color text NOT NULL DEFAULT '#22c55e';

-- Unique constraint on osm_id for dedup (partial — only non-null)
CREATE UNIQUE INDEX IF NOT EXISTS areas_osm_id_unique
  ON public.areas (osm_id) WHERE osm_id IS NOT NULL;

-- GiST index on boundary for spatial queries
CREATE INDEX IF NOT EXISTS areas_boundary_gix
  ON public.areas USING gist(boundary) WHERE boundary IS NOT NULL;

-- Index on parent_id for city → neighborhood lookups
CREATE INDEX IF NOT EXISTS areas_parent_id_idx
  ON public.areas (parent_id) WHERE parent_id IS NOT NULL;

-- Backfill existing areas: convert center+radius to circle polygon
-- This keeps ST_Contains queries working during transition
UPDATE public.areas
SET boundary = extensions.st_multi(
  extensions.st_buffer(center::extensions.geography, radius_km * 1000)::extensions.geometry
)
WHERE boundary IS NULL AND center IS NOT NULL;
