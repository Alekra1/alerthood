import type { ThreatSeverity } from '../../types'

type SeverityFilter = 'ALL' | ThreatSeverity

const FILTERS: { value: SeverityFilter; label: string }[] = [
  { value: 'ALL', label: 'ALL' },
  { value: 'LOW', label: 'LOW' },
  { value: 'MEDIUM', label: 'MEDIUM' },
  { value: 'HIGH', label: 'HIGH' },
  { value: 'CRITICAL', label: 'CRITICAL' },
]

const ACTIVE_COLORS: Record<SeverityFilter, string> = {
  ALL: 'bg-primary-container text-on-primary-container',
  LOW: 'bg-green-100 text-green-900 border-green-900',
  MEDIUM: 'bg-yellow-100 text-yellow-900 border-yellow-900',
  HIGH: 'bg-orange-100 text-orange-900 border-orange-900',
  CRITICAL: 'bg-red-100 text-red-900 border-red-900',
}

interface SeverityBarProps {
  active: SeverityFilter
  onChange: (filter: SeverityFilter) => void
}

export function SeverityBar({ active, onChange }: SeverityBarProps) {
  return (
    <div className="flex overflow-x-auto hide-scrollbar gap-2 pb-2">
      {FILTERS.map(({ value, label }) => (
        <button
          key={value}
          onClick={() => onChange(value)}
          className={[
            'whitespace-nowrap font-headline font-bold text-xs px-4 py-2 border-2 border-black transition-none shadow-hard-sm',
            active === value
              ? ACTIVE_COLORS[value]
              : 'bg-surface-container text-on-surface hover:bg-surface-container-high',
          ].join(' ')}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
