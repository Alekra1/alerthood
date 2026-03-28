import { useState, FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function AuthPage() {
  const { user, loading, signIn, signUp } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (!loading && user) return <Navigate to="/map" replace />

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    const err = mode === 'login'
      ? await signIn(email, password)
      : await signUp(email, password, username, displayName)

    setSubmitting(false)

    if (err) {
      setError(err)
    } else {
      navigate('/map', { replace: true })
    }
  }

  return (
    <div className="min-h-dvh bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="flex items-center gap-3 mb-10">
          <span
            className="material-symbols-outlined text-primary-container text-4xl"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            security
          </span>
          <span className="font-headline font-black text-3xl uppercase tracking-tighter italic text-primary-container">
            ALERTHOOD
          </span>
        </div>

        {/* Card */}
        <div className="border-2 border-black bg-surface-container shadow-hard p-6">
          {/* Mode toggle */}
          <div className="flex border-2 border-black mb-6">
            <button
              type="button"
              onClick={() => { setMode('login'); setError(null) }}
              className={`flex-1 py-2 font-headline font-bold uppercase text-sm tracking-widest transition-none ${
                mode === 'login'
                  ? 'bg-primary-container text-on-primary-container'
                  : 'bg-transparent text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              Log In
            </button>
            <button
              type="button"
              onClick={() => { setMode('signup'); setError(null) }}
              className={`flex-1 py-2 font-headline font-bold uppercase text-sm tracking-widest transition-none border-l-2 border-black ${
                mode === 'signup'
                  ? 'bg-primary-container text-on-primary-container'
                  : 'bg-transparent text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              Sign Up
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'signup' && (
              <>
                <div>
                  <label className="block font-headline font-bold uppercase text-xs tracking-widest mb-1 text-on-surface-variant">
                    Username
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    required
                    placeholder="neighborhood_watch"
                    className="w-full bg-surface-container-high border-2 border-black px-3 py-2 font-body text-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:border-primary-container"
                  />
                </div>
                <div>
                  <label className="block font-headline font-bold uppercase text-xs tracking-widest mb-1 text-on-surface-variant">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={displayName}
                    onChange={e => setDisplayName(e.target.value)}
                    placeholder="Alex R."
                    className="w-full bg-surface-container-high border-2 border-black px-3 py-2 font-body text-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:border-primary-container"
                  />
                </div>
              </>
            )}

            <div>
              <label className="block font-headline font-bold uppercase text-xs tracking-widest mb-1 text-on-surface-variant">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
                className="w-full bg-surface-container-high border-2 border-black px-3 py-2 font-body text-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:border-primary-container"
              />
            </div>

            <div>
              <label className="block font-headline font-bold uppercase text-xs tracking-widest mb-1 text-on-surface-variant">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                minLength={6}
                placeholder="••••••••"
                className="w-full bg-surface-container-high border-2 border-black px-3 py-2 font-body text-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:border-primary-container"
              />
            </div>

            {error && (
              <p className="text-error text-sm font-body border-l-2 border-error pl-3">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3 bg-primary-container text-on-primary-container border-2 border-black font-headline font-bold uppercase tracking-widest shadow-hard active:translate-x-[2px] active:translate-y-[2px] active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed transition-none"
            >
              {submitting ? 'Please wait…' : mode === 'login' ? 'Log In' : 'Create Account'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
