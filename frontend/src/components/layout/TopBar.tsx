import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export function TopBar() {
  const { user, profile } = useAuth()

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
        {user && (
          <button
            className="relative p-2 hover:bg-surface-container-high active:translate-x-[2px] active:translate-y-[2px] transition-none"
            aria-label="Notifications"
          >
            <span className="material-symbols-outlined text-on-surface">notifications</span>
          </button>
        )}

        {user ? (
          <Link
            to="/profile"
            className="w-9 h-9 rounded-full border-2 border-black bg-surface-container flex items-center justify-center hover:bg-surface-container-high active:translate-x-[2px] active:translate-y-[2px] transition-none overflow-hidden"
            aria-label="Profile"
          >
            {profile?.avatar_url ? (
              <img src={profile.avatar_url} alt="avatar" className="w-full h-full object-cover" />
            ) : (
              <span
                className="material-symbols-outlined text-2xl text-primary-container"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                account_circle
              </span>
            )}
          </Link>
        ) : (
          <Link
            to="/auth"
            className="px-4 py-1.5 border-2 border-black bg-primary-container text-white font-headline font-bold uppercase text-xs tracking-widest shadow-hard-sm hover:opacity-90 active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-none"
          >
            Log In
          </Link>
        )}
      </div>
    </nav>
  )
}
