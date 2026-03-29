import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { CircleMarker, GeoJSON as GeoJSONLayer, MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { supabase } from '../../lib/supabase'
import { getCachedUserLocation, setCachedUserLocation } from '../../lib/userLocation'
import type { Threat, ThreatCategory, ThreatSeverity } from '../../types'
import { useHeatmap } from '../../hooks/useHeatmap'
import { useNeighborhoods } from '../../hooks/useNeighborhoods'
import type { NeighborhoodFeature } from '../../hooks/useNeighborhoods'
import { ThreatMarker } from './ThreatMarker'
import { AlertBottomSheet } from './AlertBottomSheet'
import { DistrictBottomSheet } from './DistrictBottomSheet'
import { AddEventModal } from './AddEventModal'
import type { AddEventFormValues } from './AddEventModal'

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

interface EventRow {
  id: string
  title: string
  threat_type: string
  severity: string
  occurred_at: string
  lat: number
  lng: number
  location_label: string | null
  source_type: string | null
  source_url: string | null
}

const MAP_CENTER: [number, number] = [20, 0]
const MAP_ZOOM = 16
const MAP_FALLBACK_ZOOM = 3
const MAP_MIN_ZOOM = 3
const WORLD_BOUNDS: [[number, number], [number, number]] = [[-85.051129, -180], [85.051129, 180]]

const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'

// Module-level — survives route changes, resets only on full page reload
let savedCenter: [number, number] | null = null
let savedZoom: number | null = null
let hasFlownToUser = false

const userLocationIcon = L.divIcon({
  html: `<div class="user-location-marker">
    <div class="ring"></div>
    <div class="ring"></div>
    <div class="dot"></div>
  </div>`,
  className: '',
  iconSize: [40, 40],
  iconAnchor: [20, 20],
})

function weightToColor(weight: number): string {
  if (weight >= 0.75) return '#ef4444'
  if (weight >= 0.5) return '#f97316'
  if (weight >= 0.25) return '#eab308'
  return '#22c55e'
}

function mapEventRowToThreat(event: EventRow): Threat {
  return {
    id: event.id,
    title: event.title,
    category: THREAT_TYPE_MAP[event.threat_type] ?? 'CRIME',
    severity: event.severity.toUpperCase() as ThreatSeverity,
    severityPct: SEVERITY_PCT[event.severity] ?? 50,
    location: event.location_label ?? '',
    lat: event.lat,
    lng: event.lng,
    minutesAgo: Math.max(0, Math.floor((Date.now() - new Date(event.occurred_at).getTime()) / 60000)),
    upvotes: 0,
    downvotes: 0,
    source: event.source_type ?? '',
    sourceUrl: event.source_url ?? null,
  }
}

function requestCurrentPosition(): Promise<[number, number]> {
  if (!navigator.geolocation) {
    return Promise.reject(new Error('Geolocation is not available on this device.'))
  }

  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve([pos.coords.latitude, pos.coords.longitude]),
      () => reject(new Error('We need your current location before you can report an event.')),
      { enableHighAccuracy: true, timeout: 8000 },
    )
  })
}

// Flies to a position inside the Leaflet context
function FlyTo({ position }: { position: [number, number] }) {
  const map = useMap()
  useEffect(() => {
    map.flyTo(position, Math.max(map.getZoom(), 15), { duration: 1.5 })
  }, [position, map])
  return null
}

// Saves map center/zoom to module-level vars whenever the user pans or zooms
function MapStateSync() {
  useMapEvents({
    moveend: (e) => {
      const c = e.target.getCenter()
      savedCenter = [c.lat, c.lng]
      savedZoom = e.target.getZoom()
    },
  })
  return null
}

