import { Navigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import type { ReactNode } from 'react'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-dvh bg-background flex items-center justify-center">
        <span className="material-symbols-outlined text-primary-container text-4xl animate-spin">
          progress_activity
        </span>
      </div>
    )
  }

  if (!user) return <Navigate to="/auth" replace />

  return <>{children}</>
}
