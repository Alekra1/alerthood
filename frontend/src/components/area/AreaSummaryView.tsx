import { useCallback, useEffect, useRef, useState } from 'react'
import { getCachedUserLocation } from '../../lib/userLocation'
import { apiPost } from '../../lib/api'
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

type GeoState = 'requesting' | 'granted' | 'denied' | 'unavailable'

export function AreaSummaryView() {
  const [geoState, setGeoState] = useState<GeoState>('requesting')
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null)

  const { area, detect, loading: areaLoading, error: areaError } = useAreaDetect()
  const { scores, loading: scoresLoading, error: scoresError, refetch: refetchScores } = useScores()
  const { showNearest } = useAlertPrefs()
  const refreshTriggered = useRef(false)

  const [events, setEvents] = useState<Threat[]>([])
  const [eventsLoading, setEventsLoading] = useState(false)
  const [eventsError, setEventsError] = useState<string | null>(null)

  const requestGeo = useCallback(() => {
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
      (err) => {
        // PERMISSION_DENIED = 1, POSITION_UNAVAILABLE = 2, TIMEOUT = 3
        setGeoState(err.code === 1 ? 'denied' : 'unavailable')
      },
      { timeout: 10000 },
    )
  }, [])

  // Mount: use cached location from map view if available, otherwise request fresh
  useEffect(() => {
    const cached = getCachedUserLocation()
    if (cached) {
      setCoords(cached)
      setGeoState('granted')
      return
    }

    let cancelled = false
    if (!navigator.geolocation) {
      setGeoState('denied')
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        if (cancelled) return
        setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude })
        setGeoState('granted')
      },
      (err) => {
        if (cancelled) return
        setGeoState(err.code === 1 ? 'denied' : 'unavailable')
      },
      { timeout: 10000 },
    )
    return () => { cancelled = true }
  }, [])

  // Re-fetch events scoped to the detected area via PostGIS boundary containment.
  // Falls back to empty while area is loading — avoids showing cross-city events.
  useEffect(() => {
    if (!area?.id) return
    let cancelled = false
    setEventsLoading(true)

    supabase
      .rpc('events_in_area', { target_area_id: area.id, max_rows: 50 })
      .then(({ data, error }) => {
        if (cancelled) return
        if (error) { setEventsError(error.message); return }
        if (!data) return
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
      .catch((err: Error) => {
        if (!cancelled) setEventsError(err.message)
      })
      .finally(() => {
        if (!cancelled) setEventsLoading(false)
      })

    return () => { cancelled = true }
  }, [area?.id])

  const detectInitiated = useRef(false)

  // Detect area once we have coords
  useEffect(() => {
    if (coords) {
      detectInitiated.current = true
      detect(coords.lat, coords.lng)
    }
  }, [coords, detect])

  const areaScore = area
    ? scores.find((s) => s.area_id === area.id) ?? null
    : null

  // Use null when the score has never been computed (no score_updated_at),
  // so we never show the DB default of 50 as "MEDIUM RISK".
  const score: number | null =
    areaScore?.score_updated_at ? areaScore.safety_score : null
  const risk = score !== null ? getRiskLevel(score) : null

  // When the area is loaded but the score hasn't been computed yet,
  // trigger a backend refresh once, then poll every 5 s until it resolves.
  useEffect(() => {
    if (!area || score !== null) return
    if (!refreshTriggered.current) {
      refreshTriggered.current = true
      apiPost('/api/scores/refresh', {}).catch(() => {/* best-effort */})
    }
    const id = setInterval(refetchScores, 5000)
    return () => clearInterval(id)
  }, [area, score, refetchScores])

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

  const geoFailed = geoState === 'denied' || geoState === 'unavailable'
  const areaResolved = !areaLoading && detectInitiated.current && geoState === 'granted'

  return (
    <div className="px-4 max-w-2xl mx-auto space-y-6 pb-4">
      {/* 5.1 Area Header */}
      {geoState === 'requesting' || areaLoading || (geoState === 'granted' && !detectInitiated.current) ? (
        <div className="pt-2">
          <div className="h-8 w-48 bg-on-surface/5 animate-pulse" />
        </div>
      ) : geoState === 'denied' ? (
        <div className="pt-2 flex items-center gap-2 text-on-surface-variant opacity-60">
          <span className="material-symbols-outlined text-base">location_off</span>
          <p className="font-body text-sm">Enable location access to detect your area.</p>
        </div>
      ) : geoState === 'unavailable' ? (
        <div className="pt-2 flex items-center gap-3">
          <span className="material-symbols-outlined text-base text-on-surface-variant opacity-60">
            location_searching
          </span>
          <p className="font-body text-sm text-on-surface-variant opacity-60">
            Couldn't get your location.
          </p>
          <button
            onClick={requestGeo}
            className="font-headline font-bold text-xs uppercase tracking-widest px-3 py-1 rounded-full bg-on-surface/10 text-on-surface"
          >
            Retry
          </button>
        </div>
      ) : areaError ? (
        <div className="pt-2 flex items-center gap-2 text-on-surface-variant opacity-60">
          <span className="material-symbols-outlined text-base">wifi_off</span>
          <p className="font-body text-sm">Couldn't load area — check your connection.</p>
        </div>
      ) : areaResolved && !area ? (
        <div className="pt-2">
          <p className="font-body text-sm text-on-surface-variant opacity-60">
            No monitored area found near your location.
          </p>
        </div>
      ) : area ? (
        <div className="flex flex-wrap items-center gap-3 pt-2">
          <h1 className="font-headline font-bold text-2xl uppercase tracking-tight text-on-surface leading-none">
            {(area.name as string).toUpperCase()}
          </h1>
          {risk && (
            <span
              className="flex items-center gap-1.5 font-headline font-bold text-xs uppercase tracking-widest px-3 py-1 rounded-full"
              style={{ backgroundColor: risk.bg, color: risk.text }}
            >
              <span className="w-2 h-2 rounded-full block" style={{ backgroundColor: risk.text }} />
              {risk.label}
            </span>
          )}
        </div>
      ) : null}

      {/* 5.2 Safety Score Hero */}
      {area && scoresLoading && (
        <div className="h-40 bg-on-surface/5 animate-pulse rounded" />
      )}
      {area && !scoresLoading && !scoresError && (
        <SafetyScoreGauge
          score={score !== null ? Math.round(score) : null}
          updatedAt={areaScore?.score_updated_at ?? null}
        />
      )}
      {area && !scoresLoading && scoresError && (
        <p className="font-body text-xs text-on-surface-variant opacity-50 text-center py-2">
          Couldn't load safety score — check your connection.
        </p>
      )}
      {!area && !areaResolved && !geoFailed && (
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
      {!eventsLoading && eventsError && (
        <p className="font-body text-xs text-on-surface-variant opacity-50 text-center py-2">
          Couldn't load recent incidents — check your connection.
        </p>
      )}

      {/* 5.6 AI Area Brief — only once score has been computed */}
      {area && !eventsLoading && !scoresLoading && score !== null && risk !== null && (
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
