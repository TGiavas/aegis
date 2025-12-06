/**
 * API client for communicating with the Aegis backend.
 */

const API_BASE = '/api/v1'

// =============================================================================
// TYPES
// =============================================================================

export interface User {
  id: number
  email: string
  role: string
  created_at: string
}

export interface Project {
  id: number
  name: string
  description: string | null
  owner_id: number
  created_at: string
}

export interface ApiKey {
  id: number
  project_id: number
  name: string
  key_prefix: string
  created_at: string
  revoked_at: string | null
  is_active: boolean
}

export interface ApiKeyCreate {
  id: number
  project_id: number
  name: string
  key: string
  key_prefix: string
  created_at: string
}

export interface Event {
  id: number
  project_id: number
  source: string
  event_type: string
  severity: string
  latency_ms: number | null
  payload: Record<string, unknown>
  created_at: string
}

export interface Alert {
  id: number
  project_id: number
  rule_name: string
  message: string
  level: string
  created_at: string
  resolved_at: string | null
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

// =============================================================================
// API CLIENT
// =============================================================================

class ApiClient {
  private token: string | null = null

  setToken(token: string | null) {
    this.token = token
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T
    }

    return response.json()
  }

  // Auth
  async login(email: string, password: string) {
    const response = await this.request<{ access_token: string; token_type: string }>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }
    )
    this.token = response.access_token
    return response
  }

  async register(email: string, password: string) {
    return this.request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  // Projects
  async getProjects(page = 1, size = 20) {
    return this.request<PaginatedResponse<Project>>(
      `/projects?page=${page}&size=${size}`
    )
  }

  async getProject(id: number) {
    return this.request<Project>(`/projects/${id}`)
  }

  async createProject(name: string, description?: string) {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    })
  }

  async deleteProject(id: number) {
    return this.request<void>(`/projects/${id}`, { method: 'DELETE' })
  }

  // API Keys
  async getApiKeys(projectId: number) {
    return this.request<{ items: ApiKey[]; total: number }>(
      `/projects/${projectId}/api-keys`
    )
  }

  async createApiKey(projectId: number, name: string) {
    return this.request<ApiKeyCreate>(`/projects/${projectId}/api-keys`, {
      method: 'POST',
      body: JSON.stringify({ name }),
    })
  }

  async revokeApiKey(projectId: number, keyId: number) {
    return this.request<void>(`/projects/${projectId}/api-keys/${keyId}`, {
      method: 'DELETE',
    })
  }

  // Events
  async getEvents(
    projectId: number,
    params: {
      page?: number
      size?: number
      severity?: string
      event_type?: string
    } = {}
  ) {
    const query = new URLSearchParams()
    query.set('page', String(params.page || 1))
    query.set('size', String(params.size || 50))
    if (params.severity) query.set('severity', params.severity)
    if (params.event_type) query.set('event_type', params.event_type)

    return this.request<PaginatedResponse<Event>>(
      `/projects/${projectId}/events?${query}`
    )
  }

  // Alerts
  async getAlerts(
    projectId: number,
    params: { page?: number; size?: number; resolved?: boolean } = {}
  ) {
    const query = new URLSearchParams()
    query.set('page', String(params.page || 1))
    query.set('size', String(params.size || 50))
    if (params.resolved !== undefined) query.set('resolved', String(params.resolved))

    return this.request<PaginatedResponse<Alert>>(
      `/projects/${projectId}/alerts?${query}`
    )
  }

  async resolveAlert(projectId: number, alertId: number) {
    return this.request<Alert>(`/projects/${projectId}/alerts/${alertId}/resolve`, {
      method: 'POST',
    })
  }
}

export const api = new ApiClient()

