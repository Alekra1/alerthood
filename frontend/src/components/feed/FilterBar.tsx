import type { ThreatCategory } from '../../types'

type FilterValue = 'ALL' | ThreatCategory

const FILTERS: FilterValue[] = ['ALL', 'CRIME', 'UTILITY', 'NATURAL', 'DISTURBANCE']

interface FilterBarProps {
  active: FilterValue
  onChange: (filter: FilterValue) => void
}

export function FilterBar({ active, onChange }: FilterBarProps) {
  return (
    <div className="flex overflow-x-auto hide-scrollbar gap-2 pb-2">
      {FILTERS.map((filter) => (
        <button
          key={filter}
          onClick={() => onChange(filter)}
          className={[
            'whitespace-nowrap font-headline font-bold text-xs px-4 py-2 border-2 border-black transition-none',
            active === filter
              ? 'bg-primary-container text-on-primary-container shadow-hard-sm'
              : 'bg-surface-container text-on-surface shadow-hard-sm hover:bg-surface-container-high',
          ].join(' ')}
        >
          {filter}
        </button>
      ))}
    </div>
  )
}
