/**
 * Projects Page
 * 
 * Create, view, and manage projects and their API keys.
 */
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Project, ApiKey, ApiKeyCreate } from '../api/client'
import { FolderOpen, Plus, Key, Trash2, Copy, Eye, EyeOff } from 'lucide-react'

export function ProjectsPage() {
  // State
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)
  
  // Create project modal
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDesc, setNewProjectDesc] = useState('')
  
  // API Keys
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([])
  const [newKeyName, setNewKeyName] = useState('')
  const [createdKey, setCreatedKey] = useState<ApiKeyCreate | null>(null)
  const [showKey, setShowKey] = useState(false)

  // Fetch projects on mount
  useEffect(() => {
    fetchProjects()
  }, [])

  async function fetchProjects() {
    try {
      const response = await api.getProjects()
      setProjects(response.items)
    } catch (err) {
      console.error('Failed to fetch projects:', err)
    } finally {
      setIsLoading(false)
    }
  }

  // Fetch API keys when project selected
  useEffect(() => {
    if (!selectedProject) {
      setApiKeys([])
      return
    }
    
    async function fetchKeys() {
      try {
        const response = await api.getApiKeys(selectedProject!.id)
        setApiKeys(response.items)
      } catch (err) {
        console.error('Failed to fetch API keys:', err)
      }
    }
    fetchKeys()
  }, [selectedProject])

  // Create project
  async function handleCreateProject(e: React.FormEvent) {
    e.preventDefault()
    try {
      const project = await api.createProject(newProjectName, newProjectDesc || undefined)
      setProjects(prev => [project, ...prev])
      setShowCreateModal(false)
      setNewProjectName('')
      setNewProjectDesc('')
    } catch (err) {
      console.error('Failed to create project:', err)
    }
  }

  // Delete project
  async function handleDeleteProject(id: number) {
    if (!confirm('Are you sure you want to delete this project?')) return
    
    try {
      await api.deleteProject(id)
      setProjects(prev => prev.filter(p => p.id !== id))
      if (selectedProject?.id === id) {
        setSelectedProject(null)
      }
    } catch (err) {
      console.error('Failed to delete project:', err)
    }
  }

  // Create API key
  async function handleCreateKey(e: React.FormEvent) {
    e.preventDefault()
    if (!selectedProject) return
    
    try {
      const key = await api.createApiKey(selectedProject.id, newKeyName)
      setCreatedKey(key)
      setNewKeyName('')
      // Refresh keys list
      const response = await api.getApiKeys(selectedProject.id)
      setApiKeys(response.items)
    } catch (err) {
      console.error('Failed to create API key:', err)
    }
  }

  // Revoke API key
  async function handleRevokeKey(keyId: number) {
    if (!selectedProject) return
    if (!confirm('Are you sure you want to revoke this API key?')) return
    
    try {
      await api.revokeApiKey(selectedProject.id, keyId)
      setApiKeys(prev => prev.map(k => 
        k.id === keyId 
          ? { ...k, revoked_at: new Date().toISOString(), is_active: false }
          : k
      ))
    } catch (err) {
      console.error('Failed to revoke API key:', err)
    }
  }

  // Copy to clipboard
  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-[var(--color-text-secondary)]">Loading...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium text-[var(--color-text-primary)]">
          Your Projects ({projects.length})
        </h2>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-[var(--color-accent-cyan)] hover:bg-[var(--color-accent-cyan)]/90 text-[var(--color-bg-primary)] rounded-lg transition-colors font-medium"
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      {/* Projects Grid */}
      {projects.length === 0 ? (
        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-8 text-center">
          <FolderOpen className="w-12 h-12 text-[var(--color-text-muted)] mx-auto mb-4" />
          <p className="text-[var(--color-text-primary)] font-medium">No projects yet</p>
          <p className="text-[var(--color-text-muted)] mt-1">Create your first project to get started</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map(project => (
            <div
              key={project.id}
              className={`bg-[var(--color-bg-secondary)] border rounded-lg p-4 cursor-pointer transition-colors ${
                selectedProject?.id === project.id
                  ? 'border-[var(--color-accent-cyan)]'
                  : 'border-[var(--color-border)] hover:border-[var(--color-text-muted)]'
              }`}
              onClick={() => setSelectedProject(project)}
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-medium text-[var(--color-text-primary)]">{project.name}</h3>
                  <p className="text-sm text-[var(--color-text-muted)] mt-1">
                    {project.description || 'No description'}
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDeleteProject(project.id)
                  }}
                  className="p-2 text-[var(--color-text-muted)] hover:text-[var(--color-severity-error)] transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <p className="text-xs text-[var(--color-text-muted)] mt-3">
                Created {new Date(project.created_at).toLocaleDateString()}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* API Keys Section */}
      {selectedProject && (
        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg">
          <div className="p-4 border-b border-[var(--color-border)]">
            <h3 className="font-medium text-[var(--color-text-primary)] flex items-center gap-2">
              <Key className="w-4 h-4" />
              API Keys for {selectedProject.name}
            </h3>
          </div>
          
          <div className="p-4 space-y-4">
            {/* Create Key Form */}
            <form onSubmit={handleCreateKey} className="flex gap-2">
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="Key name (e.g., Production)"
                required
                className="flex-1 px-3 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent-cyan)]"
              />
              <button
                type="submit"
                className="px-4 py-2 bg-[var(--color-accent-cyan)] hover:bg-[var(--color-accent-cyan)]/90 text-[var(--color-bg-primary)] rounded-lg transition-colors font-medium"
              >
                Create Key
              </button>
            </form>

            {/* Newly Created Key */}
            {createdKey && (
              <div className="p-4 bg-[var(--color-accent-green)]/10 border border-[var(--color-accent-green)]/30 rounded-lg">
                <p className="text-sm text-[var(--color-accent-green)] font-medium mb-2">
                  API Key Created! Copy it now - you won't see it again.
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 p-2 bg-[var(--color-bg-tertiary)] rounded text-sm font-mono text-[var(--color-text-primary)]">
                    {showKey ? createdKey.key : '•'.repeat(40)}
                  </code>
                  <button
                    onClick={() => setShowKey(!showKey)}
                    className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                  >
                    {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => copyToClipboard(createdKey.key)}
                    className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-accent-cyan)]"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* Keys List */}
            <div className="space-y-2">
              {apiKeys.length === 0 ? (
                <p className="text-[var(--color-text-muted)] text-sm">No API keys yet</p>
              ) : (
                apiKeys.map(key => (
                  <div
                    key={key.id}
                    className={`flex items-center justify-between p-3 bg-[var(--color-bg-tertiary)] rounded-lg ${
                      !key.is_active ? 'opacity-50' : ''
                    }`}
                  >
                    <div>
                      <p className="text-[var(--color-text-primary)]">{key.name}</p>
                      <p className="text-sm text-[var(--color-text-muted)]">
                        {key.key_prefix}... • Created {new Date(key.created_at).toLocaleDateString()}
                        {key.revoked_at && ' • Revoked'}
                      </p>
                    </div>
                    {key.is_active && (
                      <button
                        onClick={() => handleRevokeKey(key.id)}
                        className="px-3 py-1 text-sm text-[var(--color-severity-error)] hover:bg-[var(--color-severity-error)]/10 rounded transition-colors"
                      >
                        Revoke
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-6 w-full max-w-md">
            <h2 className="text-lg font-medium text-[var(--color-text-primary)] mb-4">
              Create New Project
            </h2>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-sm text-[var(--color-text-secondary)] mb-1">
                  Project Name
                </label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  required
                  placeholder="My Project"
                  className="w-full px-3 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent-cyan)]"
                />
              </div>
              <div>
                <label className="block text-sm text-[var(--color-text-secondary)] mb-1">
                  Description (optional)
                </label>
                <textarea
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  placeholder="What is this project for?"
                  rows={3}
                  className="w-full px-3 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent-cyan)] resize-none"
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[var(--color-accent-cyan)] hover:bg-[var(--color-accent-cyan)]/90 text-[var(--color-bg-primary)] rounded-lg transition-colors font-medium"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

