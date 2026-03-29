# AlertHood — What's Done & What's Left

## Context

**Tech stack:** React + TypeScript + Vite + Tailwind (frontend), FastAPI + Python (backend), Supabase (Postgres + PostGIS + Auth + Realtime), MapLibre GL JS (maps).

**Deploy:** Cloudflare Pages (frontend), FastAPI Cloud (backend), Supabase Cloud (database).

**Architecture:** "Thin API + Supabase Direct" — reads via Supabase JS client (including realtime), writes via FastAPI for business logic.

---

## ✅ Done

### Backend (PR #1 — merged)
- [x] FastAPI skeleton — `main.py` with CORS middleware
- [x] `auth.py` — JWT verification against Supabase JWT secret
- [x] `config.py` — Pydantic Settings from `.env`
- [x] `POST /api/events` — create event endpoint
- [x] `GET /api/events/heatmap` — heatmap endpoint with time buckets
- [x] `POST /api/areas/subscribe` — subscription with 2-area limit
- [x] `services/scraper.py` — GDELT scraper, area-matched, runs every 15min
- [x] `services/safety_score.py` — safety score calculator
- [x] Auto-notifications on event insert (DB trigger)
- [x] Seed data with global area coverage

### Frontend (PR #2 — merged)
- [x] Vite + React + TypeScript + Tailwind scaffold
- [x] `TopBar.tsx` + `BottomNav.tsx` layout
- [x] `MapView.tsx` with MapLibre GL + CartoDB Dark Matter tiles
- [x] `ThreatMarker.tsx` + `MonitoredZone.tsx` + `AlertBottomSheet.tsx`
- [x] `FeedView.tsx` + `ThreatCard.tsx` + `FilterBar.tsx` + `ActiveThreatBanner.tsx`
- [x] `ProfileView.tsx` + `MonitoredAreaCard.tsx` + `MetricsBento.tsx` + `BadgeGrid.tsx`
- [x] `MapPage.tsx`, `FeedPage.tsx`, `ProfilePage.tsx`
- [x] Mock data (`mock.ts`) for development

### Database (Supabase)
- [x] Migration applied — profiles, areas, events, subscriptions, notifications tables
- [x] PostGIS extension enabled
- [x] Indexes on location, area_id, occurred_at, threat_type
- [x] Auto-create profile trigger on signup
- [x] Auto-notification trigger on event insert
- [x] Seed data populated

---

## 🔲 TODO

### Dev 1 (Olexii) — Frontend Lead

**Auth & Account (HIGH PRIORITY — next up)**
- [x] `AuthPage.tsx` — email/password sign-up/sign-in UI (neo-brutalist styled)
- [x] Google OAuth sign-in button on AuthPage
- [x] Configure Google OAuth provider in Supabase (Google Cloud Console credentials)
- [x] `supabase.ts` — Supabase JS client init in frontend
- [x] `useAuth.ts` hook with `supabase.auth.onAuthStateChange`
- [x] Auth guard on routes — redirect to `/auth` if not logged in
- [x] Wire profile page to real user data

**Wire Frontend to Supabase (replace mock data)**
- [ ] `useEvents.ts` — fetch events from Supabase, replace mock data
- [ ] `useAreas.ts` — fetch areas from Supabase
- [ ] `useProfile.ts` — fetch user profile + subscriptions
- [ ] Wire feed to Supabase realtime — new events appear without refresh
- [ ] Wire map markers to real event data (scraper events have lat/lng/severity)

**Heatmap Layer**
- [ ] Leaflet heatmap layer using `/api/events/heatmap` — green→yellow→red gradient
- [ ] Time-of-day toggle on map (morning/afternoon/evening/night)

**"Land & Know" Briefing UI**
- [ ] Briefing UI component — push notification or bottom sheet on app open

**Integration**
- [ ] Full flow test: signup → subscribe → see events on map + feed → toggle notifications

---

### Dev 2 (You) — Backend + Deploy

**"Land & Know" Instant Briefing**
- [ ] `GET /api/briefing?lat=&lng=` — backend endpoint returning:
  - Current risk level of area
  - Events reported in last 24hrs nearby
  - One "watch out for" tip (pickpockets near market, avoid X street at night)
- [ ] Geofence trigger logic — detect when user arrives at new location

**Deploy (execute)**
- [ ] Run `fastapi deploy` on FastAPI Cloud (dev 1 has beta access)
- [ ] Connect GitHub repo to Cloudflare Pages, set env vars
- [ ] Post-deploy checklist (see DEPLOY.md)

**Stretch**
- [ ] Safe route display — colored polyline on map between two points

---

### Dev 3 (Egor) — Novice-Friendly Frontend

**Notifications UI**
- [x] Notification bell in `TopBar` with unread count badge
- [x] Notification list/dropdown

**Profile & Subscriptions**
- [ ] Area subscription flow — select/add monitored areas
- [x] Notification preference toggles wired to `PATCH /api/subscriptions/{id}/notifications`

**Integration**
- [x] "VIEW MAP" on feed cards → navigate to Map centered on that event

**Stretch**
- [ ] Business suggestions along route (static icons)

---

### ✅ Deploy (Done)
- [x] Frontend → Cloudflare Pages (wrangler.toml + GitHub Actions CD)
- [x] Backend → FastAPI Cloud (pyproject.toml + uv + DEPLOY.md guide)
- [x] CI/CD — GitHub Actions: ruff lint + frontend build on PRs, auto-deploy on push to main

---

## API Contracts

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

## Design Non-Negotiables

- Hard shadows only: `shadow-[4px_4px_0px_#000000]`, never blurred
- Borders: 2-3px black, never 1px
- Active state: `active:translate-x-[2px] active:translate-y-[2px] active:shadow-none`
- Impact bar: 6px vertical left-edge on threat cards, colored by threat type
- Fonts: Space Grotesk (headlines), Inter (body)
- Transitions: `0.1s` or `0s` — no smooth animations

## Critical Files to Reference

| File | Purpose |
|------|---------|
| `design/alerthood_neo_noir/DESIGN.md` | Design system spec — all FE work must follow |
| `design/alerthood_map_view/code.html` | Map mockup with exact Tailwind classes + color tokens |
| `design/alerthood_threat_feed/code.html` | Feed mockup with card layouts, filters |
| `design/alerthood_profile_tab/code.html` | Profile mockup with areas, toggles |
