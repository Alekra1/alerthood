# AlertHood 18-Hour Parallel Dev Sprint

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship AlertHood MVP with auth, live data, heatmap, safe routing with Google Maps export, geolocation, and notifications — 3 devs working in parallel for 18 hours.

**Architecture:** Frontend reads from Supabase directly (events, profiles, subscriptions, realtime). Writes go through FastAPI (event creation, subscriptions, route calculation). Supabase Auth handles email/password + Google OAuth. Leaflet map with heatmap overlay. Safe route engine on backend returns waypoints formatted as Google Maps URL.

**Tech Stack:** React 18 + TypeScript + Vite + Tailwind + Leaflet (frontend), FastAPI + Python + httpx (backend), Supabase (Postgres + PostGIS + Auth + Realtime)

**Timeline:** 18 hours. Feature freeze at hour 16. Submit at hour 18 (tomorrow noon).

---

## File Structure

### New Files

```
frontend/src/
  lib/
    supabase.ts              # Supabase JS client init
    api.ts                   # FastAPI client helpers
  hooks/
    useAuth.ts               # Auth state hook
    useEvents.ts             # Events from Supabase
    useAreas.ts              # Areas + subscriptions
    useGeolocation.ts        # Browser geolocation
  pages/
    AuthPage.tsx             # Sign-in / sign-up page
    RoutePage.tsx            # Route planner page
  components/
    auth/
      AuthForm.tsx           # Email/password + Google OAuth form
    route/
      RouteView.tsx          # Route planner UI
      RouteBottomSheet.tsx   # Route result with Google Maps link
    layout/
      NotificationBell.tsx   # Bell icon + dropdown

backend/
  routers/
    routes.py                # Safe route endpoints
    auth_routes.py           # Google OAuth callback (if needed)
  services/
    route_engine.py          # Safe route calculation
    historical_import.py     # ACLED / historical data bulk import
    geocoding.py             # Reverse geocoding for area detection
    neighborhood_scores.py   # Crime rate + poverty index per area
```

### Modified Files

```
frontend/src/
  App.tsx                    # Add auth guard, /auth and /route routes
  main.tsx                   # Wrap with auth provider
  types/index.ts             # Add Route, Notification types
  components/
    map/MapView.tsx          # Replace mock data, add heatmap layer, geolocation
    feed/FeedView.tsx        # Replace mock data, add realtime
    feed/ThreatCard.tsx      # Add "View on Map" navigation
    profile/ProfileView.tsx  # Wire to real user data
    layout/TopBar.tsx        # Add NotificationBell

backend/
  main.py                    # Register route router, historical import on startup
  requirements.txt           # Add geopy
  config.py                  # Add Google OAuth + geocoding config
```

---

## Olexii / Dev 1 (Frontend) — Auth + Live Data + Route UI

### Task 1.1: Install Supabase JS + Create Client

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/lib/supabase.ts`
- Create: `frontend/.env`

- [ ] **Step 1: Install @supabase/supabase-js**

```bash
cd frontend && npm install @supabase/supabase-js
```

- [ ] **Step 2: Create .env file**

```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

Get these values from the Supabase dashboard → Settings → API.

- [ ] **Step 3: Create supabase client**

Write `frontend/src/lib/supabase.ts`:

```typescript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

- [ ] **Step 4: Create API helper**

Write `frontend/src/lib/api.ts`:

```typescript
import { supabase } from './supabase'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function apiFetch(path: string, options: RequestInit = {}) {
  const { data: { session } } = await supabase.auth.getSession()
  const token = session?.access_token

  return fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
}
```

- [ ] **Step 5: Add VITE_API_URL to .env**

```
VITE_API_URL=http://localhost:8000
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/supabase.ts frontend/src/lib/api.ts frontend/.env frontend/package.json frontend/package-lock.json
git commit -m "feat: add Supabase JS client + API helper"
```

---

### Task 1.2: Auth Hook + Auth Page

**Files:**
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/pages/AuthPage.tsx`
- Create: `frontend/src/components/auth/AuthForm.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add auth types**

Add to `frontend/src/types/index.ts`:

```typescript
export interface AuthUser {
  id: string
  email: string
  display_name: string
  avatar_url: string | null
}

export interface Notification {
  id: string
  event_id: string | null
  title: string
  body: string | null
  is_read: boolean
  created_at: string
}

export interface RouteWaypoint {
  lat: number
  lng: number
}

export interface SafeRoute {
  waypoints: RouteWaypoint[]
  google_maps_url: string
  avoided_events: number
  distance_km: number
}
```

- [ ] **Step 2: Create useAuth hook**

Write `frontend/src/hooks/useAuth.ts`:

```typescript
import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'
import type { User, Session } from '@supabase/supabase-js'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setUser(session?.user ?? null)
      setLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      setUser(session?.user ?? null)
    })

    return () => subscription.unsubscribe()
  }, [])

  const signInWithEmail = (email: string, password: string) =>
    supabase.auth.signInWithPassword({ email, password })

  const signUpWithEmail = (email: string, password: string) =>
    supabase.auth.signUp({ email, password })

  const signInWithGoogle = () =>
    supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })

  const signOut = () => supabase.auth.signOut()

  return { user, session, loading, signInWithEmail, signUpWithEmail, signInWithGoogle, signOut }
}
```

- [ ] **Step 3: Create AuthForm component**

Write `frontend/src/components/auth/AuthForm.tsx`:

```typescript
import { useState } from 'react'

interface AuthFormProps {
  onSignIn: (email: string, password: string) => Promise<unknown>
  onSignUp: (email: string, password: string) => Promise<unknown>
  onGoogleSignIn: () => Promise<unknown>
}

