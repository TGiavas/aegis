/**
 * Login Page
 * 
 * A simple login form that:
 * 1. Takes email and password
 * 2. Calls the API to authenticate
 * 3. Stores the token and redirects on success
 * 4. Shows error message on failure
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function LoginPage() {
  // Form state
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  
  // UI state
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  // Hooks
  const navigate = useNavigate()
  const { login } = useAuth()

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()  // Prevent page reload
    setError('')        // Clear previous errors
    setIsLoading(true)  // Show loading state

    try {
      await login(email, password)
      navigate('/dashboard')  // Redirect on success
    } catch (err) {
      // Show error message
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)] flex items-center justify-center p-4">
      {/* Login Card */}
      <div className="w-full max-w-md">
        {/* Logo & Title */}
        <div className="text-center mb-8">
          <img 
            src="/aegis.svg" 
            alt="Aegis" 
            className="w-16 h-16 mx-auto mb-4"
          />
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            Welcome to <span className="text-[var(--color-accent-cyan)]">Aegis</span>
          </h1>
          <p className="text-[var(--color-text-secondary)] mt-2">
            Sign in to your account
          </p>
        </div>

        {/* Form */}
        <form 
          onSubmit={handleSubmit}
          className="bg-[var(--color-bg-secondary)] rounded-lg p-6 border border-[var(--color-border)]"
        >
          {/* Error Message */}
          {error && (
            <div className="mb-4 p-3 bg-[var(--color-severity-error)]/10 border border-[var(--color-severity-error)]/30 rounded text-[var(--color-severity-error)] text-sm">
              {error}
            </div>
          )}

          {/* Email Field */}
          <div className="mb-4">
            <label 
              htmlFor="email"
              className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
              className="w-full px-4 py-3 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent-cyan)] transition-colors"
            />
          </div>

          {/* Password Field */}
          <div className="mb-6">
            <label 
              htmlFor="password"
              className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              className="w-full px-4 py-3 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent-cyan)] transition-colors"
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 bg-[var(--color-accent-cyan)] hover:bg-[var(--color-accent-cyan)]/90 disabled:opacity-50 disabled:cursor-not-allowed text-[var(--color-bg-primary)] font-semibold rounded-lg transition-colors"
          >
            {isLoading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        {/* Footer */}
        <p className="text-center text-[var(--color-text-muted)] text-sm mt-6">
          Don't have an account? Contact your administrator.
        </p>
      </div>
    </div>
  )
}

