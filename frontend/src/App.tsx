import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { TopBar } from './components/layout/TopBar'
import { BottomNav } from './components/layout/BottomNav'
import { MapPage } from './pages/MapPage'
import { FeedPage } from './pages/FeedPage'
import { ProfilePage } from './pages/ProfilePage'
import { AuthPage } from './pages/AuthPage'

function AppShell() {
  return (
    <div className="min-h-dvh bg-background text-on-background font-body">
      <TopBar />
      <Routes>
        <Route path="/" element={<Navigate to="/map" replace />} />
        <Route path="/map" element={<ProtectedRoute><MapPage /></ProtectedRoute>} />
        <Route path="/feed" element={<ProtectedRoute><FeedPage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="/auth" element={<AuthPage />} />
      </Routes>
      <BottomNav />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    </BrowserRouter>
  )
}
