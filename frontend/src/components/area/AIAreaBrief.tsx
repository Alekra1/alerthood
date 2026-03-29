import { useEffect, useState } from 'react'
import type { Threat } from '../../types'
import { apiPost } from '../../lib/api'

interface Props {
  areaId: string
  areaName: string
  safetyScore: number
  riskLevel: string
  crimeCount: number
  crimeRatePerKm2: number
  scoreUpdatedAt: string | null
  activeAlert: Threat | null
  recentEvents: Threat[]
}

type BriefState = 'idle' | 'loading' | 'done' | 'error'

export function AIAreaBrief({ areaId, areaName, safetyScore, riskLevel, crimeCount, crimeRatePerKm2, scoreUpdatedAt, activeAlert, recentEvents }: Props) {
  const [state, setState] = useState<BriefState>('idle')
  const [brief, setBrief] = useState<string | null>(null)

  useEffect(() => {
    if (!areaName) return
    setState('loading')
    setBrief(null)

    const alerts = activeAlert
      ? [{ title: activeAlert.title, category: activeAlert.category, severity: activeAlert.severity }]
      : []

    const incidents = recentEvents.map((e) => ({
      title: e.title,
      category: e.category,
      minutesAgo: e.minutesAgo,
    }))

    apiPost<{ brief: string }>('/api/areas/summary', {
      area_id: areaId,
      area_name: areaName,
      safety_score: safetyScore,
      risk_level: riskLevel,
      crime_count: crimeCount,
      crime_rate_per_km2: crimeRatePerKm2,
      score_updated_at: scoreUpdatedAt,
      active_alerts: alerts,
      recent_incidents: incidents,
    })
      .then((data) => {
        setBrief(data.brief)
        setState('done')
      })
      .catch(() => setState('error'))
  }, [areaId, areaName, safetyScore, riskLevel])

  return (
    <div
      className="border-2 border-black rounded-xl p-5"
      style={{ backgroundColor: '#201F1F', boxShadow: '4px 4px 0px #000000' }}
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="material-symbols-outlined text-xl" style={{ color: '#E8B3FF' }}>
          auto_awesome
        </span>
        <span
          className="font-headline font-bold text-xs uppercase tracking-widest"
          style={{ color: '#E8B3FF' }}
        >
          AI Area Brief
        </span>
      </div>

      {state === 'loading' && (
        <div className="flex items-center gap-1.5 py-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-2 h-2 rounded-full animate-bounce"
              style={{ backgroundColor: '#E8B3FF', animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      )}

      {state === 'done' && brief && (
        <p className="font-body text-sm text-on-surface leading-relaxed">{brief}</p>
      )}

      {state === 'error' && (
        <p className="font-body text-sm text-on-surface-variant opacity-60">
          Could not generate summary right now. Try again later.
        </p>
      )}
    </div>
  )
}
