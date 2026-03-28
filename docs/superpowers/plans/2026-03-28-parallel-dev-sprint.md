# AlertHood Parallel Dev Sprint — Status

**Goal:** Ship MVP with auth, live data, heatmap, safe routing, geolocation, notifications.
**Stack:** React 18 + TS + Vite + Tailwind + Leaflet | FastAPI + Python | Supabase (Postgres + PostGIS + Auth + Realtime)

---

## Dev 1 (Olexii) — Frontend: Auth + Live Data + Route UI

### Auth & Account
- [ ] `AuthPage.tsx` — email/password + Google OAuth sign-in
- [ ] `supabase.ts` — Supabase JS client init
- [ ] `useAuth.ts` hook with `supabase.auth.onAuthStateChange`
- [ ] Auth guard on routes — redirect to `/auth` if not logged in
- [ ] Configure Google OAuth in Supabase dashboard

### Wire Frontend to Real Data
- [ ] `useEvents.ts` — replace mock data with Supabase reads
- [ ] `useAreas.ts` — fetch areas + subscriptions
- [ ] `useProfile.ts` — fetch user profile
- [ ] Wire feed to Supabase realtime
- [ ] Wire map markers to real event data (scrapers populate DB with lat/lng/severity)

### Route Planner UI
- [ ] `RoutePage.tsx` + `RouteView.tsx` — origin/dest input, call `POST /api/routes/safe`
- [ ] `RouteBottomSheet.tsx` — show waypoints + Google Maps link
- [ ] Route display on map (polyline from waypoints)

### Heatmap + Notifications
- [ ] Leaflet heatmap layer using `/api/events/heatmap` — green→yellow→red
- [ ] Time-of-day toggle (morning/afternoon/evening/night)
- [ ] `NotificationBell.tsx` in TopBar with unread count
- [ ] Notification dropdown/list

---

## Dev 2 (You) — Backend: Routes + Data + Scores + Deploy

### ✅ Done
- [x] `POST /api/routes/safe` — waypoint avoidance + Google Maps URL export
- [x] `GET /api/areas/detect?lat=&lng=` — GPS area detection via PostGIS
- [x] `GET /api/scores/neighborhood/{area_id}` + `POST /api/scores/refresh`
- [x] ACLED historical import pipeline (blocked on account approval)
- [x] 5 scrapers: GDELT, USGS, NWS, UK Police, OpenWeather (parallel, deduped)
- [x] Auth on all endpoints (ES256 JWKS verification)
- [x] Deployment config: Cloudflare Pages + FastAPI Cloud + GitHub Actions CI/CD
- [x] `uv` package management
- [x] Code review fixes: auth, error handling, math, type safety, dedup

---

## Dev 3 — Backend: Scraper + Safety Scores

### ✅ Done (merged to main in PR #1)
- [x] FastAPI skeleton + CORS + JWT auth
- [x] `POST /api/events` + `GET /api/events/heatmap`
- [x] `POST /api/areas/subscribe` (2-area limit)
- [x] GDELT scraper (15min interval)
- [x] Safety score calculator
- [x] DB triggers: auto-notifications on event insert
- [x] Seed data with global area coverage

---

## New Features (Backlog)

### "Land & Know" Instant Briefing — The Hook
Auto-generated briefing when traveler arrives at new location:
- [ ] `GET /api/briefing?lat=&lng=` — risk level + last 24h events + "watch out for" tip
- [ ] Briefing UI component (push notification or bottom sheet)
- [ ] Geofence trigger on location change

### Integration
- [ ] "VIEW MAP" on feed cards → navigate to map centered on event
- [ ] Full flow test: signup → subscribe → see events → toggle notifications

### Stretch
- [ ] Business suggestions along safe route
- [ ] User-submitted threats in feed
