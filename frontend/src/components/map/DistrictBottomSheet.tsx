import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../../lib/supabase'
import { useAuth } from '../../context/AuthContext'
import { useAreaSubscriptions } from '../../hooks/useAreas'
import type { NeighborhoodFeature } from '../../hooks/useNeighborhoods'

interface DistrictBottomSheetProps {
  district: NeighborhoodFeature['properties']
  onClose: () => void
}

export function DistrictBottomSheet({ district, onClose }: DistrictBottomSheetProps) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { subscribe, unsubscribe } = useAreaSubscriptions()
  const [subscribed, setSubscribed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [checked, setChecked] = useState(false)

  // Check if user is already subscribed to this district
  useEffect(() => {
    if (!user) { setChecked(true); return }
    supabase
      .from('user_area_subscriptions')
      .select('id')
      .eq('user_id', user.id)
      .eq('area_id', district.id)
      .maybeSingle()
      .then(({ data }) => {
        setSubscribed(!!data)
        setChecked(true)
      })
  }, [user, district.id])

  async function handleToggle() {
    if (!user) {
      navigate('/auth')
      return
    }
    setLoading(true)
    try {
      if (subscribed) {
        await unsubscribe(district.id)
        setSubscribed(false)
      } else {
        await subscribe(district.id, district.name)
        setSubscribed(true)
      }
    } catch (err: any) {
      console.error('Subscription toggle failed:', err)
    } finally {
      setLoading(false)
    }
  }

  const safetyScore = Math.round(district.safety_score)

  return (
    <div className="absolute bottom-4 left-4 right-4 md:left-auto md:right-6 md:w-96 z-50">
      <div
        className="bg-surface-container border-[3px] border-black rounded-xl overflow-hidden shadow-[8px_8px_0px_#000000] relative"
        style={{ borderLeft: `6px solid ${district.safety_color}` }}
      >
        <button
          className="absolute top-3 right-3 p-1 hover:bg-surface-container-high active:translate-x-[1px] active:translate-y-[1px] transition-none z-10"
          onClick={onClose}
          aria-label="Close"
        >
          <span className="material-symbols-outlined text-sm text-on-surface-variant">close</span>
        </button>

        <div className="p-5 pl-6">
          <div className="mb-1">
            <span className="text-[10px] font-bold tracking-widest uppercase text-on-surface-variant">
              {district.area_type === 'neighborhood' ? district.parent_name ?? 'Neighborhood' : 'City'}
            </span>
          </div>
          <h2 className="font-headline text-xl text-on-surface leading-tight mb-1">{district.name}</h2>
          <div className="flex items-center gap-2 mb-5">
            <span
              className="text-[10px] font-bold tracking-widest uppercase px-2 py-0.5 border border-black"
              style={{ background: district.safety_color + '33', color: district.safety_color }}
            >
              SAFETY {safetyScore}%
            </span>
            <span className="text-xs text-on-surface-variant font-label">
              {district.event_count_90d} events in 90d
            </span>
          </div>

          <button
            onClick={handleToggle}
            disabled={loading || !checked}
            className={`w-full flex items-center justify-center gap-2 py-3 border-[3px] border-black font-headline text-sm uppercase tracking-wider transition-none shadow-hard active:translate-x-[2px] active:translate-y-[2px] active:shadow-none disabled:opacity-50 disabled:pointer-events-none ${
              subscribed
                ? 'bg-surface-container-high text-on-surface'
                : 'bg-primary-container text-on-primary-container'
            }`}
          >
            <span className="material-symbols-outlined text-base">
              {subscribed ? 'notifications_off' : 'notifications_active'}
            </span>
            {subscribed ? 'Unsubscribe' : 'Subscribe & Monitor'}
          </button>
        </div>
      </div>
    </div>
  )
}
