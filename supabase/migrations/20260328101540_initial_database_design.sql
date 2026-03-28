create schema if not exists extensions;

create extension if not exists pgcrypto with schema extensions;
create extension if not exists postgis with schema extensions;

create type public.threat_type as enum (
  'crime',
  'utility_outage',
  'water_shortage',
  'traffic',
  'fire',
  'medical',
  'weather',
  'suspicious_activity',
  'other'
);

create type public.severity_level as enum (
  'low',
  'medium',
  'high',
  'critical'
);

create type public.event_status as enum (
  'reported',
  'under_review',
  'verified',
  'resolved',
  'dismissed'
);

create type public.relevance_vote as enum (
  'relevant',
  'irrelevant'
);

create type public.verification_vote as enum (
  'confirmed',
  'false',
  'unsure'
);

create type public.location_precision as enum (
  'building',
  'street',
  'block',
  'neighborhood'
);

create type public.media_kind as enum (
  'photo',
  'video'
);

create type public.moderation_status as enum (
  'pending',
  'approved',
  'rejected'
);

create type public.notification_channel as enum (
  'push',
  'email',
  'sms'
);

create or replace function public.bump_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text not null unique,
  display_name text,
  avatar_url text,
  karma integer not null default 0,
  trust_score numeric(5,2) not null default 0,
  streak_days integer not null default 0,
  badges jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create table public.areas (
  id uuid primary key default extensions.gen_random_uuid(),
  name text not null,
  city text not null,
  country_code text not null,
  slug text not null unique,
  boundary extensions.geometry(MultiPolygon, 4326),
  center extensions.geometry(Point, 4326),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table public.user_area_subscriptions (
  id uuid primary key default extensions.gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  area_id uuid not null references public.areas(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (user_id, area_id)
);

create table public.user_notification_preferences (
  id uuid primary key default extensions.gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  area_id uuid not null references public.areas(id) on delete cascade,
  threat_types public.threat_type[] not null default '{}'::public.threat_type[],
  min_severity public.severity_level not null default 'medium',
  channels public.notification_channel[] not null default '{push}'::public.notification_channel[],
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  unique (user_id, area_id)
);

create table public.events (
  id uuid primary key default extensions.gen_random_uuid(),
  area_id uuid references public.areas(id) on delete set null,
  reporter_id uuid references public.profiles(id) on delete set null,
  title text not null,
  description text,
  threat_type public.threat_type not null,
  severity public.severity_level not null default 'medium',
  status public.event_status not null default 'reported',
  occurred_at timestamptz not null,
  approx_center extensions.geometry(Point, 4326) not null,
  approx_radius_m integer not null check (approx_radius_m >= 25),
  location_precision public.location_precision not null default 'block',
  location_label text,
  source_type text not null default 'user',
  source_url text,
  is_anonymous boolean not null default false,
  relevance_score numeric(8,2) not null default 0,
  verification_score numeric(8,2) not null default 0,
  comment_count integer not null default 0,
  contains_personal_data boolean not null default false,
  retention_until timestamptz,
  deleted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.event_media (
  id uuid primary key default extensions.gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  uploader_id uuid references public.profiles(id) on delete set null,
  kind public.media_kind not null,
  storage_path text not null unique,
  mime_type text not null,
  file_size_bytes bigint,
  width integer,
  height integer,
  duration_seconds numeric,
  captured_at timestamptz,
  is_primary boolean not null default false,
  moderation_status public.moderation_status not null default 'pending',
  metadata_stripped boolean not null default false,
  contains_faces boolean,
  contains_license_plates boolean,
  retention_until timestamptz,
  deleted_at timestamptz,
  created_at timestamptz not null default now()
);

create table public.event_relevance_votes (
  event_id uuid not null references public.events(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  vote public.relevance_vote not null,
  created_at timestamptz not null default now(),
  primary key (event_id, user_id)
);

create table public.event_verification_votes (
  event_id uuid not null references public.events(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  vote public.verification_vote not null,
  created_at timestamptz not null default now(),
  primary key (event_id, user_id)
);

create table public.posts (
  id uuid primary key default extensions.gen_random_uuid(),
  area_id uuid references public.areas(id) on delete set null,
  author_id uuid references public.profiles(id) on delete set null,
  linked_event_id uuid references public.events(id) on delete set null,
  title text not null,
  body text not null,
  threat_type public.threat_type,
  severity public.severity_level,
  occurred_at timestamptz,
  score integer not null default 0,
  comment_count integer not null default 0,
  is_deleted boolean not null default false,
  deleted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.post_comments (
  id uuid primary key default extensions.gen_random_uuid(),
  post_id uuid not null references public.posts(id) on delete cascade,
  author_id uuid references public.profiles(id) on delete set null,
  parent_comment_id uuid references public.post_comments(id) on delete cascade,
  body text not null,
  score integer not null default 0,
  is_deleted boolean not null default false,
  deleted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.post_votes (
  post_id uuid not null references public.posts(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  value smallint not null check (value in (-1, 1)),
  created_at timestamptz not null default now(),
  primary key (post_id, user_id)
);

create table public.comment_votes (
  comment_id uuid not null references public.post_comments(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  value smallint not null check (value in (-1, 1)),
  created_at timestamptz not null default now(),
  primary key (comment_id, user_id)
);

create table public.notifications (
  id uuid primary key default extensions.gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  event_id uuid references public.events(id) on delete cascade,
  post_id uuid references public.posts(id) on delete cascade,
  channel public.notification_channel not null,
  payload jsonb not null,
  sent_at timestamptz,
  created_at timestamptz not null default now()
);

create index areas_boundary_gix on public.areas using gist (boundary);
create index areas_center_gix on public.areas using gist (center);

create index events_area_id_idx on public.events (area_id);
create index events_reporter_id_idx on public.events (reporter_id);
create index events_occurred_at_idx on public.events (occurred_at desc);
create index events_threat_type_idx on public.events (threat_type);
create index events_status_idx on public.events (status);
create index events_severity_idx on public.events (severity);
create index events_approx_center_gix on public.events using gist (approx_center);

create index event_media_event_id_idx on public.event_media (event_id);
create index event_media_uploader_id_idx on public.event_media (uploader_id);
create index event_media_moderation_status_idx on public.event_media (moderation_status);

create index event_relevance_votes_user_id_idx on public.event_relevance_votes (user_id);
create index event_verification_votes_user_id_idx on public.event_verification_votes (user_id);

create index posts_area_id_idx on public.posts (area_id);
create index posts_author_id_idx on public.posts (author_id);
create index posts_linked_event_id_idx on public.posts (linked_event_id);
create index posts_created_at_idx on public.posts (created_at desc);
create index posts_occurred_at_idx on public.posts (occurred_at desc);

create index post_comments_post_id_idx on public.post_comments (post_id);
create index post_comments_author_id_idx on public.post_comments (author_id);
create index post_comments_parent_comment_id_idx on public.post_comments (parent_comment_id);
create index post_comments_created_at_idx on public.post_comments (created_at asc);

create index notifications_user_id_idx on public.notifications (user_id);
create index notifications_created_at_idx on public.notifications (created_at desc);

create trigger profiles_bump_updated_at
before update on public.profiles
for each row
execute function public.bump_updated_at();

create trigger events_bump_updated_at
before update on public.events
for each row
execute function public.bump_updated_at();

create trigger posts_bump_updated_at
before update on public.posts
for each row
execute function public.bump_updated_at();

create trigger post_comments_bump_updated_at
before update on public.post_comments
for each row
execute function public.bump_updated_at();

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'event-media',
  'event-media',
  false,
  52428800,
  array[
    'image/jpeg',
    'image/png',
    'image/webp',
    'video/mp4',
    'video/quicktime'
  ]
)
on conflict (id) do nothing;
