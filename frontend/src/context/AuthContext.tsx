import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import type { User, Session } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'

interface Profile {
  id: string
  email: string | null
  username: string
  display_name: string | null
  avatar_url: string | null
  karma: number
  trust_score: number
}

interface AuthContextValue {
  user: User | null
  session: Session | null
  profile: Profile | null
  loading: boolean
  signUp: (email: string, password: string, username: string, displayName: string) => Promise<string | null>
  signIn: (email: string, password: string) => Promise<string | null>
  signInWithGoogle: () => Promise<string | null>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)

  async function fetchProfile(userId: string) {
    const { data } = await supabase
      .from('profiles')
      .select('id, email, username, display_name, avatar_url, karma, trust_score')
      .eq('id', userId)
      .single()

    if (data) {
      setProfile(data)
      return
    }

    // No profile row yet — can happen for OAuth users whose trigger didn't fire.
    // Create one from auth metadata.
    const { data: { user: authUser } } = await supabase.auth.getUser()
    if (!authUser) { setProfile(null); return }

    const meta = authUser.user_metadata ?? {}
    const emailPart = authUser.email?.split('@')[0] ?? 'user'
    await supabase.from('profiles').upsert({
      id: userId,
      email: authUser.email ?? null,
      username: meta.username ?? emailPart,
      display_name: meta.display_name ?? meta.full_name ?? meta.name ?? emailPart,
      avatar_url: meta.avatar_url ?? null,
    })

    const { data: created } = await supabase
      .from('profiles')
      .select('id, email, username, display_name, avatar_url, karma, trust_score')
      .eq('id', userId)
      .single()
    setProfile(created ?? null)
  }

  useEffect(() => {
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      setSession(session)
      setUser(session?.user ?? null)
      if (session?.user) await fetchProfile(session.user.id)
      setLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      setUser(session?.user ?? null)
      if (session?.user) {
        fetchProfile(session.user.id)
      } else {
        setProfile(null)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  async function signUp(email: string, password: string, username: string, displayName: string): Promise<string | null> {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { username, display_name: displayName || null },
      },
    })
    if (error) {
      if (error.message.toLowerCase().includes('rate limit') || error.status === 429) {
        return 'Too many sign-up attempts. Please wait a few minutes and try again.'
      }
      return error.message
    }
    if (!data.user) return 'Sign up failed'

    // Profile is created by the handle_new_user trigger using the metadata above.
    // Small delay to let the trigger complete before fetching.
    await new Promise(r => setTimeout(r, 500))
    await fetchProfile(data.user.id)
    return null
  }

  async function signIn(email: string, password: string): Promise<string | null> {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    return error ? error.message : null
  }

  async function signInWithGoogle(): Promise<string | null> {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/map` },
    })
    return error ? error.message : null
  }

  async function signOut() {
    await supabase.auth.signOut()
  }

  return (
    <AuthContext.Provider value={{ user, session, profile, loading, signUp, signIn, signInWithGoogle, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
