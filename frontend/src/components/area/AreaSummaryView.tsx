import { useEffect, useState } from 'react'
import { useAreaDetect } from '../../hooks/useAreas'
import { useScores } from '../../hooks/useScores'
import { supabase } from '../../lib/supabase'
import type { Threat, ThreatCategory, ThreatSeverity } from '../../types'
import { SafetyScoreGauge } from './SafetyScoreGauge'
import { ActiveAlertCard } from './ActiveAlertCard'
import { MiniHeatmap } from './MiniHeatmap'
import { RecentIncidentsList } from './RecentIncidentsList'
import { AIBriefPlaceholder } from './AIBriefPlaceholder'

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

  const [events, setEvents] = useState<Threat[]>([])
  const [eventsLoading, setEventsLoading] = useState(false)

  // Request geolocation on mount
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

  // Detect area once we have coords
  useEffect(() => {
    if (coords) detect(coords.lat, coords.lng)
  }, [coords, detect])

  // Load events once area is known
  useEffect(() => {
    if (!area) return
    let cancelled = false
    setEventsLoading(true)

    supabase
      .rpc('events_with_coords', { max_rows: 20 })
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
  }, [area])

  const isLoading = geoState === 'requesting' || areaLoading || scoresLoading || eventsLoading

  const areaScore = area
    ? scores.find((s) => s.area_id === area.id) ?? null
    : null

  const score = areaScore?.safety_score ?? 50
  const risk = getRiskLevel(score)

  // Active alert: high/critical from last 24h
  const activeAlert = events.find(
    (e) => (e.severity === 'HIGH' || e.severity === 'CRITICAL') && e.minutesAgo <= 1440,
  ) ?? null

  // Recent incidents: last 48h, up to 5
  const recentEvents = events
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
  if (isLoading) {
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

  // ─── No area found ────────────────────────────────────────────────────────
  if (!area) {
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

  const areaName = (area.name as string).toUpperCase()

  // ─── Main content ─────────────────────────────────────────────────────────
  return (
    <div className="px-4 max-w-2xl mx-auto space-y-6 pb-4">
      {/* 5.1 Area Header */}
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

      {/* 5.2 Safety Score Hero */}
      <SafetyScoreGauge
        score={Math.round(score)}
        updatedAt={areaScore?.score_updated_at ?? null}
      />

      {/* 5.3 Active Alert (conditional) */}
      {activeAlert && <ActiveAlertCard event={activeAlert} />}

      {/* 5.4 Mini Heatmap */}
      <MiniHeatmap center={mapCenter} events={recentEvents} />

      {/* 5.5 Recent Incidents */}
      <RecentIncidentsList events={recentEvents} />

      {/* 5.6 AI Brief Placeholder */}
      <AIBriefPlaceholder />
    </div>
  )
}
