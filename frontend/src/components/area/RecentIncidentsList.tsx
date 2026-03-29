import { useNavigate } from 'react-router-dom'
import type { Threat } from '../../types'

const CATEGORY_STYLE: Record<string, { bg: string; text: string }> = {
  CRIME: { bg: 'bg-primary-container', text: 'text-on-primary-container' },
  UTILITY: { bg: 'bg-secondary-container', text: 'text-on-secondary-container' },
  DISTURBANCE: { bg: 'bg-tertiary-container', text: 'text-on-tertiary-container' },
  NATURAL: { bg: 'bg-yellow-400', text: 'text-yellow-900' },
}

function timeAgo(minutesAgo: number): string {
  if (minutesAgo < 60) return `${minutesAgo}m ago`
  const h = Math.floor(minutesAgo / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

interface RecentIncidentsListProps {
  events: Threat[]
}

export function RecentIncidentsList({ events }: RecentIncidentsListProps) {
  const navigate = useNavigate()

  return (
    <div className="flex flex-col gap-3">
      {/* Section header */}
      <div className="flex items-center gap-3">
        <span className="w-6 h-1 bg-primary-container block" />
        <h2 className="font-headline font-bold text-xl uppercase tracking-tight text-on-surface">
          Recent Activity
        </h2>
      </div>

      {events.length === 0 ? (
        <div className="bg-surface-container border-2 border-black rounded-xl p-4 text-center">
          <p className="font-body text-sm text-on-surface-variant">No recent incidents in this area.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {events.map((event) => {
            const style = CATEGORY_STYLE[event.category] ?? CATEGORY_STYLE.CRIME
            return (
              <div
                key={event.id}
                className="bg-surface-container border-2 border-black rounded-xl px-4 py-3 flex flex-col gap-1"
              >
                {/* Top row */}
                <div className="flex items-center gap-2">
                  <span className={`font-headline font-bold text-[10px] uppercase tracking-widest px-2 py-0.5 rounded ${style.bg} ${style.text}`}>
                    {event.category}
                  </span>
                  <span className="ml-auto font-body text-xs text-on-surface-variant uppercase font-bold">
                    {timeAgo(event.minutesAgo)}
                  </span>
                </div>

                {/* Title */}
                <p className="font-body text-sm text-on-surface leading-snug line-clamp-2">
                  {event.title}
                </p>

                {/* Upvotes */}
                <div className="flex items-center gap-1">
                  <span className="font-body text-xs text-on-surface-variant">▲ {event.upvotes}</span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Footer link */}
      <button
        onClick={() => navigate('/feed')}
        className="self-start font-body text-sm text-primary-container font-semibold flex items-center gap-1 mt-1"
      >
        See all in Feed
        <span className="material-symbols-outlined text-sm">arrow_forward</span>
      </button>
    </div>
  )
}
