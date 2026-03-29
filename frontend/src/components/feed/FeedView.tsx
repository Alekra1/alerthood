import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../../lib/supabase'
import { useAuth } from '../../context/AuthContext'
import type { Threat, ThreatCategory, ThreatSeverity } from '../../types'
import { ActiveThreatBanner } from './ActiveThreatBanner'
import { FilterBar } from './FilterBar'
import { SeverityBar } from './SeverityBar'
import { ThreatCard } from './ThreatCard'

type FilterValue = 'ALL' | ThreatCategory
type SeverityFilter = 'ALL' | ThreatSeverity

const THREAT_TYPE_MAP: Record<string, ThreatCategory> = {
  crime: 'CRIME',
  infrastructure: 'UTILITY',
  disturbance: 'DISTURBANCE',
  natural: 'NATURAL',
}

const SEVERITY_PCT: Record<string, number> = {
  low: 25,
  medium: 50,
  high: 75,
  critical: 95,
}

interface FeedItem {
  threat: Threat
  userVote: 'up' | 'down' | null
  areaId: string | null
}

interface AreaOption {
  areaId: string
  label: string
}

export function FeedView() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [activeFilter, setActiveFilter] = useState<FilterValue>('ALL')
  const [activeSeverity, setActiveSeverity] = useState<SeverityFilter>('ALL')
  const [items, setItems] = useState<FeedItem[]>([])
  const [loading, setLoading] = useState(true)
  const [areaOptions, setAreaOptions] = useState<AreaOption[]>([])
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(null)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Load user's monitored areas
  useEffect(() => {
    if (!user) return
    supabase
      .from('user_area_subscriptions')
      .select('id, label, area:areas!area_id(id, name, city)')
      .eq('user_id', user.id)
      .then(({ data }) => {
        setAreaOptions(
          (data ?? []).map((sub: any) => ({
            areaId: sub.area?.id as string,
            label: sub.label?.toUpperCase() ?? sub.area?.name?.toUpperCase() ?? 'AREA',
          })).filter((o) => o.areaId)
        )
      })
  }, [user])

  // Close dropdown on outside click
  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleMouseDown)
    return () => document.removeEventListener('mousedown', handleMouseDown)
  }, [])

  useEffect(() => {
    async function load() {
      setLoading(true)

      const { data: events } = await supabase
        .rpc('events_with_coords', { max_rows: 50 })

      if (!events || events.length === 0) {
        setItems([])
        setLoading(false)
        return
      }

      const eventIds = events.map((e) => e.id)

      const [{ data: allVotes }, { data: userVotes }] = await Promise.all([
        supabase.from('event_votes').select('event_id, vote').in('event_id', eventIds),
        user
          ? supabase.from('event_votes').select('event_id, vote').eq('user_id', user.id).in('event_id', eventIds)
          : Promise.resolve({ data: [] as { event_id: string; vote: number }[] }),
      ])

      // Count upvotes/downvotes per event
      const upMap: Record<string, number> = {}
      const downMap: Record<string, number> = {}
      for (const v of allVotes ?? []) {
        if (v.vote === 1) upMap[v.event_id] = (upMap[v.event_id] ?? 0) + 1
        else downMap[v.event_id] = (downMap[v.event_id] ?? 0) + 1
      }

      // Current user's vote per event
      const myVoteMap: Record<string, number> = {}
      for (const v of userVotes ?? []) {
        myVoteMap[v.event_id] = v.vote
      }

      setItems(
        events.map((e) => {
          const minutesAgo = Math.max(0, Math.floor((Date.now() - new Date(e.occurred_at).getTime()) / 60000))
          const mv = myVoteMap[e.id]
          return {
            threat: {
              id: e.id,
              title: e.title,
              category: THREAT_TYPE_MAP[e.threat_type] ?? 'CRIME',
              severity: e.severity.toUpperCase() as ThreatSeverity,
              severityPct: SEVERITY_PCT[e.severity] ?? 50,
              location: e.location_label ?? '',
              lat: e.lat ?? 0,
              lng: e.lng ?? 0,
              minutesAgo,
              upvotes: upMap[e.id] ?? 0,
              downvotes: downMap[e.id] ?? 0,
              source: e.source_type,
              sourceUrl: e.source_url ?? null,
            },
            userVote: mv === 1 ? 'up' : mv === -1 ? 'down' : null,
            areaId: e.area_id ?? null,
          }
        }).sort((a, b) => b.threat.upvotes - a.threat.upvotes)
      )

      setLoading(false)
    }

    load()
  }, [user])

  const byArea = selectedAreaId ? items.filter((item) => item.areaId === selectedAreaId) : items
  const byCategory = activeFilter === 'ALL' ? byArea : byArea.filter((item) => item.threat.category === activeFilter)
  const filtered = activeSeverity === 'ALL' ? byCategory : byCategory.filter((item) => item.threat.severity === activeSeverity)
  const activeThreat = filtered[0]?.threat

  const selectedLabel = selectedAreaId
    ? (areaOptions.find((o) => o.areaId === selectedAreaId)?.label ?? 'AREA')
    : 'ALL AREAS'

  return (
    <div className="px-4 max-w-2xl mx-auto">
      <div className="mt-6">
        {activeThreat && <ActiveThreatBanner threat={activeThreat} />}
      </div>

      <div className="sticky top-16 bg-background z-40 py-4 -mx-4 px-4 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen((o) => !o)}
              className="flex items-center gap-2 bg-surface-container border-2 border-black px-3 py-1.5 shadow-hard-sm active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-none"
            >
              <span className="material-symbols-outlined text-primary text-sm">location_on</span>
              <span className="font-headline font-bold text-sm tracking-tight uppercase">{selectedLabel}</span>
              <span className="material-symbols-outlined text-sm">{dropdownOpen ? 'expand_less' : 'expand_more'}</span>
            </button>
            {dropdownOpen && (
              <div className="absolute top-full left-0 mt-1 min-w-[180px] bg-surface-container border-2 border-black shadow-hard z-50 flex flex-col">
                <button
                  onClick={() => { setSelectedAreaId(null); setDropdownOpen(false) }}
                  className={`flex items-center gap-2 px-3 py-2 font-headline font-bold text-sm tracking-tight uppercase text-left hover:bg-primary/10 transition-none ${selectedAreaId === null ? 'text-primary' : ''}`}
                >
                  All Areas
                </button>
                {areaOptions.map((opt) => (
                  <button
                    key={opt.areaId}
                    onClick={() => { setSelectedAreaId(opt.areaId); setDropdownOpen(false) }}
                    className={`flex items-center gap-2 px-3 py-2 font-headline font-bold text-sm tracking-tight uppercase text-left hover:bg-primary/10 transition-none ${selectedAreaId === opt.areaId ? 'text-primary' : ''}`}
                  >
                    {opt.label}
                  </button>
                ))}
                {areaOptions.length === 0 && (
                  <span className="px-3 py-2 font-body text-xs text-on-surface-variant opacity-60">No monitored areas</span>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <span className="font-headline font-bold text-xs tracking-widest uppercase text-on-surface-variant opacity-60">Type</span>
          <FilterBar active={activeFilter} onChange={setActiveFilter} />
        </div>
        <div className="flex flex-col gap-1">
          <span className="font-headline font-bold text-xs tracking-widest uppercase text-on-surface-variant opacity-60">Severity</span>
          <SeverityBar active={activeSeverity} onChange={setActiveSeverity} />
        </div>
      </div>

      <div className="flex flex-col gap-8 mt-4 pb-8">
        {loading ? (
          <div className="text-center py-16 text-on-surface-variant">
            <p className="font-headline font-bold uppercase tracking-widest text-sm opacity-50">Loading...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-on-surface-variant">
            <span className="material-symbols-outlined text-5xl block mb-3 opacity-30">check_circle</span>
            <p className="font-headline font-bold uppercase tracking-widest text-sm">All Clear</p>
            <p className="font-body text-xs mt-1 opacity-60">
              No {activeFilter !== 'ALL' ? activeFilter.toLowerCase() : ''} alerts in your area
            </p>
          </div>
        ) : (
          filtered.map((item) => (
            <ThreatCard
              key={item.threat.id}
              threat={item.threat}
              initialVote={item.userVote}
              onViewMap={(t) => navigate('/map', { state: { lat: t.lat, lng: t.lng } })}
            />
          ))
        )}
      </div>
    </div>
  )
}
