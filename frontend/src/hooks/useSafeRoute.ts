import { useCallback, useState } from 'react'
import { apiPost } from '../lib/api'

interface RouteWaypoint {
  lat: number
  lng: number
}

interface SafeRouteResponse {
  waypoints: RouteWaypoint[]
  google_maps_url: string
  avoided_events: number
  distance_km: number
}

export function useSafeRoute() {
  const [route, setRoute] = useState<SafeRouteResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const calculate = useCallback(
    async (originLat: number, originLng: number, destLat: number, destLng: number) => {
      setLoading(true)
      setError(null)
      try {
        const data = await apiPost<SafeRouteResponse>('/api/routes/safe', {
          origin_lat: originLat,
          origin_lng: originLng,
          dest_lat: destLat,
          dest_lng: destLng,
        })
        setRoute(data)
      } catch (err: any) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  const clear = useCallback(() => setRoute(null), [])

  return { route, calculate, clear, loading, error }
}