export function AuthForm({ onSignIn, onSignUp, onGoogleSignIn }: AuthFormProps) {
  const [isSignUp, setIsSignUp] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const { error } = (isSignUp
      ? await onSignUp(email, password)
      : await onSignIn(email, password)) as { error: { message: string } | null }
    if (error) setError(error.message)
    setLoading(false)
  }

  return (
    <div className="w-full max-w-sm mx-auto space-y-6">
      <div className="text-center">
        <h1 className="font-headline text-4xl font-bold uppercase tracking-tight">
          {isSignUp ? 'CREATE ACCOUNT' : 'SIGN IN'}
        </h1>
        <p className="font-body text-on-surface-variant text-sm mt-2">
          {isSignUp ? 'Join your neighborhood watch' : 'Monitor your neighborhood'}
        </p>
      </div>

      <button
        onClick={() => { setError(null); onGoogleSignIn() }}
        className="w-full py-3 bg-surface-container border-[3px] border-black shadow-hard font-headline font-bold uppercase tracking-widest text-sm active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-none flex items-center justify-center gap-3"
      >
        <svg className="w-5 h-5" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        CONTINUE WITH GOOGLE
      </button>

      <div className="flex items-center gap-4">
        <div className="flex-1 h-[2px] bg-outline-variant" />
        <span className="font-label text-xs text-on-surface-variant uppercase">or</span>
        <div className="flex-1 h-[2px] bg-outline-variant" />
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="email"
          placeholder="EMAIL"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full px-4 py-3 bg-surface-container border-[3px] border-black shadow-hard-sm font-body text-on-surface placeholder:text-on-surface-variant placeholder:font-headline placeholder:text-xs placeholder:uppercase placeholder:tracking-widest focus:outline-none focus:border-primary"
        />
        <input
          type="password"
          placeholder="PASSWORD"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={6}
          className="w-full px-4 py-3 bg-surface-container border-[3px] border-black shadow-hard-sm font-body text-on-surface placeholder:text-on-surface-variant placeholder:font-headline placeholder:text-xs placeholder:uppercase placeholder:tracking-widest focus:outline-none focus:border-primary"
        />

        {error && (
          <div className="px-3 py-2 bg-error-container border-2 border-black text-on-error-container font-body text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 bg-primary-container border-[3px] border-black shadow-hard font-headline font-bold uppercase tracking-widest text-sm text-on-primary-container active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-none disabled:opacity-50"
        >
          {loading ? 'LOADING...' : isSignUp ? 'CREATE ACCOUNT' : 'SIGN IN'}
        </button>
      </form>

      <button
        onClick={() => { setIsSignUp(!isSignUp); setError(null) }}
        className="w-full text-center font-body text-sm text-on-surface-variant underline"
      >
        {isSignUp ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
      </button>
    </div>
  )
}
```

- [ ] **Step 4: Create AuthPage**

Write `frontend/src/pages/AuthPage.tsx`:

```typescript
import { AuthForm } from '../components/auth/AuthForm'
import { useAuth } from '../hooks/useAuth'
import { Navigate } from 'react-router-dom'

export function AuthPage() {
  const { user, loading, signInWithEmail, signUpWithEmail, signInWithGoogle } = useAuth()

  if (loading) return null
  if (user) return <Navigate to="/map" replace />

  return (
    <main className="min-h-dvh bg-background flex flex-col items-center justify-center px-6">
      <div className="mb-8 text-center">
        <div className="w-16 h-16 bg-primary-container border-[3px] border-black shadow-hard mx-auto mb-4 flex items-center justify-center">
          <span className="material-symbols-outlined text-on-primary-container text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
            shield
          </span>
        </div>
        <h2 className="font-headline text-lg font-bold uppercase tracking-widest text-primary">ALERTHOOD</h2>
      </div>
      <AuthForm
        onSignIn={signInWithEmail}
        onSignUp={signUpWithEmail}
        onGoogleSignIn={signInWithGoogle}
      />
    </main>
  )
}
```

- [ ] **Step 5: Update App.tsx with auth guard**

Replace `frontend/src/App.tsx`:

```typescript
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { TopBar } from './components/layout/TopBar'
import { BottomNav } from './components/layout/BottomNav'
import { MapPage } from './pages/MapPage'
import { FeedPage } from './pages/FeedPage'
import { ProfilePage } from './pages/ProfilePage'
import { AuthPage } from './pages/AuthPage'
import { useAuth } from './hooks/useAuth'

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/auth" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/auth" element={<AuthPage />} />
        <Route
          path="/*"
          element={
            <AuthGuard>
              <div className="min-h-dvh bg-background text-on-background font-body">
                <TopBar notificationCount={3} />
                <Routes>
                  <Route path="/" element={<Navigate to="/map" replace />} />
                  <Route path="/map" element={<MapPage />} />
                  <Route path="/feed" element={<FeedPage />} />
                  <Route path="/profile" element={<ProfilePage />} />
                </Routes>
                <BottomNav />
              </div>
            </AuthGuard>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useAuth.ts frontend/src/components/auth/AuthForm.tsx frontend/src/pages/AuthPage.tsx frontend/src/App.tsx frontend/src/types/index.ts
git commit -m "feat: auth flow with email/password + Google OAuth"
```

---

### Task 1.3: Wire Map to Real Supabase Data + Geolocation

**Files:**
- Create: `frontend/src/hooks/useEvents.ts`
- Create: `frontend/src/hooks/useGeolocation.ts`
- Modify: `frontend/src/components/map/MapView.tsx`

- [ ] **Step 1: Create useGeolocation hook**

Write `frontend/src/hooks/useGeolocation.ts`:

```typescript
import { useState, useEffect } from 'react'

interface GeoPosition {
  lat: number
  lng: number
}

export function useGeolocation() {
  const [position, setPosition] = useState<GeoPosition | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!navigator.geolocation) {
      setError('Geolocation not supported')
      setLoading(false)
      return
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setPosition({ lat: pos.coords.latitude, lng: pos.coords.longitude })
        setLoading(false)
      },
      (err) => {
        setError(err.message)
        setLoading(false)
      },
      { enableHighAccuracy: true, timeout: 10000 }
    )
  }, [])

  return { position, error, loading }
}
```

- [ ] **Step 2: Create useEvents hook**

Write `frontend/src/hooks/useEvents.ts`:

```typescript
import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'
import type { Threat } from '../types'

// Map DB row to frontend Threat type
function mapEventToThreat(row: Record<string, unknown>): Threat {
  const categoryMap: Record<string, string> = {
    crime: 'CRIME',
    infrastructure: 'UTILITY',
    natural: 'NATURAL',
    disturbance: 'DISTURBANCE',
  }
  const occurredAt = new Date(row.occurred_at as string)
  const minutesAgo = Math.round((Date.now() - occurredAt.getTime()) / 60000)

  return {
    id: row.id as string,
    title: row.title as string,
    category: (categoryMap[row.threat_type as string] || 'CRIME') as Threat['category'],
    severity: (row.severity as string).toUpperCase() as Threat['severity'],
    severityPct: row.relevance_score as number,
    relevancePct: row.relevance_score as number,
    location: (row.location_label as string) || 'Unknown',
    lat: row.lat as number,
    lng: row.lng as number,
    minutesAgo,
    commentCount: (row.comment_count as number) || 0,
    upvotes: 0,
    source: (row.source_type as string) || 'news',
  }
}

export function useEvents(areaId?: string) {
  const [events, setEvents] = useState<Threat[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchEvents() {
      // Use the RPC function that returns lat/lng extracted from geometry
      let query = supabase
        .rpc('events_in_area', areaId ? {
          area_center: `POINT(0 0)`, // placeholder, we filter by area_id instead
          radius_km: 9999,
        } : undefined as never)

      if (!areaId) {
        // Fallback: fetch recent events directly with raw SQL extraction
        const { data, error } = await supabase
          .from('events')
          .select('*, lat:location->>1, lng:location->>0')
          .order('occurred_at', { ascending: false })
          .limit(100)

        if (!error && data) {
          // PostGIS geometry needs extraction — use a simpler approach
          setEvents(data.map(mapEventToThreat))
        }
        setLoading(false)
        return
      }

      const { data, error } = await supabase
        .from('events')
        .select('*')
        .eq('area_id', areaId)
        .order('occurred_at', { ascending: false })
        .limit(100)

      if (!error && data) {
        setEvents(data.map(mapEventToThreat))
      }
      setLoading(false)
    }

    fetchEvents()

    // Realtime subscription for new events
    const channel = supabase
      .channel('events-realtime')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'events' }, (payload) => {
        const newEvent = mapEventToThreat(payload.new)
        setEvents((prev) => [newEvent, ...prev])
      })
      .subscribe()

    return () => { supabase.removeChannel(channel) }
  }, [areaId])

  return { events, loading }
}
```

**Note:** PostGIS geometry columns store data as binary. The `events_in_area` RPC function already extracts lat/lng. For direct queries, we may need a DB view or RPC that returns lat/lng as separate columns. Dev 2 will create an RPC `events_with_coords` to handle this — in the meantime, if lat/lng extraction fails, fall back to mock data.

- [ ] **Step 3: Update MapView to use real data + geolocation**

Replace `frontend/src/components/map/MapView.tsx`:

```typescript
import { useState } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import { useEvents } from '../../hooks/useEvents'
import { useGeolocation } from '../../hooks/useGeolocation'
import type { Threat } from '../../types'
import { ThreatMarker } from './ThreatMarker'
import { MonitoredZone } from './MonitoredZone'
import { AlertBottomSheet } from './AlertBottomSheet'
import { MOCK_THREATS, MOCK_PROFILE } from '../../data/mock'

const FALLBACK_CENTER: [number, number] = [41.882, -87.631]
const MAP_ZOOM = 14

const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'

