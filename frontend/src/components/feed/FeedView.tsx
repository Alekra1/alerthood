import { useEffect, useState } from 'react'
import { supabase } from '../../lib/supabase'
import { useAuth } from '../../context/AuthContext'
import type { Threat, ThreatCategory, ThreatSeverity } from '../../types'
import { ActiveThreatBanner } from './ActiveThreatBanner'
import { FilterBar } from './FilterBar'
import { ThreatCard } from './ThreatCard'

type FilterValue = 'ALL' | ThreatCategory

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
}

export function FeedView() {
  const { user } = useAuth()
  const [activeFilter, setActiveFilter] = useState<FilterValue>('ALL')
  const [items, setItems] = useState<FeedItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)

      const { data: events } = await supabase
        .from('events')
        .select('id, title, threat_type, severity, relevance_score, occurred_at, location_label, source_type')
        .eq('status', 'active')
        .order('occurred_at', { ascending: false })
        .limit(50)

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
              relevancePct: e.relevance_score,
              location: e.location_label ?? '',
              lat: 0,
              lng: 0,
              minutesAgo,
              upvotes: upMap[e.id] ?? 0,
              downvotes: downMap[e.id] ?? 0,
              source: e.source_type,
            },
            userVote: mv === 1 ? 'up' : mv === -1 ? 'down' : null,
          }
        }).sort((a, b) => b.threat.upvotes - a.threat.upvotes)
      )

      setLoading(false)
    }

    load()
  }, [user])

  const filtered = activeFilter === 'ALL' ? items : items.filter((item) => item.threat.category === activeFilter)
  const activeThreat = filtered[0]?.threat

  return (
    <div className="px-4 max-w-2xl mx-auto">
      <div className="mt-6">
        {activeThreat && <ActiveThreatBanner threat={activeThreat} />}
      </div>

      <div className="sticky top-16 bg-background z-40 py-4 -mx-4 px-4 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <button className="flex items-center gap-2 bg-surface-container border-2 border-black px-3 py-1.5 shadow-hard-sm active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-none">
            <span className="material-symbols-outlined text-primary text-sm">location_on</span>
            <span className="font-headline font-bold text-sm tracking-tight uppercase">Home (5mi radius)</span>
            <span className="material-symbols-outlined text-sm">expand_more</span>
          </button>
          <button
            className="p-2 border-2 border-black bg-surface-container active:shadow-none shadow-hard-sm"
            aria-label="Filter options"
          >
            <span className="material-symbols-outlined">tune</span>
          </button>
        </div>
        <FilterBar active={activeFilter} onChange={setActiveFilter} />
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
            <ThreatCard key={item.threat.id} threat={item.threat} initialVote={item.userVote} />
          ))
        )}
      </div>
    </div>
  )
}
