/**
 * Events Page
 * 
 * Lists all events for the selected project with filtering.
 */
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Project, Event } from '../api/client'
import { Activity, Filter } from 'lucide-react'

// Severity badge colors
const severityColors: Record<string, string> = {
  DEBUG: 'bg-gray-500/20 text-gray-400',
  INFO: 'bg-blue-500/20 text-blue-400',
  WARN: 'bg-yellow-500/20 text-yellow-400',
  ERROR: 'bg-red-500/20 text-red-400',
  CRITICAL: 'bg-red-600/30 text-red-300',
}

export function EventsPage() {
  // State
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  const [events, setEvents] = useState<Event[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [severityFilter, setSeverityFilter] = useState<string>('')

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

  // Fetch events when project or filter changes
  useEffect(() => {
    if (!selectedProjectId) return

    const projectId = selectedProjectId  // Capture for closure

    async function fetchEvents() {
      try {
        const response = await api.getEvents(projectId, {
          size: 100,
          severity: severityFilter || undefined,
        })
        setEvents(response.items)
      } catch (err) {
        console.error('Failed to fetch events:', err)
      }
    }
    fetchEvents()
  }, [selectedProjectId, severityFilter])

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
        <Activity className="w-12 h-12 text-[var(--color-text-muted)] mx-auto mb-4" />
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
            value={selectedProjectId || ''}
            onChange={(e) => setSelectedProjectId(Number(e.target.value))}
            className="px-3 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-cyan)]"
          >
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-[var(--color-text-muted)]" />
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-cyan)]"
          >
            <option value="">All Severities</option>
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARN">WARN</option>
            <option value="ERROR">ERROR</option>
            <option value="CRITICAL">CRITICAL</option>
          </select>
        </div>
      </div>

      {/* Events Table */}
      <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-[var(--color-bg-tertiary)]">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-[var(--color-text-secondary)]">Time</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-[var(--color-text-secondary)]">Source</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-[var(--color-text-secondary)]">Type</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-[var(--color-text-secondary)]">Severity</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-[var(--color-text-secondary)]">Latency</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {events.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-[var(--color-text-muted)]">
                  No events found
                </td>
              </tr>
            ) : (
              events.map(event => (
                <tr key={event.id} className="hover:bg-[var(--color-bg-hover)]">
                  <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">
                    {new Date(event.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-sm text-[var(--color-text-primary)]">
                    {event.source}
                  </td>
                  <td className="px-4 py-3 text-sm text-[var(--color-text-primary)]">
                    {event.event_type}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-1 rounded ${severityColors[event.severity] || ''}`}>
                      {event.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">
                    {event.latency_ms !== null ? `${event.latency_ms}ms` : '-'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

