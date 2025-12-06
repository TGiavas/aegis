/**
 * ProtectedRoute component
 * 
 * Wraps routes that require authentication.
 * If not authenticated, redirects to login page.
 */
import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()

  // Show nothing while checking auth status
  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--color-bg-primary)] flex items-center justify-center">
        <p className="text-[var(--color-text-secondary)]">Loading...</p>
      </div>
    )
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // Render child routes
  return <Outlet />
}

