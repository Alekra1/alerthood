import type { Badge } from '../../types'

const COLOR_MAP: Record<Badge['color'], string> = {
  primary: 'text-primary',
  secondary: 'text-secondary',
  tertiary: 'text-tertiary',
}

interface BadgeGridProps {
  badges: Badge[]
}

export function BadgeGrid({ badges }: BadgeGridProps) {
  return (
    <section className="space-y-4">
      <h3 className="font-headline text-xl font-bold uppercase tracking-tight flex items-center gap-2">
        <span className="w-6 h-1 bg-primary inline-block" />
        ACHIEVEMENTS
      </h3>
      <div className="grid grid-cols-3 gap-3">
        {badges.map((badge) => (
          <div
            key={badge.id}
            className={[
              'border-2 border-black shadow-hard p-3 rounded-lg flex flex-col items-center text-center gap-2',
              badge.earned
                ? 'bg-surface-container'
                : 'bg-surface-container-low opacity-40',
            ].join(' ')}
          >
            <span
              className={`material-symbols-outlined text-3xl ${badge.earned ? COLOR_MAP[badge.color] : 'text-on-surface-variant'}`}
              style={{ fontVariationSettings: badge.earned ? "'FILL' 1" : "'FILL' 0" }}
            >
              {badge.icon}
            </span>
            <span className="text-[10px] font-bold leading-none uppercase">{badge.name}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
