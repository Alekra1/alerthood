import { useEffect, useState } from 'react'
import { useAreaDetect } from '../../hooks/useAreas'
import { useScores } from '../../hooks/useScores'
import { useAlertPrefs } from '../../hooks/useAlertPrefs'
import { supabase } from '../../lib/supabase'
import type { Threat, ThreatCategory, ThreatSeverity } from '../../types'
import { SafetyScoreGauge } from './SafetyScoreGauge'
import { ActiveAlertCard } from './ActiveAlertCard'
import { MiniHeatmap } from './MiniHeatmap'
import { RecentIncidentsList } from './RecentIncidentsList'
import { AIAreaBrief } from './AIAreaBrief'

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLng = ((lng2 - lng1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

const THREAT_TYPE_MAP: Record<string, ThreatCategory> = {
  crime: 'CRIME',
  infrastructure: 'UTILITY',
  disturbance: 'DISTURBANCE',
  natural: 'NATURAL',
}

const SEVERITY_PCT: Record<string, number> = {
  low: 25,
  medium: 50,
  high: 75,
  critical: 95,
}

function getRiskLevel(score: number): { label: string; bg: string; text: string } {
  if (score >= 70) return { label: 'LOW RISK', bg: '#4ade80', text: '#14532d' }
  if (score >= 40) return { label: 'MEDIUM RISK', bg: '#FE9400', text: '#633700' }
  return { label: 'HIGH RISK', bg: '#FF5545', text: '#5C0002' }
}

type GeoState = 'idle' | 'requesting' | 'granted' | 'denied'

export function AreaSummaryView() {
  const [geoState, setGeoState] = useState<GeoState>('idle')
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null)

  const { area, detect, loading: areaLoading } = useAreaDetect()
  const { scores, loading: scoresLoading } = useScores()
  const { showNearest } = useAlertPrefs()

  const [events, setEvents] = useState<Threat[]>([])
  const [eventsLoading, setEventsLoading] = useState(false)

  // Start geolocation + events loading in parallel on mount
  useEffect(() => {
    if (!navigator.geolocation) {
      setGeoState('denied')
      return
    }
    setGeoState('requesting')
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude })
        setGeoState('granted')
      },
      () => setGeoState('denied'),
      { timeout: 10000 },
    )
  }, [])

  // Re-fetch events scoped to the detected area via PostGIS boundary containment.
  // Falls back to empty while area is loading — avoids showing cross-city events.
  useEffect(() => {
    if (!area?.id) return
    let cancelled = false
    setEventsLoading(true)

    supabase
      .rpc('events_in_area', { target_area_id: area.id, max_rows: 50 })
      .then(({ data }) => {
        if (cancelled || !data) return
        const now = Date.now()
        const mapped: Threat[] = data.map((e: Record<string, unknown>) => {
          const minutesAgo = Math.max(
            0,
            Math.floor((now - new Date(e.occurred_at as string).getTime()) / 60000),
          )
          return {
            id: e.id as string,
            title: e.title as string,
            category: THREAT_TYPE_MAP[(e.threat_type as string)] ?? 'CRIME',
            severity: (e.severity as string).toUpperCase() as ThreatSeverity,
            severityPct: SEVERITY_PCT[(e.severity as string)] ?? 50,
            location: (e.location_label as string) ?? '',
            lat: (e.lat as number) ?? 0,
            lng: (e.lng as number) ?? 0,
            minutesAgo,
            upvotes: 0,
            downvotes: 0,
            source: (e.source_type as string) ?? '',
            sourceUrl: (e.source_url as string) ?? null,
          }
        })
        setEvents(mapped)
      })
      .finally(() => {
        if (!cancelled) setEventsLoading(false)
      })

    return () => { cancelled = true }
  }, [area?.id])

  // Detect area once we have coords
  useEffect(() => {
    if (coords) detect(coords.lat, coords.lng)
  }, [coords, detect])

  // Only block on geolocation — events and scores load in parallel
  const isBlocked = geoState === 'requesting'

  const areaScore = area
    ? scores.find((s) => s.area_id === area.id) ?? null
    : null

  const score = areaScore?.safety_score ?? 50
  const risk = getRiskLevel(score)

  // Events are already scoped to the detected area via PostGIS (events_in_area).
  // Optionally sort by proximity if showNearest is on; no cross-area filtering needed.
  const localEvents = coords && showNearest
    ? [...events]
        .filter((e) => e.lat && e.lng)
        .sort((a, b) =>
          haversineKm(coords.lat, coords.lng, a.lat, a.lng) -
          haversineKm(coords.lat, coords.lng, b.lat, b.lng),
        )
    : events

  // Active alert: high/critical from last 24h within the area
  const activeAlert = localEvents.find(
    (e) => (e.severity === 'HIGH' || e.severity === 'CRITICAL') && e.minutesAgo <= 1440,
  ) ?? null

  // Recent incidents: last 48h, up to 5, within the area
  const recentEvents = localEvents
    .filter((e) => e.minutesAgo <= 2880)
    .slice(0, 5)

  const mapCenter: [number, number] = coords
    ? [coords.lat, coords.lng]
    : [51.505, -0.09]

  // ─── Location denied state ────────────────────────────────────────────────
  if (geoState === 'denied') {
    return (
      <div className="px-4 max-w-2xl mx-auto mt-16 flex flex-col items-center gap-4 text-center">
        <span className="material-symbols-outlined text-5xl text-on-surface-variant opacity-40">
          location_off
        </span>
        <p className="font-headline font-bold text-xl uppercase tracking-tight text-on-surface">
          Location Required
        </p>
        <p className="font-body text-sm text-on-surface-variant">
          Enable location access to see your neighbourhood summary.
        </p>
      </div>
    )
  }

  // ─── Loading state ────────────────────────────────────────────────────────
  if (isBlocked) {
    return (
      <div className="px-4 max-w-2xl mx-auto mt-24 flex flex-col items-center gap-3">
        <span className="material-symbols-outlined text-4xl text-on-surface-variant opacity-50 animate-pulse">
          radar
        </span>
        <p className="font-headline font-bold text-sm uppercase tracking-widest text-on-surface-variant opacity-60">
          {geoState === 'requesting' ? 'Getting your location…' : 'Loading area data…'}
        </p>
      </div>
    )
  }

  // ─── No area found (geolocation resolved but area detection failed) ────
  if (!area && !areaLoading) {
    return (
      <div className="px-4 max-w-2xl mx-auto mt-24 flex flex-col items-center gap-3 text-center">
        <span className="material-symbols-outlined text-5xl text-on-surface-variant opacity-40">
          location_searching
        </span>
        <p className="font-headline font-bold text-xl uppercase tracking-tight text-on-surface">
          No area found
        </p>
        <p className="font-body text-sm text-on-surface-variant">
          We couldn't find a monitored area near your location.
        </p>
      </div>
    )
  }

  const areaName = area ? (area.name as string).toUpperCase() : null

  // ─── Main content (progressive — shows events before area resolves) ───────
  return (
    <div className="px-4 max-w-2xl mx-auto space-y-6 pb-4">
      {/* 5.1 Area Header */}
      {areaName ? (
        <div className="flex flex-wrap items-center gap-3 pt-2">
          <div>
            <h1 className="font-headline font-bold text-2xl uppercase tracking-tight text-on-surface leading-none">
              {areaName}
            </h1>
          </div>
          <span
            className="flex items-center gap-1.5 font-headline font-bold text-xs uppercase tracking-widest px-3 py-1 rounded-full"
            style={{ backgroundColor: risk.bg, color: risk.text }}
          >
            <span className="w-2 h-2 rounded-full block" style={{ backgroundColor: risk.text }} />
            {risk.label}
          </span>
        </div>
      ) : (
        <div className="pt-2">
          <div className="h-8 w-48 bg-on-surface/5 animate-pulse" />
        </div>
      )}

      {/* 5.2 Safety Score Hero */}
      {area ? (
        <SafetyScoreGauge
          score={Math.round(score)}
          updatedAt={areaScore?.score_updated_at ?? null}
        />
      ) : (
        <div className="h-40 bg-on-surface/5 animate-pulse rounded" />
      )}

      {/* 5.3 Active Alert (conditional) */}
      {!eventsLoading && area && (
        activeAlert
          ? <ActiveAlertCard event={activeAlert} />
          : (
            <div className="flex items-center gap-3 px-4 py-3 rounded border border-on-surface/10 bg-on-surface/5">
              <span className="material-symbols-outlined text-xl text-on-surface-variant opacity-50">check_circle</span>
              <p className="font-body text-sm text-on-surface-variant">No active alerts in your area.</p>
            </div>
          )
      )}

      {/* 5.4 Mini Heatmap */}
      {!eventsLoading && recentEvents.length > 0 && (
        <MiniHeatmap center={mapCenter} events={recentEvents} />
      )}

      {/* 5.5 Recent Incidents */}
      {!eventsLoading && recentEvents.length > 0 && (
        <RecentIncidentsList events={recentEvents} />
      )}
      {eventsLoading && (
        <div className="h-32 bg-on-surface/5 animate-pulse rounded" />
      )}

      {/* 5.6 AI Area Brief — shown as soon as area resolves, score is optional */}
      {area && !eventsLoading && !scoresLoading && (
        <AIAreaBrief
          areaId={area.id}
          areaName={area.name as string}
          safetyScore={score}
          riskLevel={risk.label}
          crimeCount={areaScore?.crime_count ?? 0}
          crimeRatePerKm2={areaScore?.crime_rate_per_km2 ?? 0}
          scoreUpdatedAt={areaScore?.score_updated_at ?? null}
          activeAlert={activeAlert}
          recentEvents={recentEvents}
        />
      )}
    </div>
  )
}
