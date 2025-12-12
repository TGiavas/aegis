/**
 * Rules Page
 * 
 * Manage alert rules - both global and project-specific.
 */
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Project, AlertRule, AlertRuleCreate, AlertRuleUpdate } from '../api/client'
import { Settings2, Plus, Pencil, Trash2, Power, PowerOff, Globe, FolderOpen } from 'lucide-react'

// Available operators
const OPERATORS = [
  { value: '==', label: 'equals (==)' },
  { value: '!=', label: 'not equals (!=)' },
  { value: '>', label: 'greater than (>)' },
  { value: '<', label: 'less than (<)' },
  { value: '>=', label: 'greater or equal (>=)' },
  { value: '<=', label: 'less or equal (<=)' },
]

// Available alert levels
const ALERT_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

// Common event fields
const EVENT_FIELDS = ['severity', 'latency_ms', 'event_type', 'source']

// Level badge colors
const levelColors: Record<string, string> = {
  LOW: 'bg-blue-500/20 text-blue-400',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400',
  HIGH: 'bg-orange-500/20 text-orange-400',
  CRITICAL: 'bg-red-600/30 text-red-300',
}

interface RuleFormData {
  name: string
  field: string
  operator: string
  value: string
  alert_level: string
  message_template: string
  enabled: boolean
}

const emptyForm: RuleFormData = {
  name: '',
  field: 'severity',
  operator: '==',
  value: '',
  alert_level: 'MEDIUM',
  message_template: '',
  enabled: true,
}

