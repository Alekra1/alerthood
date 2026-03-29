-- Batch UPDATE-only RPC for safety scores.
-- Unlike upsert, this never tries to INSERT rows, so it won't fail on NOT NULL
-- constraints for columns we don't own (e.g. `name`).
CREATE OR REPLACE FUNCTION public.batch_update_area_scores(
  updates jsonb  -- array of {id, crime_count, crime_rate_per_km2, safety_score, safety_color, score_updated_at}
)
RETURNS integer  -- number of rows updated
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
  upd     jsonb;
  updated integer := 0;
BEGIN
  FOR upd IN SELECT * FROM jsonb_array_elements(updates)
  LOOP
    UPDATE public.areas
    SET
      crime_count        = (upd->>'crime_count')::integer,
      crime_rate_per_km2 = (upd->>'crime_rate_per_km2')::numeric,
      safety_score       = (upd->>'safety_score')::numeric,
      safety_color       = upd->>'safety_color',
      score_updated_at   = (upd->>'score_updated_at')::timestamptz
    WHERE id = (upd->>'id')::uuid;

    IF FOUND THEN
      updated := updated + 1;
    END IF;
  END LOOP;

  RETURN updated;
END;
$$;

GRANT EXECUTE ON FUNCTION public.batch_update_area_scores(jsonb) TO anon, authenticated, service_role;
