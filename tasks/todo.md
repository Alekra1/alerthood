# AlertHood Hackathon Implementation Plan

## Context

AlertHood is a neighborhood safety app showing safe/unsafe areas on a heatmap, with a threat feed and user profiles. The project was reset to "start from beginning" — only design mockups (HTML/Tailwind) exist. We need to build the full MVP for a 3-person hackathon team with clear parallel workstreams.

**Tech stack:** React + TypeScript + Vite + Tailwind (frontend), FastAPI + Python (backend), Supabase (Postgres + PostGIS + Auth + Realtime), MapLibre GL JS (maps, CartoDB Dark Matter tiles — free, no API key).

**Architecture:** "Thin API + Supabase Direct" — reads via Supabase JS client (including realtime), writes via FastAPI for business logic.

---

## Phase 0: Scaffold (All 3 people, ~30 min)

Everyone sets up the monorepo together so parallel work can begin.

### Folder Structure
```
alerthood/
  frontend/
    src/
      main.tsx, App.tsx
      lib/          → supabase.ts, api.ts, types.ts, constants.ts
      components/
        layout/     → AppShell.tsx, TopAppBar.tsx, BottomNav.tsx
        shared/     → ThreatCard.tsx, CategoryBadge.tsx, BrutalistButton.tsx
        map/        → MapContainer.tsx, HeatmapLayer.tsx, EventMarkers.tsx, MapBottomSheet.tsx
        feed/       → FeedList.tsx, FeedFilters.tsx, AreaSelector.tsx, ActiveThreatBanner.tsx
        profile/    → ProfileHeader.tsx, MonitoredAreas.tsx, AreaCard.tsx
      pages/        → MapPage.tsx, FeedPage.tsx, ProfilePage.tsx, AuthPage.tsx
      hooks/        → useEvents.ts, useAreas.ts, useProfile.ts, useAuth.ts
  backend/
    main.py, config.py, auth.py
    routers/        → events.py, areas.py, profile.py
    services/       → scraper.py, safety_score.py
    models/         → schemas.py
  supabase/
    migrations/001_initial_schema.sql
    seed.sql
```

### Setup Tasks
- **Person A:** `npm create vite@latest frontend -- --template react-ts` + Tailwind + copy design tokens from mockups
- **Person B:** `mkdir backend` + FastAPI skeleton with CORS
- **Person C:** Create Supabase project, write & apply migration, configure env vars

---

## Phase 1: Foundation (Hours 1–3, fully parallel)

### Person A: Frontend Shell + Map
1. `AppShell.tsx` with `TopAppBar` + `BottomNav` (match mockup exactly — `#131313` bg, `border-b-2 border-black`, hard shadows)
2. React Router: `/map`, `/feed`, `/profile` routes
3. MapLibre GL with CartoDB Dark Matter tiles: `https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json`
4. `EventMarkers.tsx` — hardcoded data first, wire to Supabase later
5. `MapBottomSheet.tsx` — alert detail card on marker tap (impact bar, CRIME badge, severity metrics)
6. Marker pulse animation (`@keyframes pulse`, scale 1→2.5)

**No blockers** — uses mock data until DB is ready.

### Person B: FastAPI + News Scraper
1. `main.py` with CORS middleware
2. `auth.py` — JWT verification against Supabase JWT secret (`python-jose`)
3. `config.py` — Pydantic Settings from `.env`
4. `POST /api/events` — create event endpoint
5. `services/scraper.py` — scrape 2–3 local news RSS feeds with `httpx` + `BeautifulSoup`, categorize by keywords, extract location, insert into `events` table
6. Background task: run scraper every 15 min via `asyncio`

**No blockers** — writes directly to Supabase via service key.

### Person C: Database + Auth + Seed Data
1. Write & apply MVP migration (schema below)
2. Set up RLS policies (profiles: read all/update own; events: read all; subscriptions: own only)
3. Configure Supabase Auth (email/password)
4. `seed.sql` with 50+ realistic events across 2 demo areas, varied threat types/severity/times
5. Enable Supabase Realtime on `events` table
6. Generate `types.ts` via `supabase gen types typescript`
7. Create `frontend/src/lib/supabase.ts` client init

**Handoff at ~1.5 hours:** C gives A the `types.ts` + `supabase.ts`, then C moves to help with Profile page.

---

## MVP Database Schema

```sql
create extension if not exists postgis with schema extensions;

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

-- Areas (neighborhoods — center + radius, not polygons)
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
create index areas_center_gix on public.areas using gist(center);
create index notifications_user_id_idx on public.notifications(user_id);

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
```

---

## API Contracts (defined upfront so FE/BE work in parallel)

### `GET /api/events/heatmap?area_id={uuid}&time_bucket={morning|afternoon|evening|night|all}`
```json
{ "cells": [{ "lat": 41.88, "lng": -87.63, "weight": 0.7, "event_count": 5 }], "time_bucket": "evening" }
```

