/**
 * Events Page
 * 
 * Lists all events with pagination and real-time streaming via SSE.
 */
import { useEffect, useState, useRef } from 'react'
import { api } from '../api/client'
import type { Project, Event } from '../api/client'
import { Activity, Filter, ChevronLeft, ChevronRight, Radio, WifiOff } from 'lucide-react'

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

  // Pagination state
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [total, setTotal] = useState(0)

  // SSE state - auto-enabled, tracks connection status
  const [isConnected, setIsConnected] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  // Calculate pagination info
  const totalPages = Math.ceil(total / pageSize)
  const hasNextPage = page < totalPages
  const hasPrevPage = page > 1

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

  // Fetch events when project, filter, or page changes
  useEffect(() => {
    if (!selectedProjectId) return

    const projectId = selectedProjectId

    async function fetchEvents() {
      try {
        const response = await api.getEvents(projectId, {
          page,
          size: pageSize,
          severity: severityFilter || undefined,
        })
        setEvents(response.items)
        setTotal(response.total)
      } catch (err) {
        console.error('Failed to fetch events:', err)
      }
    }
    fetchEvents()
  }, [selectedProjectId, severityFilter, page, pageSize])

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1)
  }, [selectedProjectId, severityFilter])

  // SSE connection for real-time updates - auto-enabled
  useEffect(() => {
    if (!selectedProjectId) {
      // Close existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
        setIsConnected(false)
      }
      return
    }

    const token = localStorage.getItem('aegis_token')
    if (!token) return

    // Connect to SSE endpoint
    const url = `/api/v1/projects/${selectedProjectId}/events/stream?token=${encodeURIComponent(token)}`
    const eventSource = new EventSource(url)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      setIsConnected(true)
    }

    eventSource.onmessage = (e) => {
      try {
        const newEvent: Event = JSON.parse(e.data)
        // Add new event to the top of the list (only on page 1)
        if (page === 1) {
          setEvents(prev => {
            // Check severity filter
            if (severityFilter && newEvent.severity !== severityFilter) {
              return prev
            }
            // Add to top, remove last to maintain page size
            const updated = [newEvent, ...prev]
            if (updated.length > pageSize) {
              updated.pop()
            }
            return updated
          })
          setTotal(prev => prev + 1)
        }
      } catch (err) {
        console.error('Failed to parse SSE event:', err)
      }
    }

    eventSource.onerror = () => {
      console.error('SSE connection error')
      setIsConnected(false)
    }

    return () => {
      eventSource.close()
      setIsConnected(false)
    }
  }, [selectedProjectId, page, severityFilter, pageSize])

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
      <div className="flex items-center justify-between flex-wrap gap-4">
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

        {/* Live streaming status indicator */}
        <div
          className={`flex items-center gap-2 px-4 py-2 rounded-lg ${isConnected
            ? 'bg-[var(--color-accent-green)]/20 text-[var(--color-accent-green)] border border-[var(--color-accent-green)]/30'
            : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)] border border-[var(--color-border)]'
            }`}
        >
          {isConnected ? (
            <>
              <Radio className="w-4 h-4 animate-pulse" />
              <span>Live</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4" />
              <span>Connecting...</span>
            </>
          )}
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

      {/* Pagination Controls */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-[var(--color-text-muted)]">
          Showing {events.length > 0 ? (page - 1) * pageSize + 1 : 0} - {Math.min(page * pageSize, total)} of {total} events
        </p>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={!hasPrevPage}
            className="p-2 rounded-lg bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <span className="px-4 py-2 text-sm text-[var(--color-text-primary)]">
            Page {page} of {totalPages || 1}
          </span>

          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={!hasNextPage}
            className="p-2 rounded-lg bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
