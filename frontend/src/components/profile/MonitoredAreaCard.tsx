import { useState } from 'react'
import type { MonitoredArea } from '../../types'

type NotifyKey = 'notifyCrime' | 'notifyUtility' | 'notifyNatural' | 'notifyDisturbance'

const TOGGLES: Array<{ key: NotifyKey; label: string }> = [
  { key: 'notifyCrime', label: 'CRIME' },
  { key: 'notifyUtility', label: 'INFRA' },
  { key: 'notifyNatural', label: 'NATURAL' },
  { key: 'notifyDisturbance', label: 'DISTURB' },
]

interface MonitoredAreaCardProps {
  area: MonitoredArea
  onDelete?: (id: string) => void
}

export function MonitoredAreaCard({ area, onDelete }: MonitoredAreaCardProps) {
  const [toggles, setToggles] = useState<Record<NotifyKey, boolean>>({
    notifyCrime: area.notifyCrime,
    notifyUtility: area.notifyUtility,
    notifyNatural: area.notifyNatural,
    notifyDisturbance: area.notifyDisturbance,
  })

  const toggle = (key: NotifyKey) => {
    setToggles((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="bg-surface-container border-2 border-black shadow-hard rounded-xl overflow-hidden">
      <div className="h-32 w-full relative bg-surface-container-lowest flex items-center justify-center">
        <span
          className="material-symbols-outlined text-6xl opacity-20 text-on-surface"
          style={{ fontVariationSettings: "'FILL' 1" }}
        >
          map
        </span>
        <div className="absolute top-2 right-2 flex gap-2">
          {onDelete ? (
            <button
              className="bg-surface p-2 border-2 border-black shadow-hard-sm rounded-full active:shadow-none active:translate-x-[1px] active:translate-y-[1px]"
              onClick={() => onDelete(area.id)}
              aria-label="Delete area"
            >
              <span className="material-symbols-outlined text-sm text-error">delete</span>
            </button>
          ) : (
            <button
              className="bg-surface p-2 border-2 border-black shadow-hard-sm rounded-full active:shadow-none active:translate-x-[1px] active:translate-y-[1px]"
              aria-label="Edit area"
            >
              <span className="material-symbols-outlined text-sm">edit</span>
            </button>
          )}
        </div>
        {area.isActive && (
          <div className="absolute bottom-2 left-3 bg-black/80 px-2 py-1 border border-primary">
            <span className="text-[10px] font-black uppercase text-primary italic">ACTIVE SHIELD ON</span>
          </div>
        )}
      </div>

      <div className="p-4 space-y-4">
        <div className="flex justify-between items-start">
          <div>
            <h4 className="font-headline text-lg font-bold">{area.name}</h4>
            <p className="text-xs font-label text-on-surface-variant">
              {area.radiusMiles}MI RADIUS • {area.neighborhood}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {TOGGLES.map(({ key, label }) => {
            const isOn = toggles[key]
            return (
              <button
                key={key}
                onClick={() => toggle(key)}
                className="flex items-center justify-between bg-surface-container-low p-2 border border-outline-variant rounded-lg"
                aria-pressed={isOn}
              >
                <span className="text-[10px] font-bold uppercase tracking-tighter">{label}</span>
                <div
                  className={`w-8 h-4 rounded-full relative flex items-center px-1 transition-none ${isOn ? 'bg-primary-container' : 'bg-surface-variant'}`}
                >
                  <div
                    className={`w-2 h-2 rounded-full transition-none ${isOn ? 'bg-on-primary-container ml-auto' : 'bg-on-surface-variant'}`}
                  />
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
