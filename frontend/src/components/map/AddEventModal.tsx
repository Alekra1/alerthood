import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'

export type EventFormThreatType = 'crime' | 'infrastructure' | 'disturbance' | 'natural'
export type EventFormSeverity = 'low' | 'medium' | 'high' | 'critical'

export interface AddEventFormValues {
  title: string
  description: string
  threatType: EventFormThreatType
  severity: EventFormSeverity
}

interface AddEventModalProps {
  error: string | null
  isSubmitting: boolean
  location: [number, number]
  onClose: () => void
  onSubmit: (values: AddEventFormValues) => Promise<void> | void
}

const TYPE_OPTIONS: Array<{ value: EventFormThreatType; label: string; accentClass: string }> = [
  { value: 'crime', label: 'Crime', accentClass: 'bg-primary-container text-on-primary-container' },
  { value: 'infrastructure', label: 'Utility', accentClass: 'bg-secondary-container text-on-secondary-container' },
  { value: 'disturbance', label: 'Disturbance', accentClass: 'bg-tertiary-container text-on-tertiary-container' },
  { value: 'natural', label: 'Natural', accentClass: 'bg-yellow-400 text-black' },
]

const SEVERITY_OPTIONS: Array<{ value: EventFormSeverity; label: string }> = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
]

export function AddEventModal({
  error,
  isSubmitting,
  location,
  onClose,
  onSubmit,
}: AddEventModalProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [threatType, setThreatType] = useState<EventFormThreatType>('crime')
  const [severity, setSeverity] = useState<EventFormSeverity>('medium')
  const titleRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    titleRef.current?.focus()

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isSubmitting) {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isSubmitting, onClose])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!title.trim() || !description.trim()) return
    await onSubmit({
      title: title.trim(),
      description: description.trim(),
      threatType,
      severity,
    })
  }

  return (
    <div
      className="fixed inset-0 z-[70] bg-black/75 flex items-stretch md:items-center justify-center pt-16 pb-20 md:pt-0 md:pb-0 md:p-4"
      onClick={() => {
        if (!isSubmitting) onClose()
      }}
    >
      <form
        onSubmit={handleSubmit}
        onClick={(event) => event.stopPropagation()}
        className="w-full md:max-w-xl h-full md:h-auto md:max-h-[calc(100dvh-2rem)] bg-surface-container border-[3px] md:border-[3px] border-black shadow-[8px_8px_0px_#000000] flex flex-col overflow-hidden"
      >
        <div className="flex-1 overflow-y-auto px-5 md:px-6 pt-5 md:py-6 pb-5 space-y-5">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <p className="font-headline text-[11px] uppercase tracking-[0.35em] text-on-surface-variant">
                Report Event
              </p>
              <h2 className="font-headline text-2xl uppercase tracking-tight text-on-surface">
                Add Alert From Your Location
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="w-11 h-11 shrink-0 bg-surface-container-high border-[3px] border-black shadow-hard flex items-center justify-center active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-none disabled:opacity-50"
              aria-label="Close event form"
            >
              <span className="material-symbols-outlined text-on-surface">close</span>
            </button>
          </div>

          <div className="bg-surface-container-lowest border-[3px] border-black p-4 space-y-1">
            <p className="font-headline text-[10px] uppercase tracking-[0.3em] text-on-surface-variant">
              Location
            </p>
            <p className="font-headline text-sm uppercase tracking-wide text-on-surface">
              This alert will use your current position
            </p>
            <p className="font-body text-xs text-on-surface-variant">
              {location[0].toFixed(5)}, {location[1].toFixed(5)}
            </p>
          </div>

          <label className="block space-y-2">
            <span className="font-headline text-[10px] uppercase tracking-[0.3em] text-on-surface-variant">
              Title
            </span>
            <input
              ref={titleRef}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="What is happening?"
              maxLength={120}
              className="w-full bg-surface-container-lowest border-[3px] border-black px-4 py-3 font-body text-sm text-on-surface placeholder:text-on-surface/35 outline-none"
            />
          </label>

          <label className="block space-y-2">
            <span className="font-headline text-[10px] uppercase tracking-[0.3em] text-on-surface-variant">
              Description
            </span>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Add the details someone nearby should know."
              rows={4}
              maxLength={600}
              className="w-full resize-none bg-surface-container-lowest border-[3px] border-black px-4 py-3 font-body text-sm text-on-surface placeholder:text-on-surface/35 outline-none"
            />
          </label>

          <div className="space-y-2">
            <span className="block font-headline text-[10px] uppercase tracking-[0.3em] text-on-surface-variant">
              Event Type
            </span>
            <div className="grid grid-cols-2 gap-3">
              {TYPE_OPTIONS.map((option) => {
                const active = threatType === option.value
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setThreatType(option.value)}
                    className={`border-[3px] border-black px-4 py-3 font-headline text-sm uppercase tracking-wide text-left transition-none active:translate-x-[2px] active:translate-y-[2px] active:shadow-none ${
                      active
                        ? `${option.accentClass} shadow-hard`
                        : 'bg-surface-container-lowest text-on-surface'
                    }`}
                  >
                    {option.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="space-y-2">
            <span className="block font-headline text-[10px] uppercase tracking-[0.3em] text-on-surface-variant">
              Severity
            </span>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {SEVERITY_OPTIONS.map((option) => {
                const active = severity === option.value
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setSeverity(option.value)}
                    className={`border-[3px] border-black px-3 py-3 font-headline text-sm uppercase tracking-wide transition-none active:translate-x-[2px] active:translate-y-[2px] active:shadow-none ${
                      active
                        ? 'bg-primary text-on-primary shadow-hard'
                        : 'bg-surface-container-lowest text-on-surface'
                    }`}
                  >
                    {option.label}
                  </button>
                )
              })}
            </div>
          </div>

          {error && (
            <div className="bg-error-container text-on-error-container border-[3px] border-black px-4 py-3 font-body text-sm">
              {error}
            </div>
          )}
        </div>

        <div className="border-t-[3px] border-black px-5 md:px-6 pt-4 md:pt-5 pb-5 md:pb-6 bg-surface-container">
          <div className="flex flex-col-reverse md:flex-row md:justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-5 py-3 bg-surface-container-high text-on-surface border-[3px] border-black font-headline text-sm uppercase tracking-wide transition-none active:translate-x-[2px] active:translate-y-[2px] active:shadow-none disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !title.trim() || !description.trim()}
              className="px-5 py-3 bg-primary-container text-on-primary-container border-[3px] border-black font-headline text-sm uppercase tracking-wide shadow-hard transition-none active:translate-x-[2px] active:translate-y-[2px] active:shadow-none disabled:opacity-50 disabled:shadow-none"
            >
              {isSubmitting ? 'Reporting...' : 'Report Event'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
