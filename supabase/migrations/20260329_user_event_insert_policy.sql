-- Allow authenticated users to insert events directly from the frontend.
-- The backend scraper uses the service role (bypasses RLS), so this policy
-- is specifically for user-submitted reports.
create policy "Authenticated users can insert events"
  on public.events
  for insert
  to authenticated
  with check (true);
