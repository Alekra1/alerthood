-- Update handle_new_user to read username/display_name from signup metadata
-- instead of using the email address
CREATE OR REPLACE FUNCTION public.handle_new_user() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
begin
  insert into public.profiles (id, email, username, display_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'username', new.email),
    coalesce(nullif(new.raw_user_meta_data->>'display_name', ''), split_part(new.email, '@', 1))
  );
  return new;
end; $$;

-- Clean up the test rows with email-as-username
DELETE FROM public.profiles WHERE username LIKE '%@%';
