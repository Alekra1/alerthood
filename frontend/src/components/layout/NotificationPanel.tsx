import { useEffect, useRef, useState } from 'react'
import type { Notification } from '../../types'

interface NotificationPanelProps {
  notifications: Notification[]
  onMarkAsRead: (id: string) => void
  onMarkAllAsRead: () => void
  onClose: () => void
}

const SWIPE_THRESHOLD = 72

function SwipeableItem({
  notification,
  onDismiss,
}: {
  notification: Notification
  onDismiss: () => void
}) {
  const itemRef = useRef<HTMLLIElement>(null)
  const startXRef = useRef(0)
  const deltaRef = useRef(0)
  const [gone, setGone] = useState(false)

  function onTouchStart(e: React.TouchEvent) {
    startXRef.current = e.touches[0].clientX
    deltaRef.current = 0
    if (itemRef.current) itemRef.current.style.transition = ''
  }

  function onTouchMove(e: React.TouchEvent) {
    const delta = e.touches[0].clientX - startXRef.current
    deltaRef.current = delta
    if (itemRef.current) {
      itemRef.current.style.transform = `translateX(${delta}px)`
      itemRef.current.style.opacity = `${Math.max(0, 1 - Math.abs(delta) / 160)}`
    }
  }

  function onTouchEnd() {
    if (Math.abs(deltaRef.current) >= SWIPE_THRESHOLD) {
      const dir = deltaRef.current > 0 ? 1 : -1
      if (itemRef.current) {
        itemRef.current.style.transition = 'transform 0.2s ease, opacity 0.2s ease'
        itemRef.current.style.transform = `translateX(${dir * 360}px)`
        itemRef.current.style.opacity = '0'
      }
      setTimeout(() => {
        setGone(true)
        onDismiss()
      }, 200)
    } else {
      if (itemRef.current) {
        itemRef.current.style.transition = 'transform 0.2s ease, opacity 0.2s ease'
        itemRef.current.style.transform = 'translateX(0)'
        itemRef.current.style.opacity = '1'
      }
    }
  }

  if (gone) return null

  return (
    <li
      ref={itemRef}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      className={`flex gap-3 px-4 py-3 select-none ${!notification.isRead ? 'bg-surface-container-low' : ''}`}
      style={{ touchAction: 'pan-y' }}
    >
      <div className="pt-1 flex-shrink-0">
        <div className={`w-2 h-2 rounded-full border border-black ${!notification.isRead ? 'bg-primary-container' : 'bg-transparent'}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm leading-tight ${!notification.isRead ? 'font-black text-on-surface' : 'font-medium text-on-surface-variant'}`}>
          {notification.title}
        </p>
        {notification.body && (
          <p className="text-xs text-on-surface-variant mt-0.5 line-clamp-2">{notification.body}</p>
        )}
        <p className="text-[10px] text-on-surface-variant mt-1 font-label uppercase">
          {relativeTime(notification.createdAt)}
        </p>
      </div>
    </li>
  )
}

export function NotificationPanel({ notifications, onMarkAsRead, onMarkAllAsRead, onClose }: NotificationPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  const hasUnread = notifications.some((n) => !n.isRead)

  return (
    <div
      ref={panelRef}
      className="fixed right-0 top-16 w-80 bg-surface-container border-l-2 border-b-2 border-black shadow-hard z-50 flex flex-col"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b-2 border-black flex-shrink-0">
        <span className="font-headline font-black text-sm uppercase tracking-tight">Notifications</span>
        <div className="flex items-center gap-3">
          {hasUnread && (
            <button
              onClick={onMarkAllAsRead}
              className="text-[10px] font-black uppercase text-primary-container hover:underline"
            >
              Mark all read
            </button>
          )}
          <button onClick={onClose} className="opacity-50 hover:opacity-100 transition-none">
            <span className="material-symbols-outlined text-sm">close</span>
          </button>
        </div>
      </div>

      {notifications.length === 0 ? (
        <div className="py-8 flex items-center justify-center text-on-surface-variant text-sm font-label opacity-50">
          No notifications yet
        </div>
      ) : (
        <ul className="overflow-y-auto divide-y-2 divide-black max-h-[228px]">
          {notifications.map((n) => (
            <SwipeableItem key={n.id} notification={n} onDismiss={() => onMarkAsRead(n.id)} />
          ))}
        </ul>
      )}
    </div>
  )
}

function relativeTime(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}