function NeighborhoodLayer({ onDistrictClick }: { onDistrictClick: (props: NeighborhoodFeature['properties']) => void }) {
  const [bounds, setBounds] = useState<{
    minLat: number; minLng: number; maxLat: number; maxLng: number
  } | null>(null)
  const [zoom, setZoom] = useState(MAP_ZOOM)
  const geoJsonRef = useRef<L.GeoJSON | null>(null)

  const map = useMapEvents({
    moveend: () => {
      const b = map.getBounds()
      setBounds({
        minLat: b.getSouth(),
        minLng: b.getWest(),
        maxLat: b.getNorth(),
        maxLng: b.getEast(),
      })
      setZoom(map.getZoom())
    },
  })

  // Create a custom pane below the default overlayPane so markers stay on top
  useEffect(() => {
    if (!map.getPane('neighborhoodPane')) {
      const pane = map.createPane('neighborhoodPane')
      pane.style.zIndex = '200'
    }
  }, [map])

  // Trigger initial load
  useEffect(() => {
    const b = map.getBounds()
    setBounds({
      minLat: b.getSouth(),
      minLng: b.getWest(),
      maxLat: b.getNorth(),
      maxLng: b.getEast(),
    })
    setZoom(map.getZoom())
  }, [map])

  const { geojson } = useNeighborhoods(bounds, zoom)

  // Update the Leaflet layer imperatively — swap atomically to avoid flicker
  useEffect(() => {
    const layer = geoJsonRef.current
    if (!layer || !geojson) return
    // Only clear + replace when we have features; prevents disappearance
    // when crossing zoom thresholds (city ↔ neighborhood)
    if (geojson.features.length > 0) {
      layer.clearLayers()
      layer.addData(geojson as any)
    }
  }, [geojson])

  return (
    <GeoJSONLayer
      ref={geoJsonRef}
      data={{ type: 'FeatureCollection', features: [] } as any}
      style={(feature) => {
        const props = (feature as any)?.properties as NeighborhoodFeature['properties'] | undefined
        const color = props?.safety_color ?? '#22c55e'
        return {
          color,
          weight: 2,
          fillColor: color,
          fillOpacity: 0.1,
          opacity: 0.8,
          pane: 'neighborhoodPane',
        }
      }}
      onEachFeature={(feature, layer) => {
        const props = feature.properties as NeighborhoodFeature['properties']
        layer.bindTooltip(
          `<strong>${props.name}</strong><br/>Safety: ${Math.round(props.safety_score)}%`,
          { sticky: true, className: '!bg-black/80 !text-white !border-black !text-xs !font-mono !rounded-none' }
        )
        layer.on('click', () => onDistrictClick(props))
      }}
    />
  )
}

