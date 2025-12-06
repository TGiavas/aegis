/**
 * Dashboard Page
 * 
 * Shows overview stats and recent activity.
 */
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Project, Event, Alert } from '../api/client'
import { Activity, Bell, FolderOpen, AlertTriangle } from 'lucide-react'

// Stat card component
function StatCard({ 
  label, 
  value, 
  icon: Icon, 
  color 
}: { 
  label: string
  value: number | string
  icon: React.ElementType
  color: string 
}) {
  return (
    <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[var(--color-text-muted)] text-sm">{label}</p>
          <p className="text-3xl font-bold text-[var(--color-text-primary)] mt-1">
            {value}
          </p>
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  )
}

export function DashboardPage() {
  // State
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [events, setEvents] = useState<Event[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  // Fetch projects on mount
  useEffect(() => {
    async function fetchProjects() {
      try {
        const response = await api.getProjects()
        setProjects(response.items)
        // Auto-select first project
        if (response.items.length > 0) {
          setSelectedProject(response.items[0])
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load projects')
      } finally {
        setIsLoading(false)
      }
    }
    fetchProjects()
  }, [])

  // Fetch events and alerts when project changes
  useEffect(() => {
    if (!selectedProject) return

    const projectId = selectedProject.id  // Capture for closure

    async function fetchData() {
      try {
        const [eventsRes, alertsRes] = await Promise.all([
          api.getEvents(projectId, { size: 100 }),
          api.getAlerts(projectId, { size: 100 }),
        ])
        setEvents(eventsRes.items)
        setAlerts(alertsRes.items)
      } catch (err) {
        console.error('Failed to fetch data:', err)
      }
    }
    fetchData()
  }, [selectedProject])

  // Calculate stats
  const openAlerts = alerts.filter(a => !a.resolved_at).length
  const errorEvents = events.filter(e => e.severity === 'ERROR' || e.severity === 'CRITICAL').length

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-[var(--color-text-secondary)]">Loading...</p>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="bg-[var(--color-severity-error)]/10 border border-[var(--color-severity-error)]/30 rounded-lg p-6">
        <p className="text-[var(--color-severity-error)]">{error}</p>
      </div>
    )
  }

  // No projects
  if (projects.length === 0) {
    return (
      <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-6 text-center">
        <FolderOpen className="w-12 h-12 text-[var(--color-text-muted)] mx-auto mb-4" />
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-2">
          No Projects Yet
        </h2>
        <p className="text-[var(--color-text-secondary)]">
          Create a project to start monitoring events.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Project Selector */}
      <div className="flex items-center gap-4">
        <label className="text-[var(--color-text-secondary)]">Project:</label>
        <select
          value={selectedProject?.id || ''}
          onChange={(e) => {
            const project = projects.find(p => p.id === Number(e.target.value))
            setSelectedProject(project || null)
          }}
          className="px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-cyan)]"
        >
          {projects.map(project => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Events"
          value={events.length}
          icon={Activity}
          color="bg-[var(--color-accent-cyan)]/10 text-[var(--color-accent-cyan)]"
        />
        <StatCard
          label="Open Alerts"
          value={openAlerts}
          icon={Bell}
          color={openAlerts > 0 
            ? "bg-[var(--color-severity-error)]/10 text-[var(--color-severity-error)]"
            : "bg-[var(--color-accent-green)]/10 text-[var(--color-accent-green)]"
          }
        />
        <StatCard
          label="Error Events"
          value={errorEvents}
          icon={AlertTriangle}
          color={errorEvents > 0
            ? "bg-[var(--color-severity-warn)]/10 text-[var(--color-severity-warn)]"
            : "bg-[var(--color-accent-green)]/10 text-[var(--color-accent-green)]"
          }
        />
        <StatCard
          label="Projects"
          value={projects.length}
          icon={FolderOpen}
          color="bg-[var(--color-accent-purple)]/10 text-[var(--color-accent-purple)]"
        />
      </div>

      {/* Recent Alerts */}
      <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg">
        <div className="p-4 border-b border-[var(--color-border)]">
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
            Recent Alerts
          </h2>
        </div>
        <div className="p-4">
          {alerts.length === 0 ? (
            <p className="text-[var(--color-text-muted)] text-center py-4">
              No alerts yet
            </p>
          ) : (
            <ul className="space-y-3">
              {alerts.slice(0, 5).map(alert => (
                <li 
                  key={alert.id}
                  className="flex items-center gap-3 p-3 bg-[var(--color-bg-tertiary)] rounded-lg"
                >
                  <span className={`w-2 h-2 rounded-full ${
                    alert.level === 'CRITICAL' ? 'bg-[var(--color-level-critical)]' :
                    alert.level === 'HIGH' ? 'bg-[var(--color-level-high)]' :
                    alert.level === 'MEDIUM' ? 'bg-[var(--color-level-medium)]' :
                    'bg-[var(--color-level-low)]'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-[var(--color-text-primary)] truncate">
                      {alert.message}
                    </p>
                    <p className="text-[var(--color-text-muted)] text-sm">
                      {alert.rule_name} • {new Date(alert.created_at).toLocaleString()}
                    </p>
                  </div>
                  {alert.resolved_at ? (
                    <span className="text-xs px-2 py-1 rounded bg-[var(--color-accent-green)]/10 text-[var(--color-accent-green)]">
                      Resolved
                    </span>
                  ) : (
                    <span className="text-xs px-2 py-1 rounded bg-[var(--color-severity-error)]/10 text-[var(--color-severity-error)]">
                      Open
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
