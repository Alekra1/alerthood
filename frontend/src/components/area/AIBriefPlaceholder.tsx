export function AIBriefPlaceholder() {
  return (
    <div className="bg-surface-container border-2 border-dashed border-black rounded-xl p-5 opacity-50">
      <div className="flex items-center gap-2 mb-3">
        <span className="material-symbols-outlined text-xl" style={{ color: '#E8B3FF' }}>
          auto_awesome
        </span>
        <span
          className="font-headline font-bold text-xs uppercase tracking-widest"
          style={{ color: '#E8B3FF' }}
        >
          AI Area Brief · Coming Soon
        </span>
      </div>
      <p className="font-body text-sm text-on-surface-variant leading-relaxed">
        AI-powered safety recommendations based on current conditions, time of day, and your travel patterns — coming soon.
      </p>
    </div>
  )
}
