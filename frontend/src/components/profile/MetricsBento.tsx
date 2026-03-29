interface MetricsBentoProps {
  karma: number
  karmaWeekly: number
  trustScore: number
}

function trustColor(score: number): string {
  if (score >= 90) return '#4ade80'
  if (score >= 70) return '#eab308'
  if (score >= 40) return '#f97316'
  return '#ef4444'
}

export function MetricsBento({ karma, karmaWeekly, trustScore }: MetricsBentoProps) {
  const filled = Math.round(trustScore / 10)
  const color = trustColor(trustScore)

  return (
    <section className="flex gap-3">
      {/* Karma */}
      <div className="flex-1 bg-on-background px-4 py-3 border-2 border-black shadow-hard-sm flex flex-col justify-between gap-1">
        <span className="font-label text-[9px] font-black text-black/50 uppercase tracking-widest">
          KARMA
        </span>
        <div className="flex items-baseline gap-1.5">
          <span className="font-headline text-2xl font-black text-black leading-none">
            {karma.toLocaleString()}
          </span>
          {karmaWeekly > 0 && (
            <span className="font-label text-[9px] text-black/50 font-bold italic leading-none">
              +{karmaWeekly}/wk
            </span>
          )}
        </div>
      </div>

      {/* Trust Score */}
      <div className="flex-1 bg-surface-container px-4 py-3 border-2 border-black shadow-hard-sm flex flex-col justify-between gap-2">
        <div className="flex items-center justify-between">
          <span className="font-label text-[9px] font-black uppercase tracking-widest text-on-surface/50">
            TRUST SCORE
          </span>
          <span
            className="font-headline text-sm font-black leading-none"
            style={{ color }}
          >
            {trustScore}%
          </span>
        </div>

        {/* Segmented bar */}
        <div className="flex gap-[2px]">
          {Array.from({ length: 10 }).map((_, i) => (
            <div
              key={i}
              className="h-[6px] flex-1 rounded-[1px] transition-none"
              style={{ background: i < filled ? color : '#2A2A2A' }}
            />
          ))}
        </div>
      </div>
    </section>
  )
}
