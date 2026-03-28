# AlertHood Deployment Guide

## Architecture

```
[Cloudflare Pages] → frontend (React SPA)
[FastAPI Cloud]    → backend (FastAPI + scrapers)
[Supabase Cloud]   → database (Postgres + PostGIS)
```

---

## 1. Backend — FastAPI Cloud

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- FastAPI Cloud private beta access

### Deploy

```bash
cd backend
uv sync
uv run fastapi login
uv run fastapi deploy
```

### Environment Variables (set in FastAPI Cloud dashboard)

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Service role key (NOT anon key) | `eyJ...` |
| `SUPABASE_JWT_SECRET` | JWT secret from Supabase settings (legacy, unused with JWKS) | `your-jwt-secret` |
| `CORS_ORIGINS` | JSON array of allowed origins | `["https://alerthood.pages.dev"]` |
| `SCRAPER_INTERVAL_MINUTES` | Scrape cycle interval | `15` |
| `DEMO_CITY` | Default city for scrapers | `Chicago` |
| `OPENWEATHER_API_KEY` | OpenWeatherMap API key | `abc123...` |
| `ACLED_API_KEY` | ACLED API key (optional) | `` |
| `ACLED_API_EMAIL` | ACLED account email (optional) | `` |

### Health Check
```
GET https://<your-app>.fastapicloud.dev/health
→ {"status": "ok"}
```

---

## 2. Frontend — Cloudflare Pages

### Option A: GitHub Integration (recommended)
1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com) → Pages → Create a project
2. Connect the `Alekra1/alerthood` GitHub repo
3. Configure build:
   - **Build command:** `npm run build`
   - **Build output directory:** `frontend/dist`
   - **Root directory:** `frontend`
4. Add environment variables:
   - `VITE_API_URL` = `https://<your-app>.fastapicloud.dev`
   - `VITE_SUPABASE_URL` = `https://xxx.supabase.co`
   - `VITE_SUPABASE_ANON_KEY` = your Supabase anon/public key

### Option B: CI/CD via GitHub Actions
Already configured in `.github/workflows/deploy-frontend.yml`.

Add these GitHub repo secrets:
- `CLOUDFLARE_API_TOKEN` — from Cloudflare dashboard
- `CLOUDFLARE_ACCOUNT_ID` — from Cloudflare dashboard
- `VITE_API_URL` — backend URL
- `VITE_SUPABASE_URL` — Supabase project URL
- `VITE_SUPABASE_ANON_KEY` — Supabase anon key

---

## 3. Supabase

Already deployed at `https://zevkpeatbfqeqiijfmum.supabase.co`.

Migrations are in `supabase/migrations/`. Apply via Supabase dashboard or CLI:
```bash
supabase db push
```

### Keys to collect from Supabase dashboard (Settings → API):
- **Project URL** → `SUPABASE_URL` / `VITE_SUPABASE_URL`
- **anon public key** → `VITE_SUPABASE_ANON_KEY` (frontend)
- **service_role key** → `SUPABASE_SERVICE_KEY` (backend only, never expose to frontend)
- **JWT Secret** (Settings → API → JWT Settings) → `SUPABASE_JWT_SECRET`

---

## 4. Post-Deploy Checklist

- [ ] Backend `/health` returns `{"status": "ok"}`
- [ ] Frontend loads at `https://alerthood.pages.dev`
- [ ] CORS: frontend can call backend without errors
- [ ] Scraper loop is running (check backend logs for "Running all scrapers...")
- [ ] Supabase connection works (scores endpoint returns data)

---

## 5. CI/CD

### `.github/workflows/ci.yml`
Runs on every PR and push to `main`:
- Backend: `ruff check` (Python linting)
- Frontend: `npm run build` (TypeScript + Vite build check)

### `.github/workflows/deploy-frontend.yml`
Auto-deploys frontend to Cloudflare Pages on push to `main` (only when `frontend/**` files change).

---

## Local Development

```bash
# Backend
cd backend
cp .env.example .env  # fill in real values
uv sync
uv run fastapi dev

# Frontend
cd frontend
cp .env.example .env  # fill in real values
npm install
npm run dev
```
