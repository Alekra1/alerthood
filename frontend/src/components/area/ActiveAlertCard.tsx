import type { Threat } from '../../types'

interface ActiveAlertCardProps {
  event: Threat
}

export function ActiveAlertCard({ event }: ActiveAlertCardProps) {
  const isHighest = event.severity === 'CRITICAL'
  const barColor = isHighest ? '#FF5545' : '#FE9400'
  const labelColor = isHighest ? 'text-primary-container' : 'text-secondary-container'

  const hoursAgo = Math.floor(event.minutesAgo / 60)
  const timeLabel = event.minutesAgo < 60
    ? `${event.minutesAgo}m ago`
    : `${hoursAgo}h ago`

  return (
    <div
      className="bg-surface-container border-2 border-black shadow-hard rounded-xl overflow-hidden flex"
    >
      {/* Left impact bar */}
      <div className="w-1.5 flex-shrink-0" style={{ backgroundColor: barColor }} />

      <div className="flex-1 p-4 flex flex-col gap-2">
        {/* Header */}
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-base" style={{ color: barColor }}>
            warning
          </span>
          <span className={`font-headline font-bold text-xs tracking-widest uppercase ${labelColor}`}>
            ACTIVE ALERT
          </span>
          <span className="ml-auto font-body text-xs text-on-surface-variant">{timeLabel}</span>
        </div>

        {/* Body */}
        <p className="font-body text-sm text-on-surface leading-snug line-clamp-3">
          {event.title}
          {event.location ? ` — ${event.location}` : ''}
        </p>
      </div>
    </div>
  )
}
