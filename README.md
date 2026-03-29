# AlertHood 🛡️

**Know before you go.** AlertHood is a safety-awareness mobile web app that shows you real-time and historical threat heatmaps for any area — so you can navigate your city with confidence.

---

## What It Does

- **Safety Heatmap** — map view with green→red overlay based on historical incident data, filterable by time of day
- **Live Threat Feed** — real-time incident cards scraped from news sources, police APIs, and disaster feeds
- **Area Monitoring** — subscribe to up to 2 areas (home + destination); get notified of threats nearby
- **Land & Know Briefing** — instant safety snapshot when you arrive somewhere new
- **Safe Routes** *(stretch)* — colored polyline routing through lower-risk corridors

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript + Vite + Tailwind |
| Maps | MapLibre GL JS + CartoDB Dark Matter tiles |
| Backend | FastAPI (Python 3.11) |
| Database | Supabase (Postgres + PostGIS + Auth + Realtime) |
| Deploy | Cloudflare Pages (frontend) + FastAPI Cloud (backend) |

---

## Project Structure

```
alerthood/
├── frontend/          # React SPA (Vite)
│   └── src/
│       ├── pages/     # MapPage, FeedPage, ProfilePage, AuthPage
│       ├── components/# UI components (map markers, cards, nav)
│       ├── hooks/     # useAuth, useEvents, useAreas, useProfile
│       └── context/   # Auth context
├── backend/           # FastAPI app
│   ├── main.py        # App entrypoint, scheduler, CORS
│   ├── auth.py        # JWT verification (Supabase)
│   ├── routers/       # API route handlers
│   └── services/      # Scrapers, scoring, geocoding, routing
│       ├── scraper.py          # GDELT scraper (global, 15min)
│       ├── bg_news_scraper.py  # Bulgarian news scraper
│       ├── uk_police_scraper.py
│       ├── gnews_scraper.py
│       ├── emsc_scraper.py     # Seismic events
│       ├── gdacs_scraper.py    # Global disaster alerts
│       ├── meteoalarm_scraper.py
│       ├── ai_extractor.py     # LLM incident extraction
│       ├── safety_score.py     # Area risk scoring
│       ├── geocoding.py        # Location resolution
│       └── route_engine.py     # Safe route calculation
├── supabase/          # DB migrations
├── design/            # Design mockups + system spec
├── tasks/             # todo.md (task tracker)
└── DEPLOY.md          # Deployment runbook
```

---

## Local Development

### Backend

```bash
cd backend
cp .env.example .env  # fill in real values
uv sync
uv run fastapi dev    # http://localhost:8000
```

### Frontend

```bash
cd frontend
cp .env.example .env  # fill in real values
npm install
npm run dev           # http://localhost:5173
```

### Environment Variables

**Backend (`.env`)**

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Service role key (never expose to frontend) |
| `SUPABASE_JWT_SECRET` | JWT secret from Supabase settings |
| `CORS_ORIGINS` | JSON array of allowed frontend origins |
| `SCRAPER_INTERVAL_MINUTES` | How often scrapers run (default: 15) |

**Frontend (`.env`)**

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend URL |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon/public key |

---

## Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/events/heatmap` | Heatmap cells with weights by time bucket |
| `POST` | `/api/events` | Create a new threat event (authenticated) |
| `POST` | `/api/areas/subscribe` | Subscribe to an area (max 2) |
| `PATCH` | `/api/subscriptions/{id}/notifications` | Update notification preferences |
| `GET` | `/api/briefing` | Instant area safety briefing *(in progress)* |

Frontend reads (events feed, profile, subscriptions) go directly to Supabase via the JS client — FastAPI only handles writes and business logic.

---

## Deploy

See [DEPLOY.md](./DEPLOY.md) for the full runbook. Short version:

```bash
# Backend → FastAPI Cloud
cd backend && uv run fastapi deploy

# Frontend → Cloudflare Pages (auto via GitHub Actions on push to main)
```

---

## Design System

Neo-brutalist aesthetic — hard shadows, thick borders, no smooth animations. See [`design/alerthood_neo_noir/DESIGN.md`](./design/alerthood_neo_noir/DESIGN.md) for the full spec.

- **Fonts:** Space Grotesk (headlines) / Inter (body)
- **Shadows:** `4px 4px 0px #000000` — hard only, never blurred
- **Borders:** 2–3px black
- **Transitions:** 0.1s or none

---

## Status

See [`tasks/todo.md`](./tasks/todo.md) for the current task board.

- ✅ Backend API + scrapers (GDELT, BG news, UK Police, GDACS, EMSC, MeteoAlarm)
- ✅ Frontend scaffold + all pages + mock data
- ✅ Auth (email/password + Google OAuth)
- ✅ CI/CD (GitHub Actions → Cloudflare Pages)
- 🔲 Wire frontend to real Supabase data (replace mocks)
- 🔲 Heatmap layer on map
- 🔲 Land & Know briefing endpoint
- 🔲 Area subscription UI flow
