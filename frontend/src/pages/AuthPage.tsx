import { useState, FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function AuthPage() {
  const { user, loading, signIn, signUp, signInWithGoogle } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (!loading && user) return <Navigate to="/map" replace />

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    const form = new FormData(e.currentTarget)
    const emailVal = (form.get('email') as string).trim()
    const passwordVal = form.get('password') as string
    const usernameVal = (form.get('username') as string ?? '').trim()
    const displayNameVal = (form.get('displayName') as string ?? '').trim()

    if (mode === 'signup' && (!usernameVal || usernameVal.includes('@'))) {
      setError(!usernameVal ? 'Username is required.' : 'Username cannot be an email address.')
      setSubmitting(false)
      return
    }

    const err = mode === 'login'
      ? await signIn(emailVal, passwordVal)
      : await signUp(emailVal, passwordVal, usernameVal, displayNameVal)

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

          <form onSubmit={handleSubmit} className="space-y-4" autoComplete="off">
            {mode === 'signup' && (
              <>
                <div>
                  <label className="block font-headline font-bold uppercase text-xs tracking-widest mb-1 text-on-surface-variant">
                    Username
                  </label>
                  <input
                    type="text"
                    name="username"
                    required
                    autoComplete="off"
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
                    name="displayName"
                    autoComplete="off"
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
                name="email"
                required
                autoComplete="off"
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
                name="password"
                required
                minLength={6}
                autoComplete="off"
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

          {/* Divider */}
          <div className="flex items-center gap-3 my-4">
            <div className="flex-1 h-px bg-black/20" />
            <span className="font-body text-xs text-on-surface-variant uppercase tracking-widest">or</span>
            <div className="flex-1 h-px bg-black/20" />
          </div>

          {/* Google OAuth */}
          <button
            type="button"
            onClick={async () => {
              setError(null)
              const err = await signInWithGoogle()
              if (err) setError(err)
            }}
            className="w-full py-3 bg-surface-container-high text-on-surface border-2 border-black font-headline font-bold uppercase tracking-widest shadow-hard active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-none flex items-center justify-center gap-2"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
              <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z"/>
              <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z"/>
              <path fill="#FBBC05" d="M3.964 10.71c-.18-.54-.282-1.117-.282-1.71s.102-1.17.282-1.71V4.958H.957C.347 6.173 0 7.548 0 9s.348 2.827.957 4.042l3.007-2.332z"/>
              <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"/>
            </svg>
            Continue with Google
          </button>
        </div>
      </div>
    </div>
  )
}
