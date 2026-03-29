import type { SafeRouteResponse } from '../../hooks/useSafeRoute'

interface SafeRouteOverlayProps {
  route: SafeRouteResponse
  loading: boolean
  error: string | null
  onClear: () => void
  onOpenMaps: () => void
}

export function SafeRouteOverlay({ route, loading, error, onClear, onOpenMaps }: SafeRouteOverlayProps) {
  if (loading) {
    return (
      <div className="fixed top-20 left-1/2 -translate-x-1/2 z-40 bg-surface-container border-[3px] border-black px-4 py-3 shadow-hard w-[90%] max-w-sm flex items-center justify-between">
        <span className="font-headline text-sm uppercase tracking-widest flex items-center gap-2">
          <span className="material-symbols-outlined animate-spin">refresh</span>
          Calculating Route...
        </span>
        <button onClick={onClear} className="text-on-surface hover:text-error transition-colors">
          <span className="material-symbols-outlined">close</span>
        </button>
      </div>
    )
  }

  if (error) {
    return (
      <div className="fixed top-20 left-1/2 -translate-x-1/2 z-40 bg-error-container text-on-error-container border-[3px] border-black px-4 py-3 shadow-hard w-[90%] max-w-sm flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="font-headline text-sm uppercase tracking-widest flex items-center gap-2">
            <span className="material-symbols-outlined">error</span>
            Route Failed
          </span>
          <button onClick={onClear} className="hover:opacity-75 transition-opacity">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>
        <p className="font-body text-xs">{error}</p>
      </div>
    )
  }

  if (!route) return null

  return (
    <div className="fixed top-20 left-1/2 -translate-x-1/2 z-40 bg-surface-container border-[3px] border-black shadow-hard w-[90%] max-w-sm flex flex-col">
      <div className="bg-primary/10 border-b-[3px] border-black px-4 py-3 flex items-start justify-between">
        <div className="flex flex-col gap-1">
          <h3 className="font-headline text-lg uppercase tracking-wider flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">route</span>
            Safe Route
          </h3>
          <div className="font-mono text-xs flex items-center gap-3 text-on-surface/80">
            <span>{route.distance_km} km</span>
            {route.avoided_events > 0 && (
              <span className="text-warning font-bold flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">shield</span>
                Avoided {route.avoided_events} threats
              </span>
            )}
          </div>
        </div>
        <button onClick={onClear} className="text-on-surface hover:text-error transition-colors p-1">
          <span className="material-symbols-outlined">close</span>
        </button>
      </div>
      
      <div className="p-3 bg-surface">
        <button
          onClick={onOpenMaps}
          className="w-full bg-primary text-on-primary font-headline uppercase tracking-widest py-3 border-[3px] border-black shadow-hard active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-none flex items-center justify-center gap-2"
        >
          <span className="material-symbols-outlined">map</span>
          Open in Google Maps
        </button>
      </div>
    </div>
  )
}
