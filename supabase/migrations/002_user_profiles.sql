-- =============================================================================
-- 002_user_profiles.sql
-- Extends profiles with karma, streaks, badges, and monitored area
-- notification preferences.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- events.author_id
-- Needed to attribute votes to a profile for karma.
-- ---------------------------------------------------------------------------
alter table public.events
  add column author_id uuid references public.profiles(id) on delete set null;

create index events_author_id_idx on public.events(author_id);


-- ---------------------------------------------------------------------------
-- profiles — gamification columns
-- ---------------------------------------------------------------------------
alter table public.profiles
  add column karma            integer      not null default 0,
  add column current_streak   integer      not null default 0,
  add column longest_streak   integer      not null default 0,
  add column last_active_date date;


-- ---------------------------------------------------------------------------
-- event_votes — upvote (+1) / downvote (-1) per user per event
-- ---------------------------------------------------------------------------
create table public.event_votes (
  id         uuid        primary key default gen_random_uuid(),
  user_id    uuid        not null references public.profiles(id) on delete cascade,
  event_id   uuid        not null references public.events(id)   on delete cascade,
  vote       smallint    not null check (vote in (-1, 1)),
  created_at timestamptz not null default now(),
  unique (user_id, event_id)
);

create index event_votes_event_id_idx on public.event_votes(event_id);
create index event_votes_user_id_idx  on public.event_votes(user_id);


-- ---------------------------------------------------------------------------
-- badge_definitions — static catalogue (populated via seed)
-- ---------------------------------------------------------------------------
create table public.badge_definitions (
  id          text        primary key,          -- e.g. 'first_report', 'streak_7'
  name        text        not null,
  description text        not null,
  icon        text        not null,             -- emoji or icon key
  category    text        not null default 'general',
  threshold   integer,                          -- numeric goal that unlocks it (null = manual award)
  created_at  timestamptz not null default now()
);


-- ---------------------------------------------------------------------------
-- user_badges — badges earned by each user
-- ---------------------------------------------------------------------------
create table public.user_badges (
  id        uuid        primary key default gen_random_uuid(),
  user_id   uuid        not null references public.profiles(id)          on delete cascade,
  badge_id  text        not null references public.badge_definitions(id) on delete cascade,
  earned_at timestamptz not null default now(),
  unique (user_id, badge_id)
);

create index user_badges_user_id_idx on public.user_badges(user_id);


-- ---------------------------------------------------------------------------
-- user_area_subscriptions — WIP richer notification preferences
-- Existing boolean columns stay; jsonb added for future use.
-- ---------------------------------------------------------------------------
alter table public.user_area_subscriptions
  add column notification_preferences jsonb not null default '{}';


-- ===========================================================================
-- RLS
-- ===========================================================================
alter table public.event_votes       enable row level security;
alter table public.badge_definitions enable row level security;
alter table public.user_badges       enable row level security;

-- event_votes
create policy "Anyone can read votes"
  on public.event_votes for select using (true);
create policy "Users insert own votes"
  on public.event_votes for insert with check (auth.uid() = user_id);
create policy "Users update own votes"
  on public.event_votes for update using (auth.uid() = user_id);
create policy "Users delete own votes"
  on public.event_votes for delete using (auth.uid() = user_id);

-- badge_definitions — public read-only catalogue
create policy "Anyone can read badge definitions"
  on public.badge_definitions for select using (true);

-- user_badges
create policy "Anyone can read user badges"
  on public.user_badges for select using (true);
