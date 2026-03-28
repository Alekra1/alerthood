interface TopBarProps {
  notificationCount?: number
}

export function TopBar({ notificationCount = 0 }: TopBarProps) {
  return (
    <nav className="fixed top-0 w-full z-50 flex justify-between items-center px-6 h-16 bg-background border-b-2 border-black shadow-hard">
      <div className="flex items-center gap-3">
        <span
          className="material-symbols-outlined text-primary-container"
          style={{ fontVariationSettings: "'FILL' 1" }}
        >
          security
        </span>
        <span className="font-headline font-black text-2xl uppercase tracking-tighter italic text-primary-container">
          ALERTHOOD
        </span>
      </div>
      <div className="flex items-center gap-2">
        <button
          className="relative p-2 hover:bg-surface-container-high active:translate-x-[2px] active:translate-y-[2px] transition-none"
          aria-label={`Notifications${notificationCount > 0 ? `, ${notificationCount} unread` : ''}`}
        >
          <span className="material-symbols-outlined text-on-surface">notifications</span>
          {notificationCount > 0 && (
            <span className="absolute top-1 right-1 w-4 h-4 bg-primary-container border border-black rounded-full flex items-center justify-center text-[8px] font-black text-on-primary-container">
              {notificationCount}
            </span>
          )}
        </button>
      </div>
    </nav>
  )
}
