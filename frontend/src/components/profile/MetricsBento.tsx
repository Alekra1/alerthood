interface MetricsBentoProps {
  karma: number
  karmaWeekly: number
}

export function MetricsBento({ karma, karmaWeekly }: MetricsBentoProps) {
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
    </section>
  )
}
