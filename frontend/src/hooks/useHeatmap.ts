import { useEffect, useState } from 'react'
import { apiGet } from '../lib/api'

interface HeatmapCell {
  lat: number
  lng: number
  weight: number
  event_count: number
}

interface HeatmapResponse {
  cells: HeatmapCell[]
  time_bucket: string
  generated_at: string
}

export function useHeatmap(areaId: string | null, timeBucket = 'all') {
  const [cells, setCells] = useState<HeatmapCell[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!areaId) return

    let cancelled = false
    setLoading(true)
    setError(null)

    apiGet<HeatmapResponse>('/api/events/heatmap', {
      area_id: areaId,
      time_bucket: timeBucket,
    })
      .then((data) => {
        if (!cancelled) setCells(data.cells)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [areaId, timeBucket])

  return { cells, loading, error }
}
