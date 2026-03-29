import { useState } from 'react'
import type { Threat, ThreatCategory } from '../../types'
import { supabase } from '../../lib/supabase'
import { useAuth } from '../../context/AuthContext'

const IMPACT_BAR: Record<ThreatCategory, string> = {
  CRIME: 'bg-primary-container',
  UTILITY: 'bg-secondary-container',
  NATURAL: 'bg-yellow-400',
  DISTURBANCE: 'bg-tertiary-container',
}

const CATEGORY_TEXT: Record<ThreatCategory, string> = {
  CRIME: 'text-primary',
  UTILITY: 'text-secondary',
  NATURAL: 'text-yellow-400',
  DISTURBANCE: 'text-tertiary',
}

const SEVERITY_BADGE: Record<string, string> = {
  CRITICAL: 'bg-error-container text-white border-black',
  HIGH: 'bg-primary-container text-on-primary-container border-black',
  MEDIUM: 'bg-secondary-container text-on-secondary-container border-black',
  LOW: 'bg-surface-container text-on-surface border-outline',
}

interface ThreatCardProps {
  threat: Threat
  initialVote?: 'up' | 'down' | null
  onViewMap?: (threat: Threat) => void
}

export function ThreatCard({ threat, initialVote = null, onViewMap }: ThreatCardProps) {
  const { user } = useAuth()
  const [vote, setVote] = useState<'up' | 'down' | null>(initialVote)
  const [upvotes, setUpvotes] = useState(threat.upvotes)
  const [downvotes, setDownvotes] = useState(threat.downvotes)

  async function handleVote(dir: 'up' | 'down') {
    if (!user) return
    const removing = vote === dir

    // Optimistic update
    if (removing) {
      dir === 'up' ? setUpvotes(v => v - 1) : setDownvotes(v => v - 1)
      setVote(null)
    } else {
      if (vote === 'up') setUpvotes(v => v - 1)
      if (vote === 'down') setDownvotes(v => v - 1)
      dir === 'up' ? setUpvotes(v => v + 1) : setDownvotes(v => v + 1)
      setVote(dir)
    }

    // Persist
    if (removing) {
      const { error } = await supabase.from('event_votes').delete().match({ user_id: user.id, event_id: threat.id })
      if (error) console.error('vote delete error:', error)
    } else {
      const { error } = await supabase.from('event_votes').upsert(
        { user_id: user.id, event_id: threat.id, vote: dir === 'up' ? 1 : -1 },
        { onConflict: 'user_id,event_id' }
      )
      if (error) console.error('vote upsert error:', error)
    }
  }

  const timeLabel =
    threat.minutesAgo < 60
      ? `${threat.minutesAgo}m ago`
      : `${Math.floor(threat.minutesAgo / 60)}h ago`

  const impactBar = IMPACT_BAR[threat.category]
  const categoryText = CATEGORY_TEXT[threat.category]
  const severityBadge = SEVERITY_BADGE[threat.severity]

  return (
    <article className="group relative bg-surface-container border-2 border-black shadow-hard rounded-lg overflow-hidden transition-none active:translate-x-[2px] active:translate-y-[2px] active:shadow-none">
      <div className={`absolute left-0 top-0 bottom-0 w-1.5 ${impactBar}`} />

      <div className="p-5 pl-8">
        <div className="flex justify-between items-start mb-2">
          <span className={`font-label font-bold text-[10px] uppercase ${categoryText}`}>
            {threat.category} • {timeLabel}
          </span>
          {threat.severity === 'CRITICAL' ? (
            <div className={`border-2 px-4 py-1 rounded-full shadow-hard-sm text-center ${severityBadge}`}>
              <span className="font-label font-black text-[9px] uppercase tracking-tighter">CRITICAL</span>
            </div>
          ) : (
            <button className="opacity-50 hover:opacity-100 transition-none" aria-label="More options">
              <span className="material-symbols-outlined text-sm">more_vert</span>
            </button>
          )}
        </div>

        <h3 className="font-headline font-bold text-xl leading-snug mb-4">{threat.title}</h3>

        <div className="grid grid-cols-2 gap-2 mb-4">
          <div className="bg-surface-container-low border-2 border-black p-2">
            <p className="font-label font-bold text-[9px] text-primary-container uppercase">Severity</p>
            <p className="font-headline font-black text-lg">{threat.severityPct}%</p>
          </div>
          <div className="bg-surface-container-low border-2 border-black p-2">
            <p className="font-label font-bold text-[9px] text-secondary-container uppercase">Relevance</p>
            <p className="font-headline font-black text-lg">{threat.relevancePct}%</p>
          </div>
        </div>

        <div className="flex items-center justify-between border-t-2 border-black pt-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => handleVote('up')}
              className={`flex items-center gap-1.5 transition-none ${vote === 'up' ? 'text-error' : ''}`}
              aria-label={`Upvote (${upvotes})`}
            >
              <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: vote === 'up' ? "'FILL' 1" : "'FILL' 0" }}>arrow_upward</span>
              <span className="font-label font-bold text-xs">{upvotes}</span>
            </button>
            <button
              onClick={() => handleVote('down')}
              className={`flex items-center gap-1.5 transition-none ${vote === 'down' ? 'text-error' : ''}`}
              aria-label={`Downvote (${downvotes})`}
            >
              <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: vote === 'down' ? "'FILL' 1" : "'FILL' 0" }}>arrow_downward</span>
              <span className="font-label font-bold text-xs">{downvotes}</span>
            </button>
          </div>
          <button
            className="bg-background text-on-surface border-2 border-black px-3 py-1 font-label font-bold text-[10px] uppercase shadow-hard-sm active:shadow-none active:translate-x-[1px] active:translate-y-[1px] transition-none"
            onClick={() => onViewMap?.(threat)}
          >
            VIEW MAP
          </button>
        </div>
      </div>
    </article>
  )
}