function FlyToLocation({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap()
  map.flyTo([lat, lng], MAP_ZOOM, { duration: 1.5 })
  return null
}

export function MapView() {
  const { events, loading } = useEvents()
  const { position } = useGeolocation()
  const [selectedThreat, setSelectedThreat] = useState<Threat | null>(null)

  const threats = events.length > 0 ? events : MOCK_THREATS
  const center: [number, number] = position
    ? [position.lat, position.lng]
    : FALLBACK_CENTER

  const homeArea = MOCK_PROFILE.areas.find((a) => a.name === 'HOME')

  return (
    <div className="relative w-full h-full">
      <MapContainer
        center={center}
        zoom={MAP_ZOOM}
        className="w-full h-full"
        zoomControl
        attributionControl={false}
      >
        <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />

        {position && <FlyToLocation lat={position.lat} lng={position.lng} />}

        {homeArea && <MonitoredZone area={homeArea} />}

        {threats.map((threat) => (
          <ThreatMarker
            key={threat.id}
            threat={threat}
            isSelected={selectedThreat?.id === threat.id}
            onSelect={setSelectedThreat}
          />
        ))}
      </MapContainer>

      {selectedThreat && (
        <AlertBottomSheet
          threat={selectedThreat}
          onClose={() => setSelectedThreat(null)}
          onViewDetails={(t) => console.log('View details for', t.id)}
        />
      )}

      <button
        className="fixed bottom-24 right-6 w-16 h-16 bg-primary-container border-[3px] border-black shadow-hard active:translate-x-[2px] active:translate-y-[2px] active:shadow-none flex items-center justify-center z-40 transition-none"
        aria-label="Add new alert"
      >
        <span className="material-symbols-outlined text-on-primary-container text-4xl font-bold">add</span>
      </button>
    </div>
  )
}
```

- [ ] **Step 4: Verify map loads and attempts geolocation**

```bash
cd frontend && npm run dev
```

Open browser, check:
- Geolocation prompt appears
- If allowed, map centers on user's location
- If Supabase data loads, real markers appear; otherwise falls back to mock

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useEvents.ts frontend/src/hooks/useGeolocation.ts frontend/src/components/map/MapView.tsx
git commit -m "feat: wire map to Supabase + geolocation centering"
```

---

### Task 1.4: Wire Feed to Real Data + Realtime

**Files:**
- Modify: `frontend/src/components/feed/FeedView.tsx`
- Modify: `frontend/src/components/feed/ThreatCard.tsx`

- [ ] **Step 1: Update FeedView to use useEvents**

Replace the mock imports in `frontend/src/components/feed/FeedView.tsx`:

```typescript
import { useState } from 'react'
import { useEvents } from '../../hooks/useEvents'
import { MOCK_THREATS } from '../../data/mock'
import type { ThreatCategory } from '../../types'
import { ActiveThreatBanner } from './ActiveThreatBanner'
import { FilterBar } from './FilterBar'
import { ThreatCard } from './ThreatCard'

type FilterValue = 'ALL' | ThreatCategory

export function FeedView() {
  const { events } = useEvents()
  const [activeFilter, setActiveFilter] = useState<FilterValue>('ALL')

  const threats = events.length > 0 ? events : MOCK_THREATS
  const activeThreat = threats.find((t) => t.minutesAgo <= 5) ?? threats[0]

  const filtered =
    activeFilter === 'ALL'
      ? threats
      : threats.filter((t) => t.category === activeFilter)

  return (
    <div className="px-4 max-w-2xl mx-auto">
      <div className="mt-6">
        {activeThreat && <ActiveThreatBanner threat={activeThreat} />}
      </div>

      <div className="sticky top-16 bg-background z-40 py-4 -mx-4 px-4 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <button className="flex items-center gap-2 bg-surface-container border-2 border-black px-3 py-1.5 shadow-hard-sm active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-none">
            <span className="material-symbols-outlined text-primary text-sm">location_on</span>
            <span className="font-headline font-bold text-sm tracking-tight uppercase">Nearby</span>
            <span className="material-symbols-outlined text-sm">expand_more</span>
          </button>
          <button
            className="p-2 border-2 border-black bg-surface-container active:shadow-none shadow-hard-sm"
            aria-label="Filter options"
          >
            <span className="material-symbols-outlined">tune</span>
          </button>
        </div>
        <FilterBar active={activeFilter} onChange={setActiveFilter} />
      </div>

      <div className="flex flex-col gap-8 mt-4 pb-8">
        {filtered.length === 0 ? (
          <div className="text-center py-16 text-on-surface-variant">
            <span className="material-symbols-outlined text-5xl block mb-3 opacity-30">check_circle</span>
            <p className="font-headline font-bold uppercase tracking-widest text-sm">All Clear</p>
            <p className="font-body text-xs mt-1 opacity-60">No {activeFilter.toLowerCase()} alerts in your area</p>
          </div>
        ) : (
          filtered.map((threat) => <ThreatCard key={threat.id} threat={threat} />)
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add "View on Map" to ThreatCard**

In `frontend/src/components/feed/ThreatCard.tsx`, add a navigation link. Find the action buttons section and add:

```typescript
import { useNavigate } from 'react-router-dom'

// Inside ThreatCard component:
const navigate = useNavigate()

// Add this button in the actions area:
<button
  onClick={() => navigate(`/map?lat=${threat.lat}&lng=${threat.lng}&id=${threat.id}`)}
  className="flex items-center gap-1 bg-[#131313] text-white border-2 border-black shadow-hard-sm px-3 py-1.5 font-headline font-bold text-xs uppercase tracking-widest active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-none"
>
  <span className="material-symbols-outlined text-sm">map</span>
  VIEW MAP
</button>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/feed/FeedView.tsx frontend/src/components/feed/ThreatCard.tsx
git commit -m "feat: wire feed to Supabase + add View on Map button"
```

---

### Task 1.5: Heatmap Layer on Map

**Files:**
- Modify: `frontend/src/components/map/MapView.tsx`
- Create: `frontend/src/components/map/HeatmapLayer.tsx`

- [ ] **Step 1: Install leaflet.heat**

```bash
cd frontend && npm install leaflet.heat
```

If no types exist, create a declaration file `frontend/src/leaflet-heat.d.ts`:

```typescript
declare module 'leaflet.heat' {
  import * as L from 'leaflet'
  function heatLayer(latlngs: Array<[number, number, number?]>, options?: Record<string, unknown>): L.Layer
  export = heatLayer
}
```

- [ ] **Step 2: Create HeatmapLayer component**

Write `frontend/src/components/map/HeatmapLayer.tsx`:

```typescript
import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet.heat'
import type { Threat } from '../../types'

interface HeatmapLayerProps {
  threats: Threat[]
}

const SEVERITY_WEIGHT: Record<string, number> = {
  LOW: 0.25,
  MEDIUM: 0.5,
  HIGH: 0.75,
  CRITICAL: 1.0,
}

export function HeatmapLayer({ threats }: HeatmapLayerProps) {
  const map = useMap()

  useEffect(() => {
    const points: [number, number, number][] = threats.map((t) => [
      t.lat,
      t.lng,
      SEVERITY_WEIGHT[t.severity] || 0.5,
    ])

    const heat = (L as unknown as { heatLayer: typeof import('leaflet.heat') }).heatLayer(points, {
      radius: 30,
      blur: 20,
      maxZoom: 17,
      max: 1.0,
      gradient: {
        0.0: '#4ade80',  // green - safe
        0.3: '#facc15',  // yellow - caution
        0.6: '#FE9400',  // orange - warning
        0.8: '#FF5545',  // red - danger
        1.0: '#C567F4',  // purple - critical
      },
    }).addTo(map)

    return () => { map.removeLayer(heat) }
  }, [map, threats])

  return null
}
```

- [ ] **Step 3: Add HeatmapLayer to MapView**

In `MapView.tsx`, import and add inside `<MapContainer>`:

```typescript
import { HeatmapLayer } from './HeatmapLayer'

// Inside MapContainer, after TileLayer:
<HeatmapLayer threats={threats} />
```

- [ ] **Step 4: Verify heatmap renders**

```bash
cd frontend && npm run dev
```

Expected: Green-to-red heat overlay appears around event clusters.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/map/HeatmapLayer.tsx frontend/src/components/map/MapView.tsx frontend/src/leaflet-heat.d.ts frontend/package.json frontend/package-lock.json
git commit -m "feat: heatmap layer with severity-weighted gradient"
```

---

### Task 1.6: Route Planner UI

**Files:**
- Create: `frontend/src/pages/RoutePage.tsx`
- Create: `frontend/src/components/route/RouteView.tsx`
- Create: `frontend/src/components/route/RouteBottomSheet.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/BottomNav.tsx`

**Depends on:** Dev 2 completing Task 2.1 (route API). Build the UI first with a placeholder, wire to API when ready.

- [ ] **Step 1: Create RouteView component**

Write `frontend/src/components/route/RouteView.tsx`:

```typescript
import { useState } from 'react'
import { MapContainer, TileLayer, Polyline, Marker, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { useGeolocation } from '../../hooks/useGeolocation'
import { HeatmapLayer } from '../map/HeatmapLayer'
import { useEvents } from '../../hooks/useEvents'
import { RouteBottomSheet } from './RouteBottomSheet'
import { apiFetch } from '../../lib/api'
import type { SafeRoute } from '../../types'

const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
const FALLBACK_CENTER: [number, number] = [41.882, -87.631]

function ClickHandler({ onMapClick }: { onMapClick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      onMapClick(e.latlng.lat, e.latlng.lng)
    },
  })
  return null
}

const startIcon = new L.DivIcon({
  html: '<div class="w-6 h-6 bg-success border-2 border-black shadow-hard-sm flex items-center justify-center"><span class="text-black text-xs font-bold">A</span></div>',
  className: '',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
})

const endIcon = new L.DivIcon({
  html: '<div class="w-6 h-6 bg-primary-container border-2 border-black shadow-hard-sm flex items-center justify-center"><span class="text-black text-xs font-bold">B</span></div>',
  className: '',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
})

export function RouteView() {
  const { position } = useGeolocation()
  const { events } = useEvents()
  const [origin, setOrigin] = useState<[number, number] | null>(
    position ? [position.lat, position.lng] : null
  )
  const [destination, setDestination] = useState<[number, number] | null>(null)
  const [route, setRoute] = useState<SafeRoute | null>(null)
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState<'origin' | 'destination'>('origin')

  const center: [number, number] = position
    ? [position.lat, position.lng]
    : FALLBACK_CENTER

  const handleMapClick = (lat: number, lng: number) => {
    if (step === 'origin') {
      setOrigin([lat, lng])
      setStep('destination')
    } else {
      setDestination([lat, lng])
    }
  }

  const calculateRoute = async () => {
    if (!origin || !destination) return
    setLoading(true)
    const res = await apiFetch('/api/routes/safe', {
      method: 'POST',
      body: JSON.stringify({
        origin_lat: origin[0],
        origin_lng: origin[1],
        dest_lat: destination[0],
        dest_lng: destination[1],
      }),
    })
    if (res.ok) {
      const data: SafeRoute = await res.json()
      setRoute(data)
    }
    setLoading(false)
  }

  const routeLine: [number, number][] = route
    ? route.waypoints.map((w) => [w.lat, w.lng])
    : []

  return (
    <div className="relative w-full h-full">
      <MapContainer center={center} zoom={14} className="w-full h-full" zoomControl attributionControl={false}>
        <TileLayer url={TILE_URL} />
        <ClickHandler onMapClick={handleMapClick} />
        <HeatmapLayer threats={events} />

        {origin && <Marker position={origin} icon={startIcon} />}
        {destination && <Marker position={destination} icon={endIcon} />}
        {routeLine.length > 0 && (
          <Polyline positions={routeLine} pathOptions={{ color: '#4ade80', weight: 4, dashArray: '8 4' }} />
        )}
      </MapContainer>

      {/* Instructions overlay */}
      <div className="absolute top-4 left-4 right-4 z-[1000]">
        <div className="bg-surface-container border-[3px] border-black shadow-hard px-4 py-3">
          <p className="font-headline font-bold text-sm uppercase tracking-widest">
            {!origin ? 'TAP TO SET START POINT' :
             !destination ? 'TAP TO SET DESTINATION' :
             !route ? 'READY TO CALCULATE' : 'ROUTE FOUND'}
          </p>
          {origin && destination && !route && (
            <button
              onClick={calculateRoute}
              disabled={loading}
              className="mt-2 w-full py-2 bg-primary-container border-2 border-black shadow-hard-sm font-headline font-bold text-xs uppercase tracking-widest active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-none disabled:opacity-50"
            >
              {loading ? 'CALCULATING...' : 'FIND SAFE ROUTE'}
            </button>
          )}
          {(origin || destination) && (
            <button
              onClick={() => { setOrigin(null); setDestination(null); setRoute(null); setStep('origin') }}
              className="mt-2 w-full py-1 font-body text-xs text-on-surface-variant underline"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {route && <RouteBottomSheet route={route} onClose={() => setRoute(null)} />}
    </div>
  )
}
```

- [ ] **Step 2: Create RouteBottomSheet**

Write `frontend/src/components/route/RouteBottomSheet.tsx`:

```typescript
import type { SafeRoute } from '../../types'

interface RouteBottomSheetProps {
  route: SafeRoute
  onClose: () => void
}

export function RouteBottomSheet({ route, onClose }: RouteBottomSheetProps) {
  return (
    <div className="absolute bottom-0 left-0 right-0 z-[1000] p-4">
      <div className="bg-surface-container border-[3px] border-black shadow-hard rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-headline font-bold text-lg uppercase tracking-tight">SAFE ROUTE</h3>
          <button onClick={onClose} className="p-1">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <div className="flex gap-4">
          <div className="bg-surface-container-low border-2 border-black p-3 flex-1">
            <p className="font-label text-xs text-on-surface-variant uppercase">Distance</p>
            <p className="font-headline font-bold text-lg">{route.distance_km.toFixed(1)} km</p>
          </div>
          <div className="bg-surface-container-low border-2 border-black p-3 flex-1">
            <p className="font-label text-xs text-on-surface-variant uppercase">Avoided</p>
            <p className="font-headline font-bold text-lg text-primary">{route.avoided_events} threats</p>
          </div>
        </div>

        <a
          href={route.google_maps_url}
          target="_blank"
          rel="noopener noreferrer"
          className="block w-full py-3 bg-primary-container border-[3px] border-black shadow-hard font-headline font-bold uppercase tracking-widest text-sm text-center text-on-primary-container active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-none"
        >
          OPEN IN GOOGLE MAPS
        </a>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create RoutePage**

Write `frontend/src/pages/RoutePage.tsx`:

```typescript
import { RouteView } from '../components/route/RouteView'

export function RoutePage() {
  return (
    <main className="fixed inset-0 pt-16 pb-20">
      <RouteView />
    </main>
  )
}
```

- [ ] **Step 4: Add /route to App.tsx and BottomNav**

In `App.tsx`, add the route import and route:

```typescript
import { RoutePage } from './pages/RoutePage'

// Inside Routes, add:
<Route path="/route" element={<RoutePage />} />
```

In `BottomNav.tsx`, add a route tab between MAP and FEED. Add a nav item with icon `route` and label `ROUTE` linking to `/route`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/route/ frontend/src/pages/RoutePage.tsx frontend/src/App.tsx frontend/src/components/layout/BottomNav.tsx
git commit -m "feat: route planner UI with Google Maps export"
```

---

## Artem / Dev 2 (Fullstack) — Route Engine + Historical Data + Area Detection + Crime Scores + Deploy

### Task 2.1: Safe Route API Endpoint

**Files:**
- Create: `backend/routers/routes.py`
- Create: `backend/services/route_engine.py`
- Modify: `backend/main.py`
- Modify: `backend/models/schemas.py`

- [ ] **Step 1: Add route schemas**

Add to `backend/models/schemas.py`:

```python
class RouteRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float

class RouteWaypoint(BaseModel):
    lat: float
    lng: float

class SafeRouteResponse(BaseModel):
    waypoints: list[RouteWaypoint]
    google_maps_url: str
    avoided_events: int
    distance_km: float
```

- [ ] **Step 2: Create route engine**

Write `backend/services/route_engine.py`:

The algorithm:
1. Query all active events in a bounding box around origin→destination
2. Create a grid of waypoints along the direct path
3. For each waypoint, check if it's near a high-severity event
4. If so, shift the waypoint perpendicular to the route to avoid the danger zone
5. Build Google Maps URL from final waypoints

```python
import math
from backend.db import get_supabase
from backend.models.schemas import RouteRequest, RouteWaypoint, SafeRouteResponse


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in km between two points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _build_google_maps_url(waypoints: list[RouteWaypoint]) -> str:
    """Build a Google Maps directions URL with waypoints."""
    if len(waypoints) < 2:
        return ""
    origin = f"{waypoints[0].lat},{waypoints[0].lng}"
    destination = f"{waypoints[-1].lat},{waypoints[-1].lng}"
    url = f"https://www.google.com/maps/dir/{origin}"
    # Add intermediate waypoints
    for wp in waypoints[1:-1]:
        url += f"/{wp.lat},{wp.lng}"
    url += f"/{destination}"
    return url


SEVERITY_DANGER_RADIUS_KM = {
    "low": 0.1,
    "medium": 0.3,
    "high": 0.5,
    "critical": 0.8,
}


async def calculate_safe_route(req: RouteRequest) -> SafeRouteResponse:
    sb = get_supabase()

    # 1. Bounding box with padding
    min_lat = min(req.origin_lat, req.dest_lat) - 0.02
    max_lat = max(req.origin_lat, req.dest_lat) + 0.02
    min_lng = min(req.origin_lng, req.dest_lng) - 0.02
    max_lng = max(req.origin_lng, req.dest_lng) + 0.02

    # 2. Fetch active events in bounding box using RPC
    result = sb.rpc("events_in_area", {
        "area_center": f"SRID=4326;POINT({(min_lng + max_lng) / 2} {(min_lat + max_lat) / 2})",
        "radius_km": _haversine(min_lat, min_lng, max_lat, max_lng),
    }).execute()

    events = result.data or []

    # 3. Generate waypoints along direct path
    num_points = 10
    waypoints: list[RouteWaypoint] = []
    avoided = 0

    for i in range(num_points + 1):
        t = i / num_points
        lat = req.origin_lat + t * (req.dest_lat - req.origin_lat)
        lng = req.origin_lng + t * (req.dest_lng - req.origin_lng)

        # Check proximity to dangerous events
        shifted = False
        for ev in events:
            ev_lat = ev.get("lat", 0)
            ev_lng = ev.get("lng", 0)
            severity = ev.get("severity", "medium")
            danger_radius = SEVERITY_DANGER_RADIUS_KM.get(severity, 0.3)

            dist = _haversine(lat, lng, ev_lat, ev_lng)
            if dist < danger_radius:
                # Shift perpendicular to route direction
                dx = req.dest_lng - req.origin_lng
                dy = req.dest_lat - req.origin_lat
                length = math.sqrt(dx * dx + dy * dy) or 1
                # Perpendicular vector (normalized) * offset in degrees (~0.005 deg ≈ 500m)
                offset = 0.005
                perp_lat = -dx / length * offset
                perp_lng = dy / length * offset
                lat += perp_lat
                lng += perp_lng
                avoided += 1
                shifted = True
                break

        waypoints.append(RouteWaypoint(lat=round(lat, 6), lng=round(lng, 6)))

    total_distance = sum(
        _haversine(waypoints[i].lat, waypoints[i].lng, waypoints[i + 1].lat, waypoints[i + 1].lng)
        for i in range(len(waypoints) - 1)
    )

    return SafeRouteResponse(
        waypoints=waypoints,
        google_maps_url=_build_google_maps_url(waypoints),
        avoided_events=avoided,
        distance_km=round(total_distance, 2),
    )
```

- [ ] **Step 3: Create route router**

Write `backend/routers/routes.py`:

```python
from fastapi import APIRouter
from backend.models.schemas import RouteRequest, SafeRouteResponse
from backend.services.route_engine import calculate_safe_route

router = APIRouter(prefix="/api/routes", tags=["routes"])


@router.post("/safe", response_model=SafeRouteResponse)
async def get_safe_route(req: RouteRequest):
    return await calculate_safe_route(req)
```

- [ ] **Step 4: Register router in main.py**

In `backend/main.py`, add:

```python
from backend.routers.routes import router as routes_router

app.include_router(routes_router)
```

- [ ] **Step 5: Test endpoint manually**

```bash
cd backend && uvicorn main:app --reload
```

```bash
curl -X POST http://localhost:8000/api/routes/safe \
  -H "Content-Type: application/json" \
  -d '{"origin_lat": 41.882, "origin_lng": -87.631, "dest_lat": 41.900, "dest_lng": -87.625}'
```

Expected: JSON with waypoints array and google_maps_url string.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/routes.py backend/services/route_engine.py backend/main.py backend/models/schemas.py
git commit -m "feat: safe route engine with Google Maps URL export"
```

---

### Task 2.2: Events With Coordinates RPC

**Files:**
- Supabase migration (via MCP or SQL)

The frontend needs lat/lng as plain numbers, but PostGIS stores geometry. Create an RPC that returns events with extracted coordinates.

- [ ] **Step 1: Apply migration to add events_with_coords view**

Run this SQL in Supabase:

```sql
create or replace function public.events_with_coords(
  max_rows int default 200
)
returns table (
  id uuid,
  area_id uuid,
  title text,
  description text,
  threat_type public.threat_type,
  severity public.severity_level,
  status public.event_status,
  occurred_at timestamptz,
  lat double precision,
  lng double precision,
  location_label text,
  source_type text,
  source_url text,
  relevance_score int,
  comment_count int,
  created_at timestamptz
) language sql stable as $$
  select
    e.id, e.area_id, e.title, e.description,
    e.threat_type, e.severity, e.status, e.occurred_at,
    ST_Y(e.location::geometry) as lat,
    ST_X(e.location::geometry) as lng,
    e.location_label, e.source_type, e.source_url,
    e.relevance_score, e.comment_count, e.created_at
  from public.events e
  where e.status = 'active'
  order by e.occurred_at desc
  limit max_rows;
$$;
```

- [ ] **Step 2: Commit migration file**

```bash
git add supabase/
git commit -m "feat: events_with_coords RPC for frontend lat/lng access"
```

---

### Task 2.3: Auto Area Detection Endpoint

**Files:**
- Create: `backend/services/geocoding.py`
- Modify: `backend/routers/areas.py`

- [ ] **Step 1: Create geocoding service**

Write `backend/services/geocoding.py`:

```python
from backend.db import get_supabase


async def detect_area_from_coords(lat: float, lng: float) -> dict | None:
    """Find the nearest area to given coordinates, or return None."""
    sb = get_supabase()

    result = sb.rpc("find_nearest_area", {
        "user_point": f"SRID=4326;POINT({lng} {lat})",
    }).execute()

    if result.data and len(result.data) > 0:
        return result.data[0]
    return None
```

- [ ] **Step 2: Add detect endpoint to areas router**

Add to `backend/routers/areas.py`:

```python
from backend.services.geocoding import detect_area_from_coords

@router.get("/detect")
async def detect_area(lat: float, lng: float):
    """Auto-detect area from coordinates."""
    area = await detect_area_from_coords(lat, lng)
    if not area:
        return {"area": None, "message": "No monitored area found near your location"}
    return {"area": area}
```

- [ ] **Step 3: Commit**

```bash
git add backend/services/geocoding.py backend/routers/areas.py
git commit -m "feat: auto area detection from GPS coordinates"
```

---

### Task 2.4: Historical Data Import (ACLED)

**Files:**
- Create: `backend/services/historical_import.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create historical importer**

Write `backend/services/historical_import.py`:

```python
import httpx
import logging
from datetime import datetime, timedelta
from backend.db import get_supabase

logger = logging.getLogger(__name__)

ACLED_API_URL = "https://api.acleddata.com/acled/read"

ACLED_TO_THREAT_TYPE = {
    "Battles": "crime",
    "Violence against civilians": "crime",
    "Explosions/Remote violence": "crime",
    "Riots": "disturbance",
    "Protests": "disturbance",
    "Strategic developments": "infrastructure",
}

ACLED_SEVERITY_MAP = {
    0: "low",
    1: "medium",
    2: "medium",
    3: "high",
    4: "high",
    5: "critical",
}


async def import_acled_data(
    country: str = "United States",
    days_back: int = 90,
    limit: int = 500,
):
    """Bulk import historical events from ACLED API."""
    sb = get_supabase()

    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    params = {
        "country": country,
        "event_date": f"{since}|{datetime.utcnow().strftime('%Y-%m-%d')}",
        "event_date_where": "BETWEEN",
        "limit": limit,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(ACLED_API_URL, params=params)
        if resp.status_code != 200:
            logger.error(f"ACLED API error: {resp.status_code}")
            return 0

        data = resp.json().get("data", [])

    imported = 0
    for event in data:
        lat = event.get("latitude")
        lng = event.get("longitude")
        if not lat or not lng:
            continue

        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except (ValueError, TypeError):
            continue

        event_type = event.get("event_type", "")
        threat_type = ACLED_TO_THREAT_TYPE.get(event_type, "disturbance")

        fatalities = int(event.get("fatalities", 0))
        severity = ACLED_SEVERITY_MAP.get(min(fatalities, 5), "medium")

        event_date = event.get("event_date", datetime.utcnow().isoformat())

        title = event.get("event_type", "Incident")
        notes = event.get("notes", "")
        description = notes[:500] if notes else None
        source = event.get("source", "ACLED")

        # Find matching area
        area_result = sb.rpc("find_nearest_area", {
            "user_point": f"SRID=4326;POINT({lng_f} {lat_f})",
        }).execute()

        area_id = None
        if area_result.data and len(area_result.data) > 0:
            area_id = area_result.data[0].get("id")

        row = {
            "title": title[:200],
            "description": description,
            "threat_type": threat_type,
            "severity": severity,
            "status": "active",
            "occurred_at": event_date,
            "location": f"SRID=4326;POINT({lng_f} {lat_f})",
            "location_label": event.get("location", None),
            "source_type": "acled",
            "source_url": None,
            "relevance_score": min(50 + fatalities * 10, 100),
            "area_id": area_id,
        }

        try:
            sb.table("events").insert(row).execute()
            imported += 1
        except Exception as e:
            logger.warning(f"Failed to insert ACLED event: {e}")

    logger.info(f"Imported {imported} ACLED events")
    return imported
```

- [ ] **Step 2: Add import trigger on startup**

In `backend/main.py`, add to the lifespan function (after scraper setup):

```python
from backend.services.historical_import import import_acled_data

# Inside lifespan, after scraper setup:
# One-time historical import on first boot
try:
    count = await import_acled_data(days_back=90, limit=500)
    logger.info(f"Historical import: {count} events from ACLED")
except Exception as e:
    logger.warning(f"Historical import failed: {e}")
```

- [ ] **Step 3: Test the import**

```bash
cd backend && python -c "import asyncio; from services.historical_import import import_acled_data; print(asyncio.run(import_acled_data(limit=10)))"
```

Expected: Returns number of imported events (may be 0 if ACLED requires API key — adjust auth params as needed).

- [ ] **Step 4: Commit**

```bash
git add backend/services/historical_import.py backend/main.py
git commit -m "feat: ACLED historical data import pipeline"
```

---

### Task 2.5: Deploy

**Files:**
- Frontend deploy config
- Backend deploy config

- [ ] **Step 1: Build frontend**

```bash
cd frontend && npm run build
```

Verify `dist/` directory is created.

- [ ] **Step 2: Deploy frontend to Cloudflare Pages**

```bash
npx wrangler pages deploy dist --project-name alerthood
```

Set environment variables in Cloudflare dashboard:
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_URL` (backend URL)

- [ ] **Step 3: Deploy backend**

For FastAPI Cloud or any hosting (Railway, Render, Fly.io):

Create `backend/Procfile`:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Create `backend/runtime.txt`:
```
python-3.11
```

Set env vars on host:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_JWT_SECRET`
- `CORS_ORIGINS` (set to deployed frontend URL)

- [ ] **Step 4: Verify deployed app**

Open deployed frontend URL. Check:
- Auth page loads
- Google OAuth redirects correctly
- Map loads with real data
- Feed shows events

- [ ] **Step 5: Commit deploy config**

```bash
git add backend/Procfile backend/runtime.txt
git commit -m "chore: add deploy config for backend"
```

---

### Task 2.6: Neighborhood Crime & Safety Scores

**Files:**
- Create: `backend/services/neighborhood_scores.py`
- Create: `backend/routers/scores.py`
- Modify: `backend/main.py`
- Modify: `backend/models/schemas.py`
- Supabase migration: add `safety_score` columns to `areas` table

**Concept:** Each neighborhood gets a composite safety score derived from:
1. **Crime count** — number of crime-type events in the area (from our events table)
2. **Crime rate** — crimes per km² normalized across all areas
3. **Poverty index** — external data from Census/World Bank API (or seeded static data for MVP)
4. **Composite score** — weighted formula: `100 - (crime_rate_pct * 0.6 + poverty_pct * 0.2 + recency_weight * 0.2)`

- [ ] **Step 1: Add safety score columns via migration**

Run this SQL in Supabase:

```sql
-- Add safety scoring columns to areas
alter table public.areas
  add column if not exists crime_count int not null default 0,
  add column if not exists crime_rate_per_km2 numeric(8,2) not null default 0,
  add column if not exists poverty_index numeric(5,2) not null default 0,
  add column if not exists safety_score numeric(5,2) not null default 50,
  add column if not exists score_updated_at timestamptz;

-- Seed poverty index for existing areas (static MVP data — real data from Census API later)
update public.areas set poverty_index = case slug
  when 'chicago-west-loop' then 12.5
  when 'chicago-river-north' then 8.2
  when 'chicago-south-side' then 28.4
  when 'nyc-manhattan' then 15.6
  when 'nyc-brooklyn' then 19.8
  when 'la-downtown' then 22.1
  when 'la-hollywood' then 14.3
  when 'london-central' then 11.0
  when 'tokyo-shibuya' then 5.2
  else 15.0
end;
```

- [ ] **Step 2: Add score schemas**

Add to `backend/models/schemas.py`:

```python
class NeighborhoodScore(BaseModel):
    area_id: str
    area_name: str
    crime_count: int
    crime_rate_per_km2: float
    poverty_index: float
    safety_score: float
    score_updated_at: str | None

class NeighborhoodScoresResponse(BaseModel):
    scores: list[NeighborhoodScore]
    computed_at: str
```

- [ ] **Step 3: Create neighborhood scoring service**

Write `backend/services/neighborhood_scores.py`:

```python
import logging
import math
from datetime import datetime, timedelta
from backend.db import get_supabase

logger = logging.getLogger(__name__)


async def compute_area_crime_stats(area_id: str, radius_km: float = 5.0) -> dict:
    """Count crimes in an area and compute crime rate per km²."""
    sb = get_supabase()

    # Count crime-type events in this area from last 90 days
    since = (datetime.utcnow() - timedelta(days=90)).isoformat()

    result = sb.table("events") \
        .select("id", count="exact") \
        .eq("area_id", area_id) \
        .eq("threat_type", "crime") \
        .gte("occurred_at", since) \
        .execute()

    crime_count = result.count or 0
    area_km2 = math.pi * radius_km ** 2
    crime_rate = crime_count / area_km2 if area_km2 > 0 else 0

    return {
        "crime_count": crime_count,
        "crime_rate_per_km2": round(crime_rate, 2),
    }


def compute_safety_score(
    crime_rate_per_km2: float,
    poverty_index: float,
    max_crime_rate: float = 10.0,
) -> float:
    """
    Composite safety score 0-100 (higher = safer).

    Formula:
    - crime_rate_pct = min(crime_rate / max_crime_rate, 1.0) * 100
    - poverty_pct = min(poverty_index / 50, 1.0) * 100
    - recency_weight = crime_rate_pct (crimes that happened recently weigh more)
    - score = 100 - (crime_rate_pct * 0.6 + poverty_pct * 0.2 + recency_weight * 0.2)
    """
    crime_rate_pct = min(crime_rate_per_km2 / max_crime_rate, 1.0) * 100
    poverty_pct = min(poverty_index / 50.0, 1.0) * 100
    recency_weight = crime_rate_pct  # same signal, double-weighted intentionally

    score = 100 - (crime_rate_pct * 0.6 + poverty_pct * 0.2 + recency_weight * 0.2)
    return round(max(0, min(100, score)), 2)


async def refresh_all_scores() -> int:
    """Recompute safety scores for all active areas. Returns count updated."""
    sb = get_supabase()

    areas = sb.table("areas").select("id, name, radius_km, poverty_index") \
        .eq("is_active", True).execute()

    if not areas.data:
        return 0

    # Find max crime rate for normalization
    stats = []
    for area in areas.data:
        s = await compute_area_crime_stats(area["id"], float(area.get("radius_km", 5)))
        stats.append((area, s))

    max_rate = max((s["crime_rate_per_km2"] for _, s in stats), default=1.0) or 1.0

    updated = 0
    now = datetime.utcnow().isoformat()

    for area, s in stats:
        score = compute_safety_score(
            s["crime_rate_per_km2"],
            float(area.get("poverty_index", 0)),
            max_crime_rate=max_rate,
        )

        sb.table("areas").update({
            "crime_count": s["crime_count"],
            "crime_rate_per_km2": s["crime_rate_per_km2"],
            "safety_score": score,
            "score_updated_at": now,
        }).eq("id", area["id"]).execute()

        updated += 1

    logger.info(f"Refreshed safety scores for {updated} areas")
    return updated
```

- [ ] **Step 4: Create scores router**

Write `backend/routers/scores.py`:

```python
from datetime import datetime
from fastapi import APIRouter
from backend.db import get_supabase
from backend.models.schemas import NeighborhoodScore, NeighborhoodScoresResponse
from backend.services.neighborhood_scores import refresh_all_scores

router = APIRouter(prefix="/api/scores", tags=["scores"])


@router.get("", response_model=NeighborhoodScoresResponse)
async def get_neighborhood_scores():
    """Get safety scores for all active areas."""
    sb = get_supabase()

    result = sb.table("areas") \
        .select("id, name, crime_count, crime_rate_per_km2, poverty_index, safety_score, score_updated_at") \
        .eq("is_active", True) \
        .order("safety_score", desc=False) \
        .execute()

    scores = [
        NeighborhoodScore(
            area_id=row["id"],
            area_name=row["name"],
            crime_count=row.get("crime_count", 0),
            crime_rate_per_km2=float(row.get("crime_rate_per_km2", 0)),
            poverty_index=float(row.get("poverty_index", 0)),
            safety_score=float(row.get("safety_score", 50)),
            score_updated_at=row.get("score_updated_at"),
        )
        for row in (result.data or [])
    ]

    return NeighborhoodScoresResponse(
        scores=scores,
        computed_at=datetime.utcnow().isoformat(),
    )


@router.post("/refresh")
async def refresh_scores():
    """Recompute all neighborhood safety scores."""
    count = await refresh_all_scores()
    return {"updated": count}
```

- [ ] **Step 5: Register router + add periodic refresh**

In `backend/main.py`, add:

```python
from backend.routers.scores import router as scores_router
from backend.services.neighborhood_scores import refresh_all_scores

app.include_router(scores_router)

# Inside the scraper loop (runs every 15 min), add after scraper call:
await refresh_all_scores()
```

- [ ] **Step 6: Test endpoint**

```bash
cd backend && uvicorn main:app --reload
```

```bash
# Refresh scores
curl -X POST http://localhost:8000/api/scores/refresh

# Get scores
curl http://localhost:8000/api/scores
```

Expected: JSON with `scores` array, each area having `crime_count`, `crime_rate_per_km2`, `poverty_index`, `safety_score`.

- [ ] **Step 7: Commit**

```bash
git add backend/services/neighborhood_scores.py backend/routers/scores.py backend/main.py backend/models/schemas.py
git commit -m "feat: neighborhood crime rates + safety scores (crime count, poverty index, composite score)"
```

---

## Egor / Dev 3 (Newbie) — Profile + Notifications + QA

### Task 3.1: Wire Profile Page to Real Data

**Files:**
- Create: `frontend/src/hooks/useProfile.ts`
- Modify: `frontend/src/components/profile/ProfileView.tsx`

- [ ] **Step 1: Create useProfile hook**

Write `frontend/src/hooks/useProfile.ts`:

```typescript
import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'
import { useAuth } from './useAuth'
import type { UserProfile, MonitoredArea } from '../types'
import { MOCK_PROFILE } from '../data/mock'

export function useProfile() {
  const { user } = useAuth()
  const [profile, setProfile] = useState<UserProfile>(MOCK_PROFILE)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) {
      setLoading(false)
      return
    }

    async function fetchProfile() {
      // Fetch profile
      const { data: profileData } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', user!.id)
        .single()

      // Fetch subscriptions with area details
      const { data: subscriptions } = await supabase
        .from('user_area_subscriptions')
        .select('*, areas(*)')
        .eq('user_id', user!.id)

      const areas: MonitoredArea[] = (subscriptions || []).map((sub: Record<string, unknown>) => {
        const area = sub.areas as Record<string, unknown>
        return {
          id: sub.id as string,
          name: (sub.label as string) || 'HOME',
          radiusMiles: 5,
          neighborhood: (area?.name as string) || 'Unknown',
          lat: 0,
          lng: 0,
          isActive: true,
          notifyCrime: sub.notification_crime as boolean,
          notifyUtility: sub.notification_infrastructure as boolean,
          notifyNatural: sub.notification_natural as boolean,
          notifyDisturbance: sub.notification_disturbance as boolean,
        }
      })

      if (profileData) {
        setProfile({
          name: profileData.display_name || profileData.username || '',
          email: user!.email || '',
          karma: 0,
          karmaWeekly: 0,
          trustScore: 0,
          streakDays: 0,
          badges: MOCK_PROFILE.badges,
          areas: areas.length > 0 ? areas : MOCK_PROFILE.areas,
        })
      }

      setLoading(false)
    }

    fetchProfile()
  }, [user])

  return { profile, loading }
}
```

- [ ] **Step 2: Update ProfileView to use real data**

In `frontend/src/components/profile/ProfileView.tsx`, replace mock import:

```typescript
import { useProfile } from '../../hooks/useProfile'
import { useAuth } from '../../hooks/useAuth'
import { MetricsBento } from './MetricsBento'
import { BadgeGrid } from './BadgeGrid'
import { MonitoredAreaCard } from './MonitoredAreaCard'

export function ProfileView() {
  const { profile, loading } = useProfile()
  const { signOut } = useAuth()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="font-headline text-on-surface-variant uppercase tracking-widest text-sm">Loading...</p>
      </div>
    )
  }

  return (
    <div className="px-4 max-w-2xl mx-auto space-y-8 mt-6">
      <section className="flex flex-col items-center pt-4">
        <div className="w-24 h-24 bg-surface-container border-4 border-black shadow-hard rounded-full flex items-center justify-center mb-4 overflow-hidden">
          <span
            className="material-symbols-outlined text-5xl text-primary"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            account_circle
          </span>
        </div>
        <h2 className="font-headline text-3xl font-bold uppercase tracking-tight">{profile.name}</h2>
        <p className="font-body text-on-surface-variant text-sm">{profile.email}</p>
      </section>

      <MetricsBento
        karma={profile.karma}
        karmaWeekly={profile.karmaWeekly}
        trustScore={profile.trustScore}
        streakDays={profile.streakDays}
      />

      <BadgeGrid badges={profile.badges} />

      <section className="space-y-4">
        <h3 className="font-headline text-xl font-bold uppercase tracking-tight flex items-center gap-2">
          <span className="w-6 h-1 bg-secondary inline-block" />
          MONITORED AREAS
        </h3>
        {profile.areas.map((area, i) => (
          <MonitoredAreaCard
            key={area.id}
            area={area}
            onDelete={i > 0 ? (id) => console.log('delete', id) : undefined}
          />
        ))}
      </section>

      <section className="pb-12">
        <button
          onClick={signOut}
          className="w-full py-4 border-2 border-black font-headline font-bold text-error uppercase tracking-widest hover:bg-error-container hover:text-white transition-none active:translate-x-[2px] active:translate-y-[2px] active:shadow-none"
        >
          LOGOUT SESSION
        </button>
      </section>
    </div>
  )
}
```

- [ ] **Step 3: Verify profile loads**

```bash
cd frontend && npm run dev
```

Sign in → navigate to Profile → verify name/email from Supabase appear.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useProfile.ts frontend/src/components/profile/ProfileView.tsx
git commit -m "feat: wire profile page to Supabase user data"
```

---

### Task 3.2: Notification Bell + Dropdown

**Files:**
- Create: `frontend/src/components/layout/NotificationBell.tsx`
- Modify: `frontend/src/components/layout/TopBar.tsx`

- [ ] **Step 1: Create NotificationBell component**

Write `frontend/src/components/layout/NotificationBell.tsx`:

```typescript
import { useState, useEffect, useRef } from 'react'
import { supabase } from '../../lib/supabase'
import { useAuth } from '../../hooks/useAuth'
import type { Notification } from '../../types'

export function NotificationBell() {
  const { user } = useAuth()
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const unreadCount = notifications.filter((n) => !n.is_read).length

  useEffect(() => {
    if (!user) return

    async function fetchNotifications() {
      const { data } = await supabase
        .from('notifications')
        .select('*')
        .eq('user_id', user!.id)
        .order('created_at', { ascending: false })
        .limit(20)
      if (data) setNotifications(data as Notification[])
    }

    fetchNotifications()

    // Realtime
    const channel = supabase
      .channel('notifications')
      .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'notifications',
        filter: `user_id=eq.${user.id}`,
      }, (payload) => {
        setNotifications((prev) => [payload.new as Notification, ...prev])
      })
      .subscribe()

    return () => { supabase.removeChannel(channel) }
  }, [user])

  const markAllRead = async () => {
    if (!user) return
    await supabase
      .from('notifications')
      .update({ is_read: true })
      .eq('user_id', user.id)
      .eq('is_read', false)
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
  }

  // Close on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2"
        aria-label="Notifications"
      >
        <span className="material-symbols-outlined text-2xl">notifications</span>
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-primary-container border-2 border-black text-on-primary-container text-[10px] font-bold flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 max-h-96 overflow-y-auto bg-surface-container border-[3px] border-black shadow-hard rounded-xl z-50">
          <div className="flex items-center justify-between px-4 py-3 border-b-2 border-black">
            <h4 className="font-headline font-bold text-sm uppercase tracking-widest">Alerts</h4>
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                className="font-body text-xs text-primary underline"
              >
                Mark all read
              </button>
            )}
          </div>

          {notifications.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <p className="font-body text-sm text-on-surface-variant">No notifications yet</p>
            </div>
          ) : (
            notifications.map((n) => (
              <div
                key={n.id}
                className={`px-4 py-3 border-b border-outline-variant ${!n.is_read ? 'bg-surface-container-low' : ''}`}
              >
                <p className="font-headline font-bold text-xs uppercase tracking-wide">{n.title}</p>
                {n.body && <p className="font-body text-xs text-on-surface-variant mt-1">{n.body}</p>}
                <p className="font-label text-[10px] text-on-surface-variant mt-1">
                  {new Date(n.created_at).toLocaleString()}
                </p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Wire NotificationBell into TopBar**

In `frontend/src/components/layout/TopBar.tsx`, replace the static notification icon with:

```typescript
import { NotificationBell } from './NotificationBell'

// Replace the existing notification button/icon with:
<NotificationBell />
```

Remove the `notificationCount` prop from TopBar since the bell manages its own state.

- [ ] **Step 3: Update App.tsx to remove notificationCount prop**

In `App.tsx`, change:
```typescript
<TopBar notificationCount={3} />
```
to:
```typescript
<TopBar />
```

- [ ] **Step 4: Verify bell works**

```bash
cd frontend && npm run dev
```

Sign in → check notification bell appears → click to open dropdown.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/NotificationBell.tsx frontend/src/components/layout/TopBar.tsx frontend/src/App.tsx
git commit -m "feat: notification bell with realtime updates"
```

---

### Task 3.3: Area Subscription Flow

**Files:**
- Create: `frontend/src/hooks/useAreas.ts`
- Modify: `frontend/src/components/profile/ProfileView.tsx`

- [ ] **Step 1: Create useAreas hook**

Write `frontend/src/hooks/useAreas.ts`:

```typescript
import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'
import { apiFetch } from '../lib/api'
import { useAuth } from './useAuth'

interface Area {
  id: string
  name: string
  city: string
  slug: string
}

export function useAreas() {
  const { user } = useAuth()
  const [areas, setAreas] = useState<Area[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchAreas() {
      const { data } = await supabase
        .from('areas')
        .select('id, name, city, slug')
        .eq('is_active', true)
        .order('name')
      if (data) setAreas(data)
      setLoading(false)
    }
    fetchAreas()
  }, [])

  const subscribe = async (areaId: string, label: string = 'Home') => {
    const res = await apiFetch('/api/areas/subscribe', {
      method: 'POST',
      body: JSON.stringify({ area_id: areaId, label }),
    })
    return res.ok
  }

  return { areas, loading, subscribe }
}
```

- [ ] **Step 2: Add subscribe button to ProfileView**

In the monitored areas section of `ProfileView.tsx`, after the area cards, add:

```typescript
import { useAreas } from '../../hooks/useAreas'

// Inside ProfileView, after area cards:
const { areas: availableAreas, subscribe } = useAreas()

// Add "Add Area" button if user has < 2 areas:
{profile.areas.length < 2 && (
  <button
    onClick={async () => {
      if (availableAreas.length > 0) {
        await subscribe(availableAreas[0].id, 'Work')
        window.location.reload()
      }
    }}
    className="w-full py-3 border-2 border-black border-dashed font-headline font-bold text-sm uppercase tracking-widest text-on-surface-variant active:translate-x-[1px] active:translate-y-[1px] transition-none"
  >
    + ADD AREA (1 slot remaining)
  </button>
)}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useAreas.ts frontend/src/components/profile/ProfileView.tsx
git commit -m "feat: area subscription flow on profile page"
```

---

### Task 3.4: QA — Full Flow Testing

**No files to create — testing checklist.**

- [ ] **Step 1: Test auth flow**

1. Open app → should redirect to `/auth`
2. Sign up with email/password → should redirect to `/map`
3. Refresh page → should stay logged in
4. Sign out → should redirect to `/auth`
5. Sign in with Google → should redirect to `/map`

- [ ] **Step 2: Test map**

1. Map loads with CartoDB tiles
2. Geolocation prompt appears (allow it)
3. Map centers on user location
4. Event markers appear (real or mock)
5. Click marker → bottom sheet appears
6. Heatmap overlay visible around event clusters

- [ ] **Step 3: Test feed**

1. Feed shows threat cards
2. Filter buttons work (ALL/CRIME/UTILITY/NATURAL/DISTURBANCE)
3. "View Map" button navigates to map

- [ ] **Step 4: Test route planner**

1. Navigate to Route tab
2. Tap map to set origin
3. Tap map to set destination
4. Click "Find Safe Route"
5. Route line appears on map
6. Bottom sheet shows distance + avoided threats
7. "Open in Google Maps" opens correct URL

- [ ] **Step 5: Test profile**

1. Profile shows user name/email from Supabase
2. Monitored areas display
3. Logout works

- [ ] **Step 6: Test notifications**

1. Bell shows in top bar
2. Click bell → dropdown opens
3. Notifications from DB appear
4. "Mark all read" clears unread count

- [ ] **Step 7: Mobile viewport testing**

1. Open Chrome DevTools → toggle device toolbar
2. Test on iPhone 14 Pro viewport (393 x 852)
3. Check all pages fit without horizontal scroll
4. Bottom nav doesn't overlap content
5. Inputs on auth page are usable on mobile keyboard

- [ ] **Step 8: File any bugs found as GitHub issues**

```bash
gh issue create --title "Bug: [description]" --body "[steps to reproduce]"
```

---

## Timeline & Dependencies

```
HOUR 0-2:   Olexii: Task 1.1 + 1.2 (auth)
             Artem:  Task 2.1 (route API)
             Egor:   Read codebase, set up local env

HOUR 2-4:   Olexii: Task 1.3 (map wiring + geolocation)
             Artem:  Task 2.2 + 2.3 (RPC + area detect)
             Egor:   Task 3.1 (profile wiring) [BLOCKED BY: Task 1.1]

HOUR 4-8:   Olexii: Task 1.4 + 1.5 (feed + heatmap)
             Artem:  Task 2.4 (historical ACLED import) + Task 2.6 (neighborhood crime scores)
             Egor:   Task 3.2 (notification bell)

HOUR 8-12:  Olexii: Task 1.6 (route UI) [NEEDS: Task 2.1]
             Artem:  Continue 2.4/2.6 + start 2.5 (deploy prep)
             Egor:   Task 3.3 (area subscription)

HOUR 12-16: Olexii: Integration fixes + polish
             Artem:  Task 2.5 (deploy)
             Egor:   Task 3.4 (QA)

HOUR 16-18: Feature freeze. Bug fixes only. Final deploy.
```
