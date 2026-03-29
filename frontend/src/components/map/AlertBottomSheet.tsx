import { useState } from 'react'
import type { Threat } from '../../types'
import { supabase } from '../../lib/supabase'
import { useAuth } from '../../context/AuthContext'

const CATEGORY_COLORS: Record<string, string> = {
  CRIME: 'bg-error-container text-on-error-container',
  UTILITY: 'bg-secondary-container text-on-secondary-container',
  NATURAL: 'bg-yellow-500 text-black',
  DISTURBANCE: 'bg-tertiary-container text-on-tertiary-container',
}

const IMPACT_BAR_COLORS: Record<string, string> = {
  CRIME: 'bg-primary-container',
  UTILITY: 'bg-secondary-container',
  NATURAL: 'bg-yellow-400',
  DISTURBANCE: 'bg-tertiary-container',
}

interface AlertBottomSheetProps {
  threat: Threat
  onClose: () => void
}

export function AlertBottomSheet({ threat, onClose }: AlertBottomSheetProps) {
  const { user } = useAuth()
  const [copied, setCopied] = useState(false)
  const [vote, setVote] = useState<'up' | 'down' | null>(null)
  const [upvotes, setUpvotes] = useState(threat.upvotes)
  const [downvotes, setDownvotes] = useState(threat.downvotes)

  async function handleVote(dir: 'up' | 'down') {
    if (!user) return
    const removing = vote === dir
    if (removing) {
      dir === 'up' ? setUpvotes(v => v - 1) : setDownvotes(v => v - 1)
      setVote(null)
    } else {
      if (vote === 'up') setUpvotes(v => v - 1)
      if (vote === 'down') setDownvotes(v => v - 1)
      dir === 'up' ? setUpvotes(v => v + 1) : setDownvotes(v => v + 1)
      setVote(dir)
    }
    if (removing) {
      await supabase.from('event_votes').delete().match({ user_id: user.id, event_id: threat.id })
    } else {
      await supabase.from('event_votes').upsert(
        { user_id: user.id, event_id: threat.id, vote: dir === 'up' ? 1 : -1 },
        { onConflict: 'user_id,event_id' }
      )
    }
  }

  const categoryBadgeClass = CATEGORY_COLORS[threat.category] ?? 'bg-surface-container text-on-surface'
  const impactBarClass = IMPACT_BAR_COLORS[threat.category] ?? 'bg-primary-container'
  const timeLabel =
    threat.minutesAgo < 60
      ? `${threat.minutesAgo} mins ago`
      : `${Math.floor(threat.minutesAgo / 60)}h ago`

  function handleCopy() {
    if (!threat.sourceUrl) return
    navigator.clipboard.writeText(threat.sourceUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="absolute bottom-4 left-4 right-4 md:left-auto md:right-6 md:w-96 z-50">
      {copied && (
        <div className="mb-2 px-4 py-2 bg-black text-white font-label font-bold text-xs uppercase tracking-widest text-center border-2 border-black">
          COPIED
        </div>
      )}
      <div className="bg-surface-container border-[3px] border-black rounded-xl overflow-hidden shadow-[8px_8px_0px_#000000] relative">
        <div className={`absolute left-0 top-0 bottom-0 w-[6px] ${impactBarClass}`} />

        <button
          className="absolute top-3 right-3 p-1 hover:bg-surface-container-high active:translate-x-[1px] active:translate-y-[1px] transition-none z-10"
          onClick={onClose}
          aria-label="Close alert"
        >
          <span className="material-symbols-outlined text-sm text-on-surface-variant">close</span>
        </button>

        <div className="p-5 pl-8">
          <div className="flex justify-between items-center mb-2 pr-6">
            <span
              className={`text-[10px] font-bold tracking-widest uppercase px-3 py-1 rounded-full border border-black inline-block ${categoryBadgeClass}`}
            >
              {threat.category}
            </span>
            <div className="flex flex-row gap-1 shrink-0">
              <button
                onClick={() => handleVote('up')}
                className={`border-2 border-black px-2 py-1 flex items-center gap-1 transition-none active:translate-x-[1px] active:translate-y-[1px] ${vote === 'up' ? 'bg-primary-container text-on-primary-container' : 'bg-surface-container-high text-on-surface'}`}
                aria-label={`Upvote (${upvotes})`}
              >
                <span className="material-symbols-outlined text-sm">arrow_upward</span>
                <span className="font-label font-bold text-xs">{upvotes}</span>
              </button>
              <button
                onClick={() => handleVote('down')}
                className={`border-2 border-black px-2 py-1 flex items-center gap-1 transition-none active:translate-x-[1px] active:translate-y-[1px] ${vote === 'down' ? 'bg-primary-container text-on-primary-container' : 'bg-surface-container-high text-on-surface'}`}
                aria-label={`Downvote (${downvotes})`}
              >
                <span className="material-symbols-outlined text-sm">arrow_downward</span>
                <span className="font-label font-bold text-xs">{downvotes}</span>
              </button>
            </div>
          </div>

          <div className="mb-4 pr-6">
            <h2 className="font-headline text-xl text-on-surface leading-tight">{threat.title}</h2>
            <p className="font-label text-xs text-on-surface-variant mt-1">
              {threat.location} • {timeLabel}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-surface-container-lowest border-2 border-black p-3">
              <label className="text-[10px] font-bold text-on-surface-variant block mb-1 uppercase tracking-tighter">
                Severity
              </label>
              <div className="w-full h-3 bg-black border border-outline-variant relative">
                <div
                  className="absolute inset-y-0 left-0 bg-primary-container"
                  style={{ width: `${threat.severityPct}%` }}
                />
              </div>
              <span className="text-xs font-bold mt-1 inline-block">{threat.severityPct}%</span>
            </div>
            <div className="bg-surface-container-lowest border-2 border-black p-3">
              <label className="text-[10px] font-bold text-on-surface-variant block mb-1 uppercase tracking-tighter">
                Source
              </label>
              <span className="text-sm font-bold uppercase">{threat.source}</span>
            </div>
          </div>

          <div className="flex gap-3">
            <a
              href={threat.sourceUrl ?? undefined}
              target="_blank"
              rel="noopener noreferrer"
              aria-disabled={!threat.sourceUrl}
              className={`flex-1 flex items-center justify-center font-headline py-3 border-[3px] border-black uppercase text-sm tracking-wider transition-none ${
                threat.sourceUrl
                  ? 'bg-primary-container text-on-primary-container shadow-hard active:translate-x-[2px] active:translate-y-[2px] active:shadow-none'
                  : 'bg-surface-container text-on-surface/40 pointer-events-none border-black/30'
              }`}
            >
              {threat.sourceUrl ? 'VIEW SOURCE' : 'SOURCE UNAVAILABLE'}
            </a>
            <button
              onClick={handleCopy}
              disabled={!threat.sourceUrl}
              className="w-14 bg-surface-container-high text-on-surface font-headline border-[3px] border-black shadow-hard active:translate-x-[2px] active:translate-y-[2px] active:shadow-none flex items-center justify-center transition-none disabled:opacity-40 disabled:pointer-events-none"
              aria-label="Copy source link"
            >
              <span className="material-symbols-outlined">{copied ? 'check' : 'share'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
