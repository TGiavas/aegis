/**
 * Alerts Page
 * 
 * Lists all alerts with ability to resolve them.
 */
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Project, Alert } from '../api/client'
import { Bell, CheckCircle } from 'lucide-react'

// Level badge colors
const levelColors: Record<string, string> = {
  LOW: 'bg-blue-500/20 text-blue-400',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400',
  HIGH: 'bg-orange-500/20 text-orange-400',
  CRITICAL: 'bg-red-600/30 text-red-300',
}

export function AlertsPage() {
  // State
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<number>(0)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showResolved, setShowResolved] = useState(false)

  // Fetch projects on mount
  useEffect(() => {
    async function fetchProjects() {
      try {
        const response = await api.getProjects()
        setProjects(response.items)
        if (response.items.length > 0) {
          setSelectedProjectId(response.items[0].id)
        }
      } catch (err) {
        console.error('Failed to fetch projects:', err)
      } finally {
        setIsLoading(false)
      }
    }
    fetchProjects()
  }, [])

  // Fetch alerts when project or filter changes
  useEffect(() => {
    if (!selectedProjectId) return

    const projectId = selectedProjectId  // Capture for closure

    async function fetchAlerts() {
      try {
        const response = await api.getAlerts(projectId, {
          size: 100,
          resolved: showResolved ? undefined : false,
        })
        setAlerts(response.items)
      } catch (err) {
        console.error('Failed to fetch alerts:', err)
      }
    }
    fetchAlerts()
  }, [selectedProjectId, showResolved])

  // Resolve an alert
  async function handleResolve(alertId: number) {
    if (!selectedProjectId) return

    try {
      await api.resolveAlert(selectedProjectId, alertId)
      // Update local state
      setAlerts(prev => prev.map(a => 
        a.id === alertId 
          ? { ...a, resolved_at: new Date().toISOString() }
          : a
      ))
    } catch (err) {
      console.error('Failed to resolve alert:', err)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-[var(--color-text-secondary)]">Loading...</p>
      </div>
    )
  }

  if (projects.length === 0) {
    return (
      <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-6 text-center">
        <Bell className="w-12 h-12 text-[var(--color-text-muted)] mx-auto mb-4" />
        <p className="text-[var(--color-text-secondary)]">No projects yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <label className="text-[var(--color-text-secondary)]">Project:</label>
          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(Number(e.target.value))}
            className="px-3 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-cyan)]"
          >
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showResolved}
            onChange={(e) => setShowResolved(e.target.checked)}
            className="w-4 h-4 rounded border-[var(--color-border)] bg-[var(--color-bg-tertiary)] text-[var(--color-accent-cyan)] focus:ring-[var(--color-accent-cyan)]"
          />
          <span className="text-[var(--color-text-secondary)]">Show resolved</span>
        </label>
      </div>

      {/* Alerts List */}
      <div className="space-y-3">
        {alerts.length === 0 ? (
          <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-8 text-center">
            <CheckCircle className="w-12 h-12 text-[var(--color-accent-green)] mx-auto mb-4" />
            <p className="text-[var(--color-text-primary)] font-medium">All clear!</p>
            <p className="text-[var(--color-text-muted)] mt-1">No open alerts</p>
          </div>
        ) : (
          alerts.map(alert => (
            <div
              key={alert.id}
              className={`bg-[var(--color-bg-secondary)] border rounded-lg p-4 ${
                alert.resolved_at 
                  ? 'border-[var(--color-border)] opacity-60' 
                  : 'border-[var(--color-severity-error)]/30'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs px-2 py-1 rounded ${levelColors[alert.level] || ''}`}>
                      {alert.level}
                    </span>
                    <span className="text-sm text-[var(--color-text-muted)]">
                      {alert.rule_name}
                    </span>
                    {alert.resolved_at && (
                      <span className="text-xs px-2 py-1 rounded bg-[var(--color-accent-green)]/10 text-[var(--color-accent-green)]">
                        Resolved
                      </span>
                    )}
                  </div>
                  <p className="text-[var(--color-text-primary)]">{alert.message}</p>
                  <p className="text-sm text-[var(--color-text-muted)] mt-2">
                    {new Date(alert.created_at).toLocaleString()}
                    {alert.resolved_at && (
                      <> • Resolved {new Date(alert.resolved_at).toLocaleString()}</>
                    )}
                  </p>
                </div>
                
                {!alert.resolved_at && (
                  <button
                    onClick={() => handleResolve(alert.id)}
                    className="px-3 py-2 bg-[var(--color-accent-green)]/10 hover:bg-[var(--color-accent-green)]/20 text-[var(--color-accent-green)] rounded-lg transition-colors text-sm"
                  >
                    Resolve
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

