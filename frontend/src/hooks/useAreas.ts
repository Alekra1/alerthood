import { useCallback, useState } from 'react'
import { apiGet, apiPost, apiPatch, apiDelete } from '../lib/api'

interface DetectedArea {
  id: string
  name: string
  [key: string]: unknown
}

interface Subscription {
  subscription_id: string
}

export function useAreaDetect() {
  const [area, setArea] = useState<DetectedArea | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const detect = useCallback(async (lat: number, lng: number) => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiGet<{ area: DetectedArea | null }>('/api/areas/detect', {
        lat: String(lat),
        lng: String(lng),
      })
      setArea(data.area)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { area, detect, loading, error }
}

export function useAreaSubscriptions() {
  const subscribe = useCallback(async (areaId: string, label = 'Home') => {
    return apiPost<Subscription>('/api/areas/subscribe', {
      area_id: areaId,
      label,
    })
  }, [])

  const unsubscribe = useCallback(async (areaId: string) => {
    await apiDelete(`/api/areas/${areaId}/subscribe`)
  }, [])

  const updateNotificationPrefs = useCallback(
    async (subscriptionId: string, prefs: Record<string, boolean | string>) => {
      await apiPatch(`/api/subscriptions/${subscriptionId}/notifications`, prefs)
    },
    [],
  )

  return { subscribe, unsubscribe, updateNotificationPrefs }
}
