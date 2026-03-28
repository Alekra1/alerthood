# AlertHood MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a mobile-first neighborhood threat monitoring web app with interactive map, community-driven threat feed, and gamified user profiles.

**Architecture:** "Thin API + Supabase Direct" — frontend reads directly from Supabase (including Realtime subscriptions), all writes go through FastAPI for business logic enforcement (karma, badges, streaks, severity). Supabase Auth issues JWTs consumed by both clients.

**Tech Stack:** React + TypeScript (Vite), Tailwind CSS, MapLibre GL JS, FastAPI (Python), Supabase (Postgres, Auth, Realtime, Storage), pnpm

**Key Specs:**
- Design spec: `docs/superpowers/specs/2026-03-28-alerthood-mvp-design.md`
- Design system: `design/alerthood_neo_noir/DESIGN.md` (Editorial Neo-Brutalism)
- HTML mockups: `design/alerthood_map_view/`, `design/alerthood_threat_feed/`, `design/alerthood_profile_tab/`

---

## Phase 0: Scaffolding & Local Dev Environment

### Task 1: Update AGENTS.md
- [ ] Update Architecture section to reflect "Thin API + Supabase Direct" pattern (reads via Supabase JS, writes through FastAPI)
- [ ] Replace "frontend talks to FastAPI (not Supabase directly)" with the correct pattern
- [ ] Add Supabase CLI as the tool for local dev, migrations, and type generation
- [ ] Remove alembic reference
- [ ] Commit

### Task 2: Supabase Local Environment
- [ ] Run `supabase init` at project root
- [ ] Run `supabase start` to spin up local services
- [ ] Create `.env.local` with Supabase credentials from `supabase status` (URL, anon key, service role key, JWT secret)
- [ ] Add `.env.local` to `.gitignore`
- [ ] Commit

