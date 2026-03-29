import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, CircleMarker } from 'react-leaflet'
import type { Threat } from '../../types'

const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
const TILE_ATTRIBUTION = '&copy; OpenStreetMap contributors &copy; CARTO'

const CATEGORY_COLOR: Record<string, string> = {
  CRIME: '#FF5545',
  UTILITY: '#FE9400',
  DISTURBANCE: '#C567F4',
  NATURAL: '#facc15',
}

interface MiniHeatmapProps {
  center: [number, number]
  events: Threat[]
}

export function MiniHeatmap({ center, events }: MiniHeatmapProps) {
  const navigate = useNavigate()

  return (
    <div className="border-2 border-black shadow-hard rounded-xl overflow-hidden relative">
      <MapContainer
        center={center}
        zoom={13}
        style={{ height: 170, width: '100%' }}
        zoomControl={false}
        dragging={false}
        scrollWheelZoom={false}
        doubleClickZoom={false}
        touchZoom={false}
        keyboard={false}
        attributionControl={false}
      >
        <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
        {events.map((e) =>
          e.lat && e.lng ? (
            <CircleMarker
              key={e.id}
              center={[e.lat, e.lng]}
              radius={6}
              pathOptions={{
                fillColor: CATEGORY_COLOR[e.category] ?? '#FF5545',
                color: '#000',
                weight: 1.5,
                fillOpacity: 0.85,
              }}
            />
          ) : null
        )}
      </MapContainer>

      {/* Event count overlay */}
      <div className="absolute bottom-2 left-2 z-[1000] bg-surface-container border border-black px-2 py-0.5">
        <span className="font-body text-xs text-on-surface-variant uppercase font-bold">
          {events.length} events · last 48h
        </span>
      </div>

      {/* View on Map button */}
      <button
        onClick={() => navigate('/map', { state: { lat: center[0], lng: center[1] } })}
        className="absolute bottom-2 right-2 z-[1000] flex items-center gap-1 bg-primary-container text-on-primary-container border-2 border-black shadow-hard-sm px-3 py-1 font-headline font-bold text-xs tracking-wide uppercase active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-none"
      >
        VIEW ON MAP
        <span className="material-symbols-outlined text-sm">arrow_forward</span>
      </button>
    </div>
  )
}
