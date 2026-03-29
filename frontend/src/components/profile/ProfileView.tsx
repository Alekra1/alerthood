import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { supabase } from '../../lib/supabase'
import { MOCK_PROFILE } from '../../data/mock'
import type { MonitoredArea } from '../../types'
import { MetricsBento } from './MetricsBento'
import { BadgeGrid } from './BadgeGrid'
import { MonitoredAreaCard } from './MonitoredAreaCard'
import { AreaPickerMap } from './AreaPickerMap'

export function ProfileView() {
  const { user, profile, loading, signOut } = useAuth()
  const navigate = useNavigate()
  const [areas, setAreas] = useState<MonitoredArea[]>([])
  const [showPicker, setShowPicker] = useState(false)

  async function loadAreas() {
    if (!user) return
    const { data, error } = await supabase
      .from('user_area_subscriptions')
      .select('id, label, area:areas!area_id(id, name, city)')
      .eq('user_id', user.id)

    if (error) {
      console.error('loadAreas error:', error)
      return
    }

    setAreas(
      (data ?? []).map((sub: any) => ({
        id: sub.id,
        name: sub.label?.toUpperCase() ?? 'AREA',
        area_type: (sub.area?.city ? 'neighborhood' : 'city') as 'city' | 'neighborhood',
        parent_name: sub.area?.city ?? null,
        safety_score: 50,
        safety_color: '#eab308',
        isActive: true,
        notifyCrime: true,
        notifyUtility: true,
        notifyNatural: true,
        notifyDisturbance: false,
      })),
    )
  }

  useEffect(() => {
    loadAreas()
  }, [user])

  async function handleLogout() {
    await signOut()
    navigate('/auth', { replace: true })
  }

  const displayName = profile?.display_name || profile?.username || 'User'
  const email = profile?.email || user?.email || ''

  if (loading) {
    return (
      <div className="flex items-center justify-center pt-32">
        <span className="material-symbols-outlined text-primary-container text-4xl animate-spin">
          progress_activity
        </span>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="flex flex-col items-center justify-center pt-32 gap-4">
        <span className="material-symbols-outlined text-error text-4xl">error</span>
        <p className="font-body text-on-surface-variant text-sm">Could not load profile. Try signing out and back in.</p>
        <button
          onClick={handleLogout}
          className="px-6 py-2 border-2 border-black font-headline font-bold text-error uppercase tracking-widest"
        >
          SIGN OUT
        </button>
      </div>
    )
  }


  return (
    <>
      {showPicker && (
        <AreaPickerMap
          onClose={() => setShowPicker(false)}
          onConfirm={() => { setShowPicker(false); loadAreas() }}
        />
      )}

      <div className="px-4 max-w-2xl mx-auto space-y-8 mt-6">
        <section className="flex flex-col items-center pt-4">
          <div className="w-24 h-24 bg-surface-container border-4 border-black shadow-hard rounded-full flex items-center justify-center mb-4 overflow-hidden">
            {profile?.avatar_url ? (
              <img src={profile.avatar_url} alt="avatar" className="w-full h-full object-cover" />
            ) : (
              <span
                className="material-symbols-outlined text-5xl text-primary"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                account_circle
              </span>
            )}
          </div>
          <h2 className="font-headline text-3xl font-bold uppercase tracking-tight">{displayName}</h2>
          {profile?.username && (
            <p className="font-body text-on-surface-variant text-sm">@{profile.username}</p>
          )}
          <p className="font-body text-on-surface-variant text-xs mt-0.5">{email}</p>
        </section>

        <MetricsBento
          karma={profile?.karma ?? 0}
          karmaWeekly={0}
          trustScore={Number(profile?.trust_score ?? 50)}
        />

        <BadgeGrid badges={MOCK_PROFILE.badges} />

        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-headline text-xl font-bold uppercase tracking-tight flex items-center gap-2">
              <span className="w-6 h-1 bg-secondary inline-block" />
              MONITORED AREAS
            </h3>
            <button
              onClick={() => setShowPicker(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 border-2 border-black bg-surface-container shadow-hard-sm font-headline text-xs font-bold uppercase tracking-widest active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-none"
            >
              <span className="material-symbols-outlined text-sm">add_location</span>
              SELECT ON MAP
            </button>
          </div>

          {areas.length === 0 && (
            <div className="py-8 flex flex-col items-center gap-2 text-on-surface-variant opacity-50">
              <span className="material-symbols-outlined text-4xl">location_off</span>
              <p className="text-sm font-label uppercase tracking-wide">No monitored areas yet</p>
            </div>
          )}

          {areas.map((area) => (
            <MonitoredAreaCard
              key={area.id}
              area={area}
              onDelete={(id) => setAreas((prev) => prev.filter((a) => a.id !== id))}
            />
          ))}
        </section>

        <section className="pb-12">
          <button
            onClick={handleLogout}
            className="w-full py-4 border-2 border-black font-headline font-bold text-error uppercase tracking-widest hover:bg-error-container hover:text-white transition-none active:translate-x-[2px] active:translate-y-[2px] active:shadow-none"
          >
            LOGOUT SESSION
          </button>
        </section>
      </div>
    </>
  )
}
