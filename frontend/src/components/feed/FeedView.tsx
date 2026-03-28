import { useState } from 'react'
import { MOCK_THREATS } from '../../data/mock'
import type { ThreatCategory } from '../../types'
import { ActiveThreatBanner } from './ActiveThreatBanner'
import { FilterBar } from './FilterBar'
import { ThreatCard } from './ThreatCard'

type FilterValue = 'ALL' | ThreatCategory

const activeThreat = MOCK_THREATS.find((t) => t.minutesAgo <= 5) ?? MOCK_THREATS[0]

export function FeedView() {
  const [activeFilter, setActiveFilter] = useState<FilterValue>('ALL')

  const filtered =
    activeFilter === 'ALL'
      ? MOCK_THREATS
      : MOCK_THREATS.filter((t) => t.category === activeFilter)

  return (
    <div className="px-4 max-w-2xl mx-auto">
      <div className="mt-6">
        <ActiveThreatBanner threat={activeThreat} />
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
        {filtered.length === 0 ? (
          <div className="text-center py-16 text-on-surface-variant">
            <span className="material-symbols-outlined text-5xl block mb-3 opacity-30">check_circle</span>
            <p className="font-headline font-bold uppercase tracking-widest text-sm">All Clear</p>
            <p className="font-body text-xs mt-1 opacity-60">No {activeFilter.toLowerCase()} alerts in your area</p>
          </div>
        ) : (
          filtered.map((threat) => <ThreatCard key={threat.id} threat={threat} />)
        )}
      </div>
    </div>
  )
}
