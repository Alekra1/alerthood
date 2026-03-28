import type { Threat } from '../../types'

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
  onViewDetails: (threat: Threat) => void
}

export function AlertBottomSheet({ threat, onClose, onViewDetails }: AlertBottomSheetProps) {
  const categoryBadgeClass = CATEGORY_COLORS[threat.category] ?? 'bg-surface-container text-on-surface'
  const impactBarClass = IMPACT_BAR_COLORS[threat.category] ?? 'bg-primary-container'
  const timeLabel =
    threat.minutesAgo < 60
      ? `${threat.minutesAgo} mins ago`
      : `${Math.floor(threat.minutesAgo / 60)}h ago`

  return (
    <div className="absolute bottom-4 left-4 right-4 md:left-auto md:right-6 md:w-96 z-40">
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
          <div className="flex justify-between items-start mb-4 pr-6">
            <div>
              <span
                className={`text-[10px] font-bold tracking-widest uppercase px-3 py-1 rounded-full border border-black mb-2 inline-block ${categoryBadgeClass}`}
              >
                {threat.category}
              </span>
              <h2 className="font-headline text-xl text-on-surface leading-tight">{threat.title}</h2>
              <p className="font-label text-xs text-on-surface-variant mt-1">
                {threat.location} • {timeLabel}
              </p>
            </div>
            <div className="bg-surface-container-high border-2 border-black p-2 flex flex-col items-center ml-2 shrink-0">
              <span className="text-xs font-bold text-primary">{threat.upvotes}</span>
              <span
                className="material-symbols-outlined text-sm"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                thumb_up
              </span>
            </div>
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
                Relevance
              </label>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-headline text-secondary">{threat.relevancePct}</span>
                <span className="text-xs font-bold text-secondary">%</span>
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              className="flex-1 bg-primary-container text-on-primary-container font-headline py-3 border-[3px] border-black shadow-hard active:translate-x-[2px] active:translate-y-[2px] active:shadow-none uppercase text-sm tracking-wider transition-none"
              onClick={() => onViewDetails(threat)}
            >
              VIEW DETAILS
            </button>
            <button
              className="w-14 bg-surface-container-high text-on-surface font-headline border-[3px] border-black shadow-hard active:translate-x-[2px] active:translate-y-[2px] active:shadow-none flex items-center justify-center transition-none"
              aria-label="Share alert"
            >
              <span className="material-symbols-outlined">share</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
