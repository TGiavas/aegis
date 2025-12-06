/**
 * Layout component with Sidebar and Header
 * 
 * Wraps all authenticated pages with consistent navigation.
 */
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { 
  LayoutDashboard, 
  Activity, 
  Bell, 
  FolderOpen,
  LogOut,
  Shield
} from 'lucide-react'

// Navigation items
const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/events', label: 'Events', icon: Activity },
  { path: '/alerts', label: 'Alerts', icon: Bell },
  { path: '/projects', label: 'Projects', icon: FolderOpen },
]

export function Layout() {
  const { logout } = useAuth()
  const location = useLocation()

  // Get current page title
  const currentPage = navItems.find(item => item.path === location.pathname)
  const pageTitle = currentPage?.label || 'Dashboard'

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)] flex">
      {/* ========== SIDEBAR ========== */}
      <aside className="w-64 bg-[var(--color-bg-secondary)] border-r border-[var(--color-border)] flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-[var(--color-accent-cyan)]" />
            <span className="text-xl font-bold text-[var(--color-text-primary)]">
              Aegis
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {navItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-[var(--color-accent-cyan)]/10 text-[var(--color-accent-cyan)]'
                        : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]'
                    }`
                  }
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Sign Out Button */}
        <div className="p-4 border-t border-[var(--color-border)]">
          <button
            onClick={logout}
            className="flex items-center gap-3 w-full px-4 py-3 rounded-lg text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-severity-error)] transition-colors"
          >
            <LogOut className="w-5 h-5" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {/* ========== MAIN CONTENT ========== */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="h-16 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)] flex items-center px-6">
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
            {pageTitle}
          </h1>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

