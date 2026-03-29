-- Prevent duplicate notifications for the same user+event pair.
-- Scrapers may re-encounter the same event on consecutive runs; this
-- index lets the backend use ON CONFLICT DO NOTHING instead of a
-- separate pre-insert existence check.
create unique index if not exists notifications_user_event_udx
  on public.notifications (user_id, event_id)
  where event_id is not null;