### Task 3: Frontend Scaffolding
- [ ] Scaffold Vite React+TS project in `frontend/`
- [ ] Install deps: `@supabase/supabase-js`, `maplibre-gl`, `react-map-gl`, `tailwindcss`, `@tailwindcss/vite`
- [ ] Configure Vite with Tailwind plugin and `/api` proxy to FastAPI at `localhost:8000`
- [ ] Configure Tailwind with design system tokens from `design/alerthood_neo_noir/DESIGN.md` (colors, fonts, hard shadows, border radius)
- [ ] Set up `index.css` with Tailwind directives and `@font-face` for Space Grotesk + Inter (self-hosted in `public/fonts/`)
- [ ] Create Supabase client (`src/lib/supabase.ts`) using env vars
- [ ] Create FastAPI client wrapper (`src/lib/api.ts`) that attaches JWT from Supabase session
- [ ] Create `frontend/.env` with `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
- [ ] Verify `pnpm dev` starts at `localhost:5173`
- [ ] Commit

### Task 4: Backend Scaffolding
- [ ] Create `backend/pyproject.toml` with deps: fastapi, uvicorn, supabase, pydantic-settings, python-jose, python-multipart, httpx, pytest
- [ ] Create `backend/app/config.py` — Settings class reading Supabase env vars via pydantic-settings
- [ ] Create `backend/app/deps.py` — `get_current_user` dependency (decode JWT from Authorization header using Supabase JWT secret), `get_supabase` dependency (service role client)
- [ ] Create `backend/app/main.py` — FastAPI app with CORS middleware (allow `localhost:5173`) and health endpoint
- [ ] Verify `uvicorn app.main:app --reload` starts at `localhost:8000` with Swagger at `/docs`
- [ ] Commit

**Parallelization:** Tasks 3 and 4 can run in parallel after Task 2.

---

## Phase 1: Database Schema + Auth

### Task 5: Database Migrations
- [ ] Create migration via `supabase migration new initial_schema`
- [ ] Define enums: `event_category` (crime, infrastructure_utility, natural_disaster, public_disturbance), `event_status` (active, resolved, expired), `badge_type` (first_report, trusted_reporter, streak_7, streak_30, upvotes_100, community_guardian)
- [ ] Create `profiles` table — linked to `auth.users(id)`, fields: display_name, avatar_url, karma_score (default 0), trust_score (default 0.50), report_count, vote_count, current_streak, longest_streak, last_active_date, timestamps
- [ ] Create trigger on `auth.users` INSERT to auto-create a profiles row (SECURITY DEFINER)
- [ ] Create `monitored_areas` table — user_id FK, label, lat/lng, radius_meters (default 1000), notification_preferences (JSONB with per-category booleans), is_active
- [ ] Create `events` table — reporter_id FK, title, description, category, lat/lng, photo_url, severity_score (default 0), relevance_score (default 0), vote_count, status (default active), resolved_by, resolved_at, expires_at (default now + 72h), timestamps. Add indexes on location, category, status
- [ ] Create `votes` table — event_id FK, user_id FK, is_relevant (bool), is_true (bool), weight (default 0.50), UNIQUE(event_id, user_id). **Note:** votes use two booleans per spec, not a single enum
- [ ] Create `comments` table — event_id FK, user_id FK, body, parent_id (self-referencing FK for threading), timestamps
- [ ] Create `badges` table — user_id FK, badge_type, awarded_at, UNIQUE(user_id, badge_type)
- [ ] Create `notifications` table — user_id FK, event_id FK (nullable), type, title, body, is_read (default false), timestamps. Add index on (user_id) WHERE NOT is_read
- [ ] Enable RLS on all tables with policies: profiles (read all, update own), monitored_areas (CRUD own), events (read all, insert/update own), votes (read all, insert own), comments (read all, insert/update own), badges (read all), notifications (read/update own)
- [ ] Enable Realtime on events, notifications, votes tables via `ALTER PUBLICATION supabase_realtime ADD TABLE`
- [ ] Apply with `supabase db reset`
- [ ] Generate TypeScript types: `supabase gen types typescript --local > frontend/src/lib/database.types.ts`
- [ ] Create minimal `supabase/seed.sql` with instructions for creating test data
- [ ] Commit

### Task 6: Backend Pydantic Models
- [ ] Create `backend/app/models/enums.py` — Python StrEnum classes matching DB enums
- [ ] Create request/response models for each resource: EventCreate/EventResponse/EventListParams, VoteCreate/VoteResponse, CommentCreate/CommentResponse, AreaCreate/AreaUpdate/AreaResponse, ProfileResponse/ProfileUpdate, NotificationResponse
- [ ] Commit

### Task 7: Auth Flow (Backend + Frontend)
- [ ] Backend: Create `backend/app/routers/auth.py` — `GET /auth/me` (return profile), `PUT /auth/profile` (update display_name, avatar)
- [ ] Register auth router in `main.py`
- [ ] Frontend: Create `AuthContext` wrapping `supabase.auth.onAuthStateChange`, provide user/session/signUp/signIn/signOut
- [ ] Frontend: Create `useAuth` hook consuming context
- [ ] Frontend: Create `AuthPage` — email/password form with sign-up/sign-in toggle, styled per neo-brutalism design system
- [ ] Frontend: Update `App.tsx` — show AuthPage when not authenticated, show app shell when authenticated
- [ ] Verify end-to-end: sign up creates user + auto-creates profile row, sign in works, JWT reaches backend
- [ ] Commit

**Parallelization:** Tasks 6 and 7 can run in parallel after Task 5.

---

## Phase 2: UI Shell + Design System Components

### Task 8: UI Primitives
Build each as a small component matching the design system in `design/alerthood_neo_noir/DESIGN.md`:
- [ ] `Button` — variants: primary (crime red), secondary (infra orange), ghost. Hard shadow, press removes shadow
- [ ] `Card` — surface-container bg, 3px black border, 0.75rem radius. Optional left impact bar (6px, colored by category)
- [ ] `CategoryBadge` — full-radius chips, color-mapped by event category
- [ ] `Input` / `Textarea` — dark bg, 2px border, 3px primary on focus, instant transition (no blur)
- [ ] `Modal` — overlay + card, mobile-first (slides from bottom on mobile, centered on desktop)
- [ ] Commit

### Task 9: TabNav + Page Shells
- [ ] Create `TabNav` — fixed bottom nav with Map/Feed/Profile icons. Active tab uses crime color. Account for safe-area-inset-bottom
- [ ] Create placeholder pages: `MapTab`, `FeedTab`, `ProfileTab`
- [ ] Update `App.tsx` — render TabNav with tab switching state when authenticated
- [ ] Verify tab navigation works in browser
- [ ] Commit

**Parallelization:** Tasks 8 and 9 can start after Task 7 (auth provides the authenticated shell).

---

## Phase 3: Backend Business Logic + Core Routers

### Task 10: Business Logic Services (TDD)
Test the pure functions only — these are the core business rules:

- [ ] **Karma service** — `calculate_karma_change(reason)` returns: +10 report, +2 upvote_received, -1 downvote_received, +1 vote_cast, +5 badge_earned. `apply_karma(sb, user_id, reason)` does atomic update. Write tests first, then implement
- [ ] **Streak service** — `compute_streak(current_streak, longest_streak, last_active, today)` returns updated values or None if same day. Rules: consecutive day increments, gap resets to 1, updates longest. Write tests first, then implement
- [ ] **Severity calculation** — `calculate_severity(votes)` takes list of {is_relevant, is_true, weight}. Positive vote = is_relevant AND is_true. Score = weighted positive sum / total weight * 100, clamped 0-100. Write tests first, then implement
- [ ] **Vote service** — `cast_vote(sb, event_id, user_id, is_relevant, is_true)`: gets voter trust_score as weight, inserts vote, recalculates severity + relevance on event, applies karma to voter (+1) and reporter (+2 or -1), increments voter vote_count
- [ ] **Badge service** — `check_badge_eligibility(profile, total_upvotes, existing_badges)` returns list of new badge types. Rules: first_report (report_count >= 1), trusted_reporter (trust_score >= 0.8), streak_7/30 (current_streak >=), upvotes_100 (cumulative upvotes on user's events >= 100), community_guardian (vote_count >= 50). `evaluate_and_award_badges(sb, user_id)` checks and inserts new badges + applies karma. Write tests first, then implement
- [ ] Run all tests, verify passing
- [ ] Commit

### Task 11: Event + Vote + Comment Routers
- [ ] **Event service** — `create_event`: insert event, increment report_count, apply karma, update streak, evaluate badges, notify area users. `list_events`: query with geo bounding box filter (lat/lng ± delta based on radius), category filter, sort by time or severity, pagination
- [ ] **Notification helper** — `notify_area_users(event)`: find monitored_areas where event is within radius (haversine) AND category enabled in notification_preferences, insert notification for each matching user (skip reporter)
- [ ] **Events router** — `POST /events`, `GET /events` (with query params: lat, lng, radius_m, category, sort, page, limit), `GET /events/{id}`, `POST /events/{id}/vote`, `PATCH /events/{id}/resolve` (reporter only)
- [ ] **Comments router** — `POST /events/{id}/comments`, `GET /events/{id}/comments` (join with profiles for display_name)
- [ ] Register routers in main.py
- [ ] Verify endpoints in Swagger
- [ ] Commit

### Task 12: Remaining Routers
- [ ] **Areas router** — full CRUD: `POST /areas`, `GET /areas` (user's own), `PUT /areas/{id}`, `DELETE /areas/{id}`
- [ ] **Profile router** — `GET /profile`, `GET /profile/badges`, `GET /profile/events`
- [ ] **Notifications router** — `GET /notifications` (limit 50, ordered by created_at desc), `PATCH /notifications/{id}` (mark read), `PATCH /notifications/read-all`
- [ ] **Upload router** — `POST /upload/photo`: accept multipart file, upload to Supabase Storage bucket `event-photos`, return public URL
- [ ] Create `event-photos` storage bucket (public) via Supabase CLI or SQL
- [ ] Register all routers in main.py
- [ ] Verify all 14+ endpoints in Swagger
- [ ] Commit

**Parallelization:** Task 10 and Task 8/9 are independent (backend vs frontend). Tasks 11-12 depend on Task 10.

---

## Phase 4: Map Tab (Frontend)

### Task 13: MapView + Event Markers
- [ ] Create `useEvents` hook — reads events from Supabase with geo bounding box filter, returns events + loading state
- [ ] Create `useAreas` hook — reads user's monitored areas from Supabase
- [ ] Create `MapView` component — initialize MapLibre GL with dark basemap (CartoDB Dark Matter, free, no API key), geolocate control, emit bounds on moveend
- [ ] Create `EventMarker` component — render markers on map using MapLibre Marker API, colored by category (crime=#FF5545, infra=#FE9400, disaster=#C567F4), 3px black border, hard shadow
- [ ] Create `MonitoredAreaCircle` component — render dashed white circle overlay for each monitored area using GeoJSON polygon source + line layer with dasharray
- [ ] Assemble `MapTab` — MapView with EventMarkers and MonitoredAreaCircles, pass map instance to children via context or callback ref
- [ ] Verify map renders with dark theme
- [ ] Commit

### Task 14: EventPopup + ReportEventModal
- [ ] Create `EventPopup` — bottom sheet card that appears on marker click. Shows: category badge, title, time ago, severity bar, relevance bar. Styled per mockup in `design/alerthood_map_view/`
- [ ] Create `ReportEventModal` — form with: title input, description textarea, category selector (4 chip buttons), location display (from map tap or GPS), photo upload (calls `/upload/photo`), submit button (calls `POST /events` via FastAPI client)
- [ ] Add FAB button (+ icon, crime red, bottom-right above tab nav) to MapTab that opens ReportEventModal
- [ ] Wire up map tap to set report location
- [ ] Commit

---

## Phase 5: Feed Tab (Frontend)

### Task 15: Feed Components
- [ ] Create `FilterBar` — horizontal scrolling category chips (ALL, CRIME, UTILITY, NATURAL, DISTURBANCE) + sort toggle (Latest/Severity). Style per `design/alerthood_threat_feed/` mockup
- [ ] Create `PostCard` — card with left impact bar (6px, colored by category), category badge, title, time ago, severity bar, relevance percentage. Match the threat feed mockup
- [ ] Create `PostList` — vertical list with infinite scroll via IntersectionObserver
- [ ] Create `useVotes` hook — `castVote(eventId, isRelevant, isTrue)` via FastAPI, track voted state
- [ ] Create `VoteButtons` — confirm/deny buttons, disabled after voting, shows "Vote recorded" state
- [ ] Create `useComments` hook — read comments from Supabase (joined with profiles), `addComment` via FastAPI
- [ ] Create `CommentThread` — recursive rendering with indent by depth, add-comment input at bottom
- [ ] Create `PostDetail` — full-screen event detail view with description, photo, severity/relevance stats, VoteButtons, CommentThread. Use 3px black border separators between sections
- [ ] Assemble `FeedTab` — FilterBar at top, PostList below, PostDetail as overlay on event click. Header shows "THREAT FEED"
- [ ] Commit

---

## Phase 6: Profile Tab (Frontend)

### Task 16: Profile Components
- [ ] Create `useProfile` hook — read profile + badges from Supabase
- [ ] Create `ProfileHeader` — avatar (initial letter fallback), display name, email, large karma number. Match `design/alerthood_profile_tab/` mockup
- [ ] Create trust/reports/votes stat cards row — 3 cards with large numbers and labels
- [ ] Create `StatBadges` — streak counter with fire icon, badge grid (3x2) showing earned vs locked badges. All 6 badge types with icons
- [ ] Create `MonitoredAreasList` — list of areas with label, radius, remove button (calls `DELETE /areas/{id}`)
- [ ] Assemble `ProfileTab` — ProfileHeader, stat cards, StatBadges, MonitoredAreasList, sign out button
- [ ] Commit

---

## Phase 7: Realtime + Notifications

### Task 17: Realtime Subscriptions + NotificationBanner
- [ ] Create `useRealtimeEvents` hook — subscribe to events table INSERT via Supabase Realtime, merge new events into local state
- [ ] Create `useNotifications` hook — initial fetch of notifications, subscribe to Realtime INSERTs filtered by user_id, track unread count, track latest notification for banner
- [ ] Create `NotificationBanner` — slides in from top, auto-dismiss after 5s. Shows notification type, title, body. Styled with category color. Tap to dismiss
- [ ] Wire up NotificationBanner in App.tsx
- [ ] Add unread count badge to notification bell icon (if applicable)
- [ ] Commit

---

## Phase 8: Polish + Verification

### Task 18: Final Integration + Mobile Polish
- [ ] Add `viewport-fit=cover` meta tag and safe-area padding to CSS
- [ ] Ensure bottom tab nav accounts for `env(safe-area-inset-bottom)`
- [ ] Test on 375px viewport width (iPhone SE) — verify cards, map, forms are usable
- [ ] Verify map touch gestures work (pinch zoom, pan)
- [ ] Run full backend test suite: `python -m pytest tests/ -v`
- [ ] E2E verification flow: sign up → report event → vote → check severity update → check profile badges → check notifications (with second user)
- [ ] Commit

---

## Dependency Graph

```
Task 1 (AGENTS.md update)
Task 2 (Supabase init) ──┬── Task 3 (Frontend scaffold)
                         └── Task 4 (Backend scaffold)
                                      │
