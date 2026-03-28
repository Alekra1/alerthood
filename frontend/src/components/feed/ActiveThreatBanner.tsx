import type { Threat } from '../../types'

interface ActiveThreatBannerProps {
  threat: Threat
}

export function ActiveThreatBanner({ threat }: ActiveThreatBannerProps) {
  const timeLabel =
    threat.minutesAgo < 60
      ? `${threat.minutesAgo}m ago`
      : `${Math.floor(threat.minutesAgo / 60)}h ago`

  return (
    <div className="mb-8 bg-secondary-container text-on-secondary-container p-4 border-2 border-black shadow-hard relative overflow-hidden">
      <div className="flex items-start justify-between relative z-10">
        <div className="flex flex-col gap-1">
          <span className="font-headline font-bold text-xs uppercase tracking-widest bg-black text-secondary px-2 py-0.5 w-fit">
            ACTIVE THREAT
          </span>
          <h2 className="font-headline font-bold text-lg leading-tight">{threat.title}</h2>
          <p className="font-label font-bold text-[10px] opacity-80">
            {timeLabel} • Reported by {threat.source}
          </p>
        </div>
        <span className="material-symbols-outlined text-3xl opacity-30">warning</span>
      </div>
      <div className="absolute -right-4 -bottom-4 opacity-10">
        <span
          className="material-symbols-outlined text-8xl"
          style={{ fontVariationSettings: "'FILL' 1" }}
        >
          warning
        </span>
      </div>
    </div>
  )
}
