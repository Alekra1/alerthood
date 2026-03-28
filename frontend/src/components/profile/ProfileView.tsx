import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { supabase } from '../../lib/supabase'
import { MOCK_PROFILE } from '../../data/mock'
import type { MonitoredArea } from '../../types'
import { MetricsBento } from './MetricsBento'
import { BadgeGrid } from './BadgeGrid'
import { MonitoredAreaCard } from './MonitoredAreaCard'

export function ProfileView() {
  const { user, profile, signOut } = useAuth()
  const navigate = useNavigate()
  const [areas, setAreas] = useState<MonitoredArea[]>([])

  useEffect(() => {
    if (!user) return

    async function loadAreas() {
      const { data } = await supabase
        .from('user_area_subscriptions')
        .select('id, label, area:areas(id, name, lat, lng)')
        .eq('user_id', user!.id)

      if (data) {
        setAreas(
          data.map((sub: any) => ({
            id: sub.id,
            name: sub.label?.toUpperCase() ?? 'AREA',
            radiusMiles: 5,
            neighborhood: sub.area?.name ?? '',
            lat: sub.area?.lat ?? 0,
            lng: sub.area?.lng ?? 0,
            isActive: true,
            notifyCrime: true,
            notifyUtility: true,
            notifyNatural: true,
            notifyDisturbance: false,
          })),
        )
      }
    }

    loadAreas()
  }, [user])

  async function handleLogout() {
    await signOut()
    navigate('/auth', { replace: true })
  }

  const displayName = profile?.display_name || profile?.username || 'User'
  const email = profile?.email || user?.email || ''

  if (!profile) {
    return (
      <div className="flex items-center justify-center pt-32">
        <span className="material-symbols-outlined text-primary-container text-4xl animate-spin">
          progress_activity
        </span>
      </div>
    )
  }

  const displayAreas = areas.length > 0 ? areas : MOCK_PROFILE.areas

  return (
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
        <h3 className="font-headline text-xl font-bold uppercase tracking-tight flex items-center gap-2">
          <span className="w-6 h-1 bg-secondary inline-block" />
          MONITORED AREAS
        </h3>
        {displayAreas.map((area, i) => (
          <MonitoredAreaCard
            key={area.id}
            area={area}
            onDelete={i > 0 ? (id) => console.log('delete', id) : undefined}
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
  )
}
