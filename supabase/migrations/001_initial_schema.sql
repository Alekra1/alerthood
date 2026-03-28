-- Extensions
create extension if not exists postgis with schema extensions;

-- Enums
create type public.threat_type as enum ('crime', 'infrastructure', 'disturbance', 'natural');
create type public.severity_level as enum ('low', 'medium', 'high', 'critical');
create type public.event_status as enum ('active', 'verified', 'resolved', 'dismissed');

-- Auto-update trigger
create or replace function public.bump_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end; $$;

-- Profiles (extends auth.users)
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text not null unique,
  display_name text,
  avatar_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Areas (neighborhoods — center + radius)
create table public.areas (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  city text not null,
  slug text not null unique,
  center extensions.geometry(Point, 4326) not null,
  radius_km numeric(6,2) not null default 5.0,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

-- User area subscriptions (max 2 for free tier, notification prefs inline)
create table public.user_area_subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  area_id uuid not null references public.areas(id) on delete cascade,
  label text not null default 'Home',
  notification_crime boolean not null default true,
  notification_infrastructure boolean not null default true,
  notification_natural boolean not null default true,
  notification_disturbance boolean not null default false,
  min_severity public.severity_level not null default 'medium',
  created_at timestamptz not null default now(),
  unique (user_id, area_id)
);

-- Events (core entity — map markers + feed items)
create table public.events (
  id uuid primary key default gen_random_uuid(),
  area_id uuid references public.areas(id) on delete set null,
  title text not null,
  description text,
  threat_type public.threat_type not null,
  severity public.severity_level not null default 'medium',
  status public.event_status not null default 'active',
  occurred_at timestamptz not null,
  location extensions.geometry(Point, 4326) not null,
  location_label text,
  source_type text not null default 'news',
  source_url text,
  relevance_score integer not null default 50,
  comment_count integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Notifications
create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  event_id uuid references public.events(id) on delete cascade,
  title text not null,
  body text,
  is_read boolean not null default false,
  created_at timestamptz not null default now()
);

-- Indexes
create index events_location_gix on public.events using gist(location);
create index events_area_id_idx on public.events(area_id);
create index events_occurred_at_idx on public.events(occurred_at desc);
create index events_threat_type_idx on public.events(threat_type);
create index events_status_idx on public.events(status);
create index areas_center_gix on public.areas using gist(center);
create index notifications_user_id_idx on public.notifications(user_id);
create index notifications_created_at_idx on public.notifications(created_at desc);

-- Triggers
create trigger profiles_bump before update on public.profiles
  for each row execute function public.bump_updated_at();
create trigger events_bump before update on public.events
  for each row execute function public.bump_updated_at();

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into public.profiles (id, username, display_name)
  values (new.id, new.email, split_part(new.email, '@', 1));
  return new;
end; $$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- RPC: get events within an area's radius (used by heatmap endpoint)
create or replace function public.events_in_area(target_area_id uuid)
returns table (
  id uuid,
  title text,
  threat_type public.threat_type,
  severity public.severity_level,
  occurred_at timestamptz,
  lat double precision,
  lng double precision,
  relevance_score integer
)
language sql stable as $$
  select
    e.id,
    e.title,
    e.threat_type,
    e.severity,
    e.occurred_at,
    extensions.st_y(e.location) as lat,
    extensions.st_x(e.location) as lng,
    e.relevance_score
  from public.events e
  join public.areas a on a.id = target_area_id
  where e.status = 'active'
    and extensions.st_dwithin(
      e.location::extensions.geography,
      a.center::extensions.geography,
      a.radius_km * 1000  -- convert km to meters
    )
  order by e.occurred_at desc
  limit 500;
$$;

-- RLS Policies
alter table public.profiles enable row level security;
alter table public.events enable row level security;
alter table public.areas enable row level security;
alter table public.user_area_subscriptions enable row level security;
alter table public.notifications enable row level security;

-- Profiles: anyone can read, users update own
create policy "Profiles are viewable by everyone" on public.profiles for select using (true);
create policy "Users can update own profile" on public.profiles for update using (auth.uid() = id);

-- Areas: anyone can read
create policy "Areas are viewable by everyone" on public.areas for select using (true);

-- Events: anyone can read, service role inserts (scraper)
create policy "Events are viewable by everyone" on public.events for select using (true);
create policy "Service role can insert events" on public.events for insert with check (true);

-- Subscriptions: users manage own
create policy "Users can view own subscriptions" on public.user_area_subscriptions for select using (auth.uid() = user_id);
create policy "Users can insert own subscriptions" on public.user_area_subscriptions for insert with check (auth.uid() = user_id);
create policy "Users can update own subscriptions" on public.user_area_subscriptions for update using (auth.uid() = user_id);
create policy "Users can delete own subscriptions" on public.user_area_subscriptions for delete using (auth.uid() = user_id);

-- Notifications: users see own
create policy "Users can view own notifications" on public.notifications for select using (auth.uid() = user_id);
create policy "Users can update own notifications" on public.notifications for update using (auth.uid() = user_id);