export function RulesPage() {
  // State
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedScope, setSelectedScope] = useState<'global' | number>('global')
  const [rules, setRules] = useState<AlertRule[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null)
  const [formData, setFormData] = useState<RuleFormData>(emptyForm)
  const [error, setError] = useState<string | null>(null)

  // Fetch projects on mount
  useEffect(() => {
    async function fetchProjects() {
      try {
        const response = await api.getProjects()
        setProjects(response.items)
      } catch (err) {
        console.error('Failed to fetch projects:', err)
      }
    }
    fetchProjects()
  }, [])

  // Fetch rules when scope changes
  useEffect(() => {
    async function fetchRules() {
      setIsLoading(true)
      try {
        if (selectedScope === 'global') {
          const response = await api.getGlobalRules()
          setRules(response.items)
        } else {
          const response = await api.getProjectRules(selectedScope)
          setRules(response.items)
        }
      } catch (err) {
        console.error('Failed to fetch rules:', err)
        setError('Failed to load rules')
      } finally {
        setIsLoading(false)
      }
    }
    fetchRules()
  }, [selectedScope])

  // Open form for new rule
  function handleNewRule() {
    setEditingRule(null)
    setFormData(emptyForm)
    setShowForm(true)
    setError(null)
  }

  // Open form for editing
  function handleEdit(rule: AlertRule) {
    setEditingRule(rule)
    setFormData({
      name: rule.name,
      field: rule.field,
      operator: rule.operator,
      value: rule.value,
      alert_level: rule.alert_level,
      message_template: rule.message_template,
      enabled: rule.enabled,
    })
    setShowForm(true)
    setError(null)
  }

  // Toggle rule enabled/disabled
  async function handleToggle(rule: AlertRule) {
    try {
      const update: AlertRuleUpdate = { enabled: !rule.enabled }
      if (rule.project_id === null) {
        await api.updateGlobalRule(rule.id, update)
      } else {
        await api.updateProjectRule(rule.project_id, rule.id, update)
      }
      setRules(prev => prev.map(r => 
        r.id === rule.id ? { ...r, enabled: !r.enabled } : r
      ))
    } catch (err) {
      console.error('Failed to toggle rule:', err)
      setError('Failed to update rule')
    }
  }

  // Delete rule
  async function handleDelete(rule: AlertRule) {
    if (!confirm(`Delete rule "${rule.name}"?`)) return
    
    try {
      if (rule.project_id === null) {
        await api.deleteGlobalRule(rule.id)
      } else {
        await api.deleteProjectRule(rule.project_id, rule.id)
      }
      setRules(prev => prev.filter(r => r.id !== rule.id))
    } catch (err) {
      console.error('Failed to delete rule:', err)
      setError('Failed to delete rule')
    }
  }

  // Save rule (create or update)
  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    try {
      if (editingRule) {
        // Update existing rule
        const update: AlertRuleUpdate = {
          field: formData.field,
          operator: formData.operator,
          value: formData.value,
          alert_level: formData.alert_level,
          message_template: formData.message_template,
          enabled: formData.enabled,
        }
        
        let updated: AlertRule
        if (editingRule.project_id === null) {
          updated = await api.updateGlobalRule(editingRule.id, update)
        } else {
          updated = await api.updateProjectRule(editingRule.project_id, editingRule.id, update)
        }
        
        setRules(prev => prev.map(r => r.id === editingRule.id ? updated : r))
      } else {
        // Create new rule
        const create: AlertRuleCreate = {
          name: formData.name,
          field: formData.field,
          operator: formData.operator,
          value: formData.value,
          alert_level: formData.alert_level,
          message_template: formData.message_template,
          enabled: formData.enabled,
        }
        
        let created: AlertRule
        if (selectedScope === 'global') {
          created = await api.createGlobalRule(create)
        } else {
          created = await api.createProjectRule(selectedScope, create)
        }
        
        setRules(prev => [...prev, created])
      }
      
      setShowForm(false)
      setEditingRule(null)
      setFormData(emptyForm)
    } catch (err: unknown) {
      console.error('Failed to save rule:', err)
      setError(err instanceof Error ? err.message : 'Failed to save rule')
    }
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
      {/* Header with scope selector */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <label className="text-[var(--color-text-secondary)]">Scope:</label>
          <select
            value={selectedScope}
            onChange={(e) => setSelectedScope(e.target.value === 'global' ? 'global' : Number(e.target.value))}
            className="px-3 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-cyan)]"
          >
            <option value="global">Global Rules</option>
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <button
          onClick={handleNewRule}
          className="flex items-center gap-2 px-4 py-2 bg-[var(--color-accent-cyan)] hover:bg-[var(--color-accent-cyan)]/80 text-black rounded-lg transition-colors font-medium"
        >
          <Plus className="w-4 h-4" />
          New Rule
        </button>
      </div>

      {/* Scope description */}
      <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-4">
        <div className="flex items-center gap-2 text-[var(--color-text-secondary)]">
          {selectedScope === 'global' ? (
            <>
              <Globe className="w-5 h-5 text-[var(--color-accent-cyan)]" />
              <span>Global rules apply to all projects unless overridden by a project-specific rule with the same name.</span>
            </>
          ) : (
            <>
              <FolderOpen className="w-5 h-5 text-[var(--color-accent-purple)]" />
              <span>Project rules override global rules with the same name for this project only.</span>
            </>
          )}
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
          {error}
        </div>
      )}

      {/* Rule Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-[var(--color-border)]">
              <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">
                {editingRule ? 'Edit Rule' : 'Create Rule'}
              </h2>
            </div>
            
            <form onSubmit={handleSave} className="p-6 space-y-4">
              {/* Name (only for new rules) */}
              {!editingRule && (
                <div>
                  <label className="block text-sm text-[var(--color-text-secondary)] mb-2">
                    Rule Name
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., high_latency, critical_error"
                    className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-cyan)]"
                    required
                  />
                </div>
              )}

              {/* Condition: field, operator, value */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm text-[var(--color-text-secondary)] mb-2">
                    Field
                  </label>
                  <select
                    value={formData.field}
                    onChange={(e) => setFormData(prev => ({ ...prev, field: e.target.value }))}
                    className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-cyan)]"
                  >
                    {EVENT_FIELDS.map(f => (
                      <option key={f} value={f}>{f}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm text-[var(--color-text-secondary)] mb-2">
                    Operator
                  </label>
                  <select
                    value={formData.operator}
                    onChange={(e) => setFormData(prev => ({ ...prev, operator: e.target.value }))}
                    className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-cyan)]"
                  >
                    {OPERATORS.map(op => (
                      <option key={op.value} value={op.value}>{op.label}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm text-[var(--color-text-secondary)] mb-2">
                    Value
                  </label>
                  <input
                    type="text"
                    value={formData.value}
                    onChange={(e) => setFormData(prev => ({ ...prev, value: e.target.value }))}
                    placeholder="e.g., CRITICAL, 5000"
                    className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-cyan)]"
                    required
                  />
                </div>
              </div>

              {/* Alert Level */}
              <div>
                <label className="block text-sm text-[var(--color-text-secondary)] mb-2">
                  Alert Level
                </label>
                <select
                  value={formData.alert_level}
                  onChange={(e) => setFormData(prev => ({ ...prev, alert_level: e.target.value }))}
                  className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-cyan)]"
                >
                  {ALERT_LEVELS.map(level => (
                    <option key={level} value={level}>{level}</option>
                  ))}
                </select>
              </div>

              {/* Message Template */}
              <div>
                <label className="block text-sm text-[var(--color-text-secondary)] mb-2">
                  Message Template
                </label>
                <input
                  type="text"
                  value={formData.message_template}
                  onChange={(e) => setFormData(prev => ({ ...prev, message_template: e.target.value }))}
                  placeholder="e.g., High latency: {latency_ms}ms from {source}"
                  className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-cyan)]"
                  required
                />
                <p className="text-xs text-[var(--color-text-muted)] mt-1">
                  Use {'{field}'} for placeholders: {'{source}'}, {'{event_type}'}, {'{severity}'}, {'{latency_ms}'}
                </p>
              </div>

              {/* Enabled Toggle */}
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.enabled}
                  onChange={(e) => setFormData(prev => ({ ...prev, enabled: e.target.checked }))}
                  className="w-5 h-5 rounded border-[var(--color-border)] bg-[var(--color-bg-tertiary)] text-[var(--color-accent-cyan)] focus:ring-[var(--color-accent-cyan)]"
                />
                <span className="text-[var(--color-text-primary)]">Rule is enabled</span>
              </label>

              {/* Form Actions */}
              <div className="flex justify-end gap-3 pt-4 border-t border-[var(--color-border)]">
                <button
                  type="button"
                  onClick={() => { setShowForm(false); setEditingRule(null); }}
                  className="px-4 py-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[var(--color-accent-cyan)] hover:bg-[var(--color-accent-cyan)]/80 text-black rounded-lg transition-colors font-medium"
                >
                  {editingRule ? 'Save Changes' : 'Create Rule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Rules List */}
      <div className="space-y-3">
        {rules.length === 0 ? (
          <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-8 text-center">
            <Settings2 className="w-12 h-12 text-[var(--color-text-muted)] mx-auto mb-4" />
            <p className="text-[var(--color-text-primary)] font-medium">No rules yet</p>
            <p className="text-[var(--color-text-muted)] mt-1">Create a rule to start generating alerts</p>
          </div>
        ) : (
          rules.map(rule => (
            <div
              key={rule.id}
              className={`bg-[var(--color-bg-secondary)] border rounded-lg p-4 ${
                rule.enabled 
                  ? 'border-[var(--color-border)]' 
                  : 'border-[var(--color-border)] opacity-60'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <span className="font-mono text-[var(--color-accent-cyan)]">{rule.name}</span>
                    <span className={`text-xs px-2 py-1 rounded ${levelColors[rule.alert_level] || ''}`}>
                      {rule.alert_level}
                    </span>
                    {rule.project_id === null ? (
                      <span className="text-xs px-2 py-1 rounded bg-[var(--color-accent-cyan)]/10 text-[var(--color-accent-cyan)]">
                        Global
                      </span>
                    ) : (
                      <span className="text-xs px-2 py-1 rounded bg-[var(--color-accent-purple)]/10 text-[var(--color-accent-purple)]">
                        Override
                      </span>
                    )}
                    {!rule.enabled && (
                      <span className="text-xs px-2 py-1 rounded bg-gray-500/20 text-gray-400">
                        Disabled
                      </span>
                    )}
                  </div>
                  
                  <div className="font-mono text-sm text-[var(--color-text-secondary)] mb-2">
                    {rule.field} {rule.operator} "{rule.value}"
                  </div>
                  
                  <p className="text-sm text-[var(--color-text-muted)]">
                    {rule.message_template}
                  </p>
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleToggle(rule)}
                    className={`p-2 rounded-lg transition-colors ${
                      rule.enabled 
                        ? 'text-[var(--color-accent-green)] hover:bg-[var(--color-accent-green)]/10' 
                        : 'text-gray-500 hover:bg-gray-500/10'
                    }`}
                    title={rule.enabled ? 'Disable' : 'Enable'}
                  >
                    {rule.enabled ? <Power className="w-5 h-5" /> : <PowerOff className="w-5 h-5" />}
                  </button>
                  
                  <button
                    onClick={() => handleEdit(rule)}
                    className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-accent-cyan)] hover:bg-[var(--color-accent-cyan)]/10 rounded-lg transition-colors"
                    title="Edit"
                  >
                    <Pencil className="w-5 h-5" />
                  </button>
                  
                  <button
                    onClick={() => handleDelete(rule)}
                    className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-severity-error)] hover:bg-[var(--color-severity-error)]/10 rounded-lg transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

