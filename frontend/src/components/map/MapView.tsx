import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import { useHeatmap } from '../../hooks/useHeatmap'
import { MonitoredZone } from './MonitoredZone'
import { MOCK_PROFILE } from '../../data/mock'

const MAP_CENTER: [number, number] = [41.882, -87.631]
const MAP_ZOOM = 14
const MAP_MIN_ZOOM = 3
const WORLD_BOUNDS: [[number, number], [number, number]] = [[-85.051129, -180], [85.051129, 180]]

const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'

function weightToColor(weight: number): string {
  if (weight >= 0.75) return '#ef4444'
  if (weight >= 0.5) return '#f97316'
  if (weight >= 0.25) return '#eab308'
  return '#22c55e'
}

export function MapView() {
  const homeArea = MOCK_PROFILE.areas.find((a) => a.name === 'HOME')
  const { cells, loading } = useHeatmap(homeArea?.id ?? null)

  return (
    <div className="relative w-full h-full">
      <div className="absolute inset-0 z-0">
        <MapContainer
          center={MAP_CENTER}
          zoom={MAP_ZOOM}
          minZoom={MAP_MIN_ZOOM}
          maxBounds={WORLD_BOUNDS}
          maxBoundsViscosity={1}
          className="w-full h-full"
          zoomControl
          attributionControl={false}
        >
          <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />

          {homeArea && <MonitoredZone area={homeArea} />}

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

      <button
        className="fixed bottom-24 right-6 w-16 h-16 bg-primary-container border-[3px] border-black shadow-hard active:translate-x-[2px] active:translate-y-[2px] active:shadow-none flex items-center justify-center z-40 transition-none"
        aria-label="Add new alert"
      >
        <span className="material-symbols-outlined text-on-primary-container text-4xl font-bold">add</span>
      </button>
    </div>
  )
}
