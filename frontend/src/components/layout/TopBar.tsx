import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useNotifications } from '../../hooks/useNotifications'
import { NotificationPanel } from './NotificationPanel'

export function TopBar() {
  const { user, profile } = useAuth()
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications(user?.id ?? null)
  const [isOpen, setIsOpen] = useState(false)

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

      <div className="relative flex items-center gap-2">
        {user && (
          <button
            onClick={() => setIsOpen((o) => !o)}
            className="relative p-2 hover:bg-surface-container-high active:translate-x-[2px] active:translate-y-[2px] transition-none"
            aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
          >
            <span className="material-symbols-outlined text-on-surface">notifications</span>
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-primary-container border border-black rounded-full flex items-center justify-center text-[8px] font-black text-on-primary-container">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>
        )}

        {isOpen && user && (
          <NotificationPanel
            notifications={notifications}
            onMarkAsRead={markAsRead}
            onMarkAllAsRead={markAllAsRead}
            onClose={() => setIsOpen(false)}
          />
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
