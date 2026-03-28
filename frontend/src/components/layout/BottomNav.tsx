import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/map', label: 'MAP', icon: 'map' },
  { to: '/feed', label: 'FEED', icon: 'dynamic_feed' },
  { to: '/profile', label: 'PROFILE', icon: 'person' },
] as const

export function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 w-full z-50 flex justify-around items-center h-20 bg-background border-t-2 border-black">
      {NAV_ITEMS.map(({ to, label, icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            [
              'flex flex-col items-center justify-center py-2 px-4 w-1/3 h-full transition-none active:scale-95',
              isActive
                ? 'text-primary-container bg-surface-container border-t-4 border-primary-container'
                : 'text-gray-500 hover:text-on-surface',
            ].join(' ')
          }
        >
          {({ isActive }) => (
            <>
              <span
                className="material-symbols-outlined mb-1"
                style={{ fontVariationSettings: isActive ? "'FILL' 1" : "'FILL' 0" }}
              >
                {icon}
              </span>
              <span className="font-headline font-bold text-[10px] tracking-widest">{label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}
