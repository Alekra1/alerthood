import { useCallback, useEffect, useRef, useState } from 'react'

interface NeighborhoodProperties {
  id: string
  name: string
  slug: string
  area_type: 'city' | 'neighborhood'
  safety_score: number
  safety_color: string
  event_count_90d: number
  parent_name: string | null
}

export interface NeighborhoodFeature {
  type: 'Feature'
  geometry: GeoJSON.MultiPolygon | GeoJSON.Polygon
  properties: NeighborhoodProperties
}

interface FeatureCollection {
  type: 'FeatureCollection'
  features: NeighborhoodFeature[]
}

interface Bounds {
  minLat: number
  minLng: number
  maxLat: number
  maxLng: number
}

const DEBOUNCE_MS = 300
const API_URL = import.meta.env.VITE_API_URL

export function useNeighborhoods(bounds: Bounds | null, zoom: number) {
  const [geojson, setGeojson] = useState<FeatureCollection | null>(null)
  const [loading, setLoading] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  const fetchNeighborhoods = useCallback(async (b: Bounds, z: number) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        min_lat: String(b.minLat),
        min_lng: String(b.minLng),
        max_lat: String(b.maxLat),
        max_lng: String(b.maxLng),
        zoom: String(Math.round(z)),
      })
      const res = await fetch(`${API_URL}/api/neighborhoods?${params}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: FeatureCollection = await res.json()
      setGeojson(data)
    } catch (err) {
      console.error('Failed to fetch neighborhoods:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!bounds) return

    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      fetchNeighborhoods(bounds, zoom)
    }, DEBOUNCE_MS)

    return () => clearTimeout(timerRef.current)
  }, [bounds?.minLat, bounds?.minLng, bounds?.maxLat, bounds?.maxLng, zoom, fetchNeighborhoods])

  return { geojson, loading }
}