export function MapView() {
  const { state: navState } = useLocation()
  const fromFeed = !!(navState?.lat && navState?.lng)
  const cachedUserLocation = getCachedUserLocation()

  // On the very first visit (no saved position, not coming from feed), we wait
  // for geolocation before rendering the map so it opens instantly at the user's
  // location with zero fly animation.
  const isFirstVisit = !savedCenter && !fromFeed

  const [initialCenter, setInitialCenter] = useState<[number, number] | null>(
    isFirstVisit ? null : (savedCenter ?? MAP_CENTER)
  )
  const [userPos, setUserPos] = useState<[number, number] | null>(
    cachedUserLocation ? [cachedUserLocation.lat, cachedUserLocation.lng] : null
  )
  // flyTo is only used for feed→marker navigation and the locate button
  const [flyTo, setFlyTo] = useState<[number, number] | null>(
    fromFeed ? [navState.lat, navState.lng] : null
  )

  const [threats, setThreats] = useState<Threat[]>([])
  const [selectedThreat, setSelectedThreat] = useState<Threat | null>(null)
  const [isAddEventOpen, setIsAddEventOpen] = useState(false)
  const [isSubmittingEvent, setIsSubmittingEvent] = useState(false)
  const [addEventError, setAddEventError] = useState<string | null>(null)
  const [selectedDistrict, setSelectedDistrict] = useState<NeighborhoodFeature['properties'] | null>(null)
  const { cells, loading } = useHeatmap(null)

  async function loadThreats(): Promise<Threat[]> {
    const { data, error } = await supabase.rpc('events_with_coords', { max_rows: 100 })
    if (error || !data) {
      if (error) {
        console.error('Failed to load map events:', error)
      }
      return []
    }

    const mapped = (data as EventRow[]).map(mapEventRowToThreat)
    setThreats(mapped)
    return mapped
  }

  useEffect(() => {
    void loadThreats()
  }, [])

  useEffect(() => {
    requestCurrentPosition()
      .then((coords) => {
        setUserPos(coords)
        setCachedUserLocation(coords[0], coords[1])
        if (isFirstVisit) {
          // Open the map directly at user position — no fly animation
          setInitialCenter(coords)
          savedCenter = coords
          savedZoom = MAP_ZOOM
          hasFlownToUser = true
        }
      })
      .catch(() => {
        // Geolocation denied / unavailable on first visit — fall back to world view
        if (isFirstVisit) {
          setInitialCenter(MAP_CENTER)
          savedCenter = MAP_CENTER
          savedZoom = MAP_FALLBACK_ZOOM
        }
      })
  }, [])

  async function centreOnUser() {
    try {
      const coords = await requestCurrentPosition()
      setUserPos(coords)
      setCachedUserLocation(coords[0], coords[1])
      setFlyTo(coords)
    } catch {}
  }

  async function openAddEventModal() {
    setAddEventError(null)
    setSelectedThreat(null)

    if (userPos) {
      setIsAddEventOpen(true)
      return
    }

    try {
      const coords = await requestCurrentPosition()
      setUserPos(coords)
      setCachedUserLocation(coords[0], coords[1])
      setIsAddEventOpen(true)
    } catch (error) {
      setAddEventError(error instanceof Error ? error.message : 'Unable to get your location.')
    }
  }

  async function handleAddEventSubmit(values: AddEventFormValues) {
    if (!userPos) {
      setAddEventError('We need your current location before you can report an event.')
      return
    }

    setIsSubmittingEvent(true)
    setAddEventError(null)

    let detectedAreaId: string | null = null
    let locationLabel = 'Your current location'

    try {
      const { data: areaRows } = await supabase.rpc('find_nearest_area', {
        user_point: `SRID=4326;POINT(${userPos[1]} ${userPos[0]})`,
      })
      if (areaRows && areaRows.length > 0) {
        detectedAreaId = areaRows[0].id ?? null
        locationLabel = areaRows[0].name ?? locationLabel
      }

      const { data: { user } } = await supabase.auth.getUser()

      const { data, error } = await supabase
        .from('events')
        .insert({
          title: values.title,
          description: values.description,
          threat_type: values.threatType,
          severity: values.severity,
          occurred_at: new Date().toISOString(),
          // PostGIS WKT: POINT(lng lat)
          location: `SRID=4326;POINT(${userPos[1]} ${userPos[0]})`,
          location_label: locationLabel,
          source_type: 'user',
          area_id: detectedAreaId,
          author_id: user?.id ?? null,
        })
        .select('id, created_at')
        .single()

      if (error) throw new Error(error.message)

      const refreshedThreats = await loadThreats()
      const createdThreat = refreshedThreats.find((threat) => threat.id === data.id) ?? {
        id: data.id,
        title: values.title,
        category: THREAT_TYPE_MAP[values.threatType] ?? 'CRIME',
        severity: values.severity.toUpperCase() as ThreatSeverity,
        severityPct: SEVERITY_PCT[values.severity] ?? 50,
        location: locationLabel,
        lat: userPos[0],
        lng: userPos[1],
        minutesAgo: 0,
        upvotes: 0,
        downvotes: 0,
        source: 'user',
        sourceUrl: null,
      }

      if (!refreshedThreats.some((threat) => threat.id === data.id)) {
        setThreats((current) => [createdThreat, ...current.filter((threat) => threat.id !== data.id)])
      }

      setIsAddEventOpen(false)
      setSelectedThreat(createdThreat)
    } catch (error) {
      setAddEventError(
        error instanceof Error ? error.message : 'Failed to report the event. Please try again.',
      )
    } finally {
      setIsSubmittingEvent(false)
    }
  }

  // Block render until we have an initial center (first-visit geolocation pending)
  if (!initialCenter) {
    return (
      <div className="flex items-center justify-center w-full h-full bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="user-location-marker scale-150">
            <div className="ring" />
            <div className="ring" />
            <div className="dot" />
          </div>
          <span className="font-headline text-[10px] uppercase tracking-widest text-on-surface/50 mt-2">
            Locating you…
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="relative w-full h-full">
      <div className="absolute inset-0 z-0">
        <MapContainer
          center={initialCenter}
          zoom={savedZoom ?? MAP_FALLBACK_ZOOM}
          minZoom={MAP_MIN_ZOOM}
          maxBounds={WORLD_BOUNDS}
          maxBoundsViscosity={1}
          className="w-full h-full"
          zoomControl
          attributionControl={false}
        >
          <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
          <MapStateSync />

          <NeighborhoodLayer onDistrictClick={(props) => { setSelectedThreat(null); setSelectedDistrict(props) }} />

          {flyTo && <FlyTo position={flyTo} />}

          {userPos && (
            <Marker position={userPos} icon={userLocationIcon} />
          )}

          {threats.map((threat) => (
            <ThreatMarker
              key={threat.id}
              threat={threat}
              onSelect={setSelectedThreat}
              isSelected={selectedThreat?.id === threat.id}
            />
          ))}

          {cells.map((cell, i) => (
            <CircleMarker
              key={`${cell.lat}-${cell.lng}-${i}`}
              center={[cell.lat, cell.lng]}
              radius={Math.max(6, cell.weight * 20)}
              pathOptions={{
                color: weightToColor(cell.weight),
                fillColor: weightToColor(cell.weight),
                fillOpacity: 0.6,
                weight: 1,
              }}
            >
              <Popup>
                <span className="font-bold">{cell.event_count} events</span>
                <br />
                Risk: {Math.round(cell.weight * 100)}%
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>

      {loading && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-40 bg-surface-container border-2 border-black px-4 py-2 shadow-hard-sm">
          <span className="font-headline text-xs uppercase tracking-widest">Loading heatmap...</span>
        </div>
      )}

      {selectedDistrict && (
        <DistrictBottomSheet
          district={selectedDistrict}
          onClose={() => setSelectedDistrict(null)}
        />
      )}

      {selectedThreat && !selectedDistrict && (
        <AlertBottomSheet
          threat={selectedThreat}
          onClose={() => setSelectedThreat(null)}
        />
      )}

      {addEventError && !isAddEventOpen && (
        <div className="fixed right-6 left-6 md:left-auto md:w-80 bottom-44 z-50 bg-error-container text-on-error-container border-[3px] border-black shadow-hard px-4 py-3">
          <p className="font-body text-sm">{addEventError}</p>
        </div>
      )}

      <button
        onClick={centreOnUser}
        className="fixed bottom-44 right-6 w-12 h-12 bg-surface-container border-2 border-black shadow-hard active:translate-x-[2px] active:translate-y-[2px] active:shadow-none flex items-center justify-center z-40 transition-none"
        aria-label="Center map on my location"
      >
        <span className="material-symbols-outlined text-on-surface text-2xl">my_location</span>
      </button>

      <button
        onClick={openAddEventModal}
        className="fixed bottom-24 right-6 w-16 h-16 bg-primary-container border-[3px] border-black shadow-hard active:translate-x-[2px] active:translate-y-[2px] active:shadow-none flex items-center justify-center z-40 transition-none"
        aria-label="Add new alert"
      >
        <span className="material-symbols-outlined text-on-primary-container text-4xl font-bold">add</span>
      </button>

      {isAddEventOpen && userPos && (
        <AddEventModal
          error={addEventError}
          isSubmitting={isSubmittingEvent}
          location={userPos}
          onClose={() => {
            if (isSubmittingEvent) return
            setIsAddEventOpen(false)
            setAddEventError(null)
          }}
          onSubmit={handleAddEventSubmit}
        />
      )}
    </div>
  )
}