### `POST /api/events` (authenticated)
```json
{ "title": "...", "threat_type": "crime", "severity": "high", "occurred_at": "ISO8601", "lat": 41.88, "lng": -87.63, "location_label": "Main & 5th", "source_type": "news" }
```

### `POST /api/areas/subscribe` (authenticated, enforces 2-area limit)
```json
{ "area_id": "uuid", "label": "Home" }
```

### `PATCH /api/subscriptions/{id}/notifications` (authenticated)
```json
{ "notification_crime": true, "min_severity": "high" }
```

### Frontend Direct Reads (Supabase JS, bypass FastAPI)
- Events for feed: `supabase.from('events').select('*').eq('area_id', id).order('occurred_at', {ascending: false})`
- Realtime: `supabase.channel('events').on('postgres_changes', {event: 'INSERT', table: 'events'}, handler)`
- Profile: `supabase.from('profiles').select('*').eq('id', userId).single()`
- Subscriptions: `supabase.from('user_area_subscriptions').select('*, areas(*)').eq('user_id', userId)`

---

## Phase 2: Core Features (Hours 3–6, parallel)

### Person A: Heatmap Layer + Feed Page
1. MapLibre heatmap layer using `/api/events/heatmap` data — green→yellow→red gradient
2. Time-of-day toggle on map (morning/afternoon/evening/night)
3. **Feed page:** `ActiveThreatBanner.tsx`, `AreaSelector.tsx`, `FeedFilters.tsx` (ALL/CRIME/UTILITY/NATURAL/DISTURBANCE), `FeedList.tsx` with `ThreatCard.tsx`
4. Wire feed to Supabase realtime — new events appear at top without refresh

### Person B: Heatmap Endpoint + Subscription API
1. `GET /api/events/heatmap` — grid area into cells, weight events by severity + recency (exponential decay), filter by time_bucket (morning=6-12, afternoon=12-18, evening=18-24, night=0-6)
2. `POST /api/areas/subscribe` with 2-area limit
3. `PATCH /api/subscriptions/{id}/notifications`
4. Harden scraper with 2 working RSS sources

### Person C: Auth Flow + Profile Page
1. `AuthPage.tsx` — email/password login/signup via Supabase Auth (neo-brutalist styled inputs)
2. `useAuth.ts` hook with `supabase.auth.onAuthStateChange`
3. Auth guard on routes — redirect to `/auth` if not logged in
4. `ProfilePage.tsx`: `ProfileHeader.tsx`, `MonitoredAreas.tsx` with notification toggles
5. Wire toggle changes to `PATCH /api/subscriptions/{id}/notifications`

---

## Phase 3: Polish + Integration (Hours 6–8)

### Person A: Route Builder (stretch) + Map Polish
1. **(Stretch)** Safe route display — A* over heatmap grid or colored line between two points
2. **(Stretch)** Business suggestions along route (static icons)
3. Smooth zoom-to-marker, popup positioning, two-tab realtime test

### Person B: Notifications + Demo Data
1. Background task: on new event insert → find affected subscribers → insert notifications
2. Polish `seed.sql` with 50+ visually compelling events
3. Error handling on all endpoints

### Person C: Integration + Demo Prep
1. Notification bell in `TopAppBar` with unread count badge
2. "VIEW MAP" on feed cards → navigate to Map centered on that event
3. Full flow test: signup → subscribe → see events on map + feed → toggle notifications
4. Deploy: Vite → Vercel/Netlify, FastAPI → Railway/Fly.io (or local for demo)

---

## Critical Files to Reference

| File | Purpose |
|------|---------|
| `design/alerthood_neo_noir/DESIGN.md` | Design system spec — all FE work must follow |
| `design/alerthood_map_view/code.html` | Map mockup with exact Tailwind classes + color tokens |
| `design/alerthood_threat_feed/code.html` | Feed mockup with card layouts, filters |
| `design/alerthood_profile_tab/code.html` | Profile mockup with areas, toggles |

### Design Non-Negotiables
- Hard shadows only: `shadow-[4px_4px_0px_#000000]`, never blurred
- Borders: 2-3px black, never 1px
- Active state: `active:translate-x-[2px] active:translate-y-[2px] active:shadow-none`
- Impact bar: 6px vertical left-edge on threat cards, colored by threat type
- Fonts: Space Grotesk (headlines), Inter (body)
- Transitions: `0.1s` or `0s` — no smooth animations
- Copy full Tailwind color config from mockup HTML files

---

## Verification

1. **Map:** Opens with CartoDB Dark Matter tiles, shows event markers with pulse animation, heatmap layer renders with time-of-day toggle
2. **Feed:** Shows categorized threat cards, filters work, new events appear in realtime
3. **Profile:** Login/signup works, monitored areas display, notification toggles persist
4. **Integration:** Tapping feed card → map centers on event; notification bell shows count
5. **Scraper:** New events from RSS appear on map + feed within 15 minutes
6. **Seed data:** Demo looks compelling with 50+ events across 2 neighborhoods
