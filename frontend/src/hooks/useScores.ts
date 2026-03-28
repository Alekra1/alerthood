import { useEffect, useState } from 'react'
import { apiGet } from '../lib/api'

interface NeighborhoodScore {
  area_id: string
  area_name: string
  crime_count: number
  crime_rate_per_km2: number
  poverty_index: number
  safety_score: number
  score_updated_at: string | null
}

interface ScoresResponse {
  scores: NeighborhoodScore[]
  computed_at: string
}

export function useScores() {
  const [scores, setScores] = useState<NeighborhoodScore[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    apiGet<ScoresResponse>('/api/scores')
      .then((data) => {
        if (!cancelled) setScores(data.scores)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [])

  return { scores, loading, error }
}
