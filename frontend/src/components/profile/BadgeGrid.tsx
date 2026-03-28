import type { Badge } from '../../types'

const COLOR_MAP: Record<Badge['color'], string> = {
  primary: 'text-primary',
  secondary: 'text-secondary',
  tertiary: 'text-tertiary',
}

// CSS filters to recolour the black SVGs to theme colours
const FILTER_MAP: Record<Badge['color'], string> = {
  primary:   'invert(29%) sepia(97%) saturate(500%) hue-rotate(190deg) brightness(95%)',
  secondary: 'invert(40%) sepia(60%) saturate(400%) hue-rotate(130deg) brightness(90%)',
  tertiary:  'invert(35%) sepia(50%) saturate(600%) hue-rotate(270deg) brightness(90%)',
}

function colorToFilter(color: Badge['color']) {
  return FILTER_MAP[color]
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
            <img
              src={badge.icon}
              alt={badge.name}
              className={`w-7 h-7 ${badge.earned ? COLOR_MAP[badge.color] : 'opacity-40'}`}
              style={{ filter: badge.earned ? colorToFilter(badge.color) : 'none' }}
            />
            <span className="text-[10px] font-bold leading-none uppercase">{badge.name}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