Task 5 (DB schema) ──┬── Task 6 (Pydantic models) ── Task 10 (Business logic TDD)
                     │                                       │
                     └── Task 7 (Auth flow)                  ▼
                              │                    Task 11 (Event/vote/comment routers)
                              │                              │
                     Task 8 (UI primitives)        Task 12 (Remaining routers)
                              │                              │
                     Task 9 (TabNav) ────────────────────────┘
                              │
                     Task 13 (Map: MapView + markers)
                              │
                     Task 14 (Map: popup + report modal)
                              │
                     Task 15 (Feed tab)
                              │
                     Task 16 (Profile tab)
                              │
                     Task 17 (Realtime + notifications)
                              │
                     Task 18 (Polish + verification)
```

**Parallelizable groups:**
- Tasks 3 + 4 (frontend + backend scaffold)
- Tasks 6 + 7 (models + auth) after Task 5
- Tasks 8/9 + 10 (UI primitives + business logic TDD) — fully independent
- Tasks 11/12 + 13 (backend routers + map frontend) can overlap once deps are met

## Key Technical Decisions

1. **Dark basemap:** CartoDB Dark Matter (free, no API key) — matches `#131313` surface color
2. **Geo-filtering:** Bounding box in Postgres (lat/lng ± delta). No PostGIS needed for MVP scale
3. **Vote model:** Two booleans (is_relevant, is_true) per spec, not a single enum
4. **State management:** React Context for auth, custom hooks with useState/useEffect. No Redux/Zustand for MVP
5. **Routing:** Simple useState for tabs, no React Router needed for 3-tab SPA
6. **Fonts:** Self-hosted in `/public/fonts/` for privacy and performance
7. **Tests:** Business logic only (karma, streaks, severity, badges) per AGENTS.md guidance — minimal tests, priority is business logic
