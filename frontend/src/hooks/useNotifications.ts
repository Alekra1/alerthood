import { useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Notification } from '../types'

export function useNotifications(userId: string | null) {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const userIdRef = useRef<string | null>(null)

  useEffect(() => {
    if (!userId) return
    let channel: ReturnType<typeof supabase.channel> | null = null

    async function init() {
      userIdRef.current = userId

      const { data } = await supabase
        .from('notifications')
        .select('*')
        .eq('user_id', userId)
        .eq('is_read', false)
        .order('created_at', { ascending: false })

      if (data) setNotifications(data.map(toNotification))

      channel = supabase
        .channel('notifications-' + userId)
        .on(
          'postgres_changes',
          { event: '*', schema: 'public', table: 'notifications', filter: `user_id=eq.${userId}` },
          (payload) => {
            if (payload.eventType === 'INSERT') {
              setNotifications((prev) => [toNotification(payload.new), ...prev])
            } else if (payload.eventType === 'UPDATE') {
              if (payload.new.is_read) {
                setNotifications((prev) => prev.filter((n) => n.id !== payload.new.id))
              } else {
                setNotifications((prev) =>
                  prev.map((n) => (n.id === payload.new.id ? toNotification(payload.new) : n)),
                )
              }
            }
          },
        )
        .subscribe()
    }

    init()
    return () => { channel?.unsubscribe() }
  }, [userId])

  async function markAsRead(id: string) {
    await supabase.from('notifications').update({ is_read: true }).eq('id', id)
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, isRead: true } : n)))
  }

  async function markAllAsRead() {
    if (!userIdRef.current) return
    await supabase.from('notifications').update({ is_read: true }).eq('user_id', userIdRef.current).eq('is_read', false)
    setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })))
  }

  const unreadCount = notifications.filter((n) => !n.isRead).length

  return { notifications, unreadCount, markAsRead, markAllAsRead }
}

function toNotification(row: any): Notification {
  return {
    id: row.id,
    userId: row.user_id,
    eventId: row.event_id ?? null,
    title: row.title,
    body: row.body ?? null,
    isRead: row.is_read,
    createdAt: row.created_at,
  }
}
