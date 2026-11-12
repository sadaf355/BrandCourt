import React, { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  ShieldCheck,
  LayoutDashboard,
  FileCheck2,
  BookOpen,
  CheckCircle2,
  Palette,
  Workflow,
  Sparkles,
  Activity,
  Users,
  LogOut,
  Layers,
  Settings,
  Scale,
  Cpu,
  PanelLeftClose,
  PanelLeftOpen,
  PanelLeft,
} from 'lucide-react'
import { User, Role } from '../../types/api'
import { api, setToken } from '../../lib/api'
import { ThemeToggle } from '../ThemeToggle'
import { NotificationBell } from './NotificationBell'

interface AppShellProps {
  user: User
  workspaceName?: string
  onSignOut: () => void
  onUserChanged?: (user: User) => void
  children: React.ReactNode
}

export function AppShell({ user, workspaceName = 'Brand Workspace', onSignOut, onUserChanged, children }: AppShellProps) {
  const location = useLocation()
  const roleName = user.role === 'admin' ? 'Guideline owner' : user.role.charAt(0).toUpperCase() + user.role.slice(1)

  const DEMO_ROLES: { role: Role; label: string; summary: string }[] = [
    { role: 'admin', label: 'Admin', summary: 'Rules, facts, models & approvals' },
    { role: 'creator', label: 'Creator', summary: 'Draft content, run checks & edit' },
    { role: 'reviewer', label: 'Reviewer', summary: 'Inspect queue, verify & override' },
    { role: 'manager', label: 'Manager', summary: 'Approve, lock & export reports' },
  ]

  const isDemoUser = Boolean(
    user.email.endsWith('@glowserum.com') ||
    user.email.endsWith('@demo.local') ||
    workspaceName.toLowerCase().includes('glowserum demo')
  )

  const [switchingRole, setSwitchingRole] = useState(false)

  const handleDemoRoleSwitch = async (targetRole: Role) => {
    if (targetRole === user.role || switchingRole) return
    setSwitchingRole(true)
    try {
      const result = await api<{ access_token: string; user: User }>('/auth/demo-login', {
        method: 'POST',
        body: JSON.stringify({ role: targetRole }),
      })
      setToken(result.access_token)
      if (onUserChanged) {
        onUserChanged(result.user)
      } else {
        window.location.reload()
      }
    } catch (err) {
      console.error('Failed to switch demo role:', err)
    } finally {
      setSwitchingRole(false)
    }
  }

  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('brandcourt_sidebar_collapsed') === 'true'
    } catch {
      return false
    }
  })

  const toggleSidebar = () => {
    setIsCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem('brandcourt_sidebar_collapsed', String(next))
      } catch (_err) {
        // Ignore localStorage quota or private-browsing errors
      }
      return next
    })
  }

  const navItems = [
    { label: 'Dashboard', icon: LayoutDashboard, to: '/app/dashboard', roles: ['creator', 'reviewer', 'manager', 'admin'] },
    { label: 'Content Reviews', icon: FileCheck2, to: '/app/reviews', roles: ['creator', 'reviewer', 'manager', 'admin'] },
    { label: 'Reviewer Queue', icon: Workflow, to: '/app/reviewer/queue', roles: ['reviewer', 'manager', 'admin'] },
    { label: 'Approvals Gate', icon: ShieldCheck, to: '/app/approvals', roles: ['manager', 'admin'] },
    { label: 'Brand Guidelines', icon: BookOpen, to: '/app/brand/guidelines', roles: ['manager', 'admin'] },
    { label: 'Brand Rules', icon: BookOpen, to: '/app/brand/rules', roles: ['manager', 'admin', 'reviewer'] },
    { label: 'Approved Facts', icon: CheckCircle2, to: '/app/brand/facts', roles: ['creator', 'reviewer', 'manager', 'admin'] },
    { label: 'Brand Assets', icon: Palette, to: '/app/brand/assets', roles: ['manager', 'admin'] },
    { label: 'Guideline Health', icon: Activity, to: '/app/brand/guideline-health', roles: ['reviewer', 'manager', 'admin'] },
    { label: 'Precedents', icon: Scale, to: '/app/intelligence/precedents', roles: ['reviewer', 'manager', 'admin'] },
    { label: 'Fix Sandbox', icon: Sparkles, to: '/app/intelligence/fix-verify', roles: ['creator', 'reviewer', 'manager', 'admin'] },
    { label: 'Insights & Reports', icon: LayoutDashboard, to: '/app/insights', roles: ['manager', 'admin'] },
    { label: 'Model Settings', icon: Cpu, to: '/app/settings/models', roles: ['admin'] },
    { label: 'Audit Trail', icon: Layers, to: '/app/audit', roles: ['reviewer', 'manager', 'admin'] },
  ]

  const visibleNav = navItems.filter((item) => item.roles.includes(user.role))

  return (
    <div className="app-shell">
      {/* Sidebar Navigation */}
      <aside
        className={`sidebar ${isCollapsed ? 'sidebar--collapsed' : ''}`}
        aria-label="Workspace sidebar navigation"
      >
        <div className="sidebar-header-row">
          <NavLink
            to="/app/dashboard"
            className="brand-lockup"
            aria-label={isCollapsed ? 'BrandCourt Home' : undefined}
            title="BrandCourt Home"
          >
            <span className="brand-mark">
              <ShieldCheck size={21} strokeWidth={2.1} />
            </span>
            {!isCollapsed && (
              <span className="brand-word">
                BrandCourt<span className="brand-period">.</span>
                <small>GOVERNANCE PLATFORM</small>
              </span>
            )}
          </NavLink>

          <button
            type="button"
            className="sidebar-toggle-btn"
            onClick={toggleSidebar}
            title={isCollapsed ? 'Open sidebar' : 'Collapse sidebar'}
            aria-label={isCollapsed ? 'Open sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>
        </div>

        {/* Workspace details */}
        <div
          className="workspace-switcher"
          title={`${workspaceName} • ${roleName} access`}
        >
          <span className="workspace-avatar">
            {user.full_name
              .split(' ')
              .map((x) => x[0])
              .slice(0, 2)
              .join('')
              .toUpperCase()}
          </span>
          {!isCollapsed && (
            <span className="workspace-switcher__copy">
              <b>{workspaceName}</b>
              <small>{roleName} access</small>
            </span>
          )}
        </div>

        {!isCollapsed && <div className="nav-section-label">NAVIGATION</div>}
        <nav className="side-nav" aria-label="Workspace navigation">
          {visibleNav.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname.startsWith(item.to)
            return (
              <NavLink
                key={item.to}
                to={item.to}
                title={item.label}
                className={`nav-link ${isActive ? 'nav-link--active' : ''}`}
              >
                <Icon size={17} />
                {!isCollapsed && <span>{item.label}</span>}
              </NavLink>
            )
          })}
        </nav>

        {!isCollapsed && (
          <div className="nav-section-label nav-section-label--lower">
            SETTINGS
          </div>
        )}
        <nav className="side-nav" aria-label="Settings navigation">
          <NavLink
            to="/app/settings/profile"
            title="Profile Settings"
            className={({ isActive }) => `nav-link ${isActive ? 'nav-link--active' : ''}`}
          >
            <Settings size={17} />
            {!isCollapsed && <span>Profile Settings</span>}
          </NavLink>
          {user.role === 'admin' && (
            <NavLink
              to="/app/settings/workspace"
              title="Workspace Members"
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link--active' : ''}`}
            >
              <Users size={17} />
              {!isCollapsed && <span>Workspace Members</span>}
            </NavLink>
          )}
        </nav>

        <div className="sidebar-bottom">
          {!isCollapsed ? (
            <div className="sidebar-version">
              <span className="version-dot" /> BrandCourt <span>v2.0.0</span>
            </div>
          ) : (
            <div className="sidebar-version sidebar-version--collapsed" title="BrandCourt v2.0.0">
              <span className="version-dot" />
            </div>
          )}
        </div>
      </aside>

      {/* Main Page Area */}
      <div className="app-main">
        <header className="topbar">
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <button
              type="button"
              className="topbar-sidebar-toggle"
              onClick={toggleSidebar}
              title={isCollapsed ? 'Open sidebar' : 'Collapse sidebar'}
              aria-label={isCollapsed ? 'Open sidebar' : 'Collapse sidebar'}
            >
              <PanelLeft size={18} />
            </button>

            <div className="breadcrumbs">
              <span>Workspace</span>
              <span className="breadcrumb-slash">/</span>
              <b>{workspaceName}</b>
            </div>
          </div>

          <div className="topbar-actions">
            {isDemoUser && (
              <div
                className="demo-role-switcher"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.2rem',
                  padding: '0.15rem 0.35rem',
                  borderRadius: '0.375rem',
                  border: '1px solid var(--border, #cbd5e1)',
                  background: 'var(--bg-subtle, #f1f5f9)',
                  marginRight: '0.35rem',
                }}
              >
                <span
                  style={{
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    color: 'var(--fg-muted, #64748b)',
                    padding: '0 0.2rem',
                    whiteSpace: 'nowrap',
                  }}
                >
                  Demo:
                </span>
                {DEMO_ROLES.map(({ role, label, summary }) => {
                  const isCurrent = user.role === role
                  return (
                    <button
                      key={role}
                      type="button"
                      disabled={switchingRole}
                      onClick={() => handleDemoRoleSwitch(role)}
                      style={{
                        padding: '0.2rem 0.5rem',
                        fontSize: '0.72rem',
                        fontWeight: isCurrent ? 700 : 500,
                        borderRadius: '0.25rem',
                        border: 'none',
                        background: isCurrent ? 'var(--btn-primary-bg, #0f766e)' : 'transparent',
                        color: isCurrent ? '#ffffff' : 'var(--text, #0f172a)',
                        cursor: switchingRole ? 'not-allowed' : 'pointer',
                        transition: 'background 0.15s ease',
                      }}
                      title={`${label}: ${summary}`}
                      aria-label={`Switch to ${label} (${summary})`}
                    >
                      {label}
                    </button>
                  )
                })}
              </div>
            )}
            <NotificationBell />
            <ThemeToggle />
            <div
              className="profile-avatar"
              title={`${user.full_name} (${roleName})`}
            >
              {user.full_name
                .split(' ')
                .map((x) => x[0])
                .slice(0, 2)
                .join('')
                .toUpperCase()}
            </div>
            <button
              className="signout-button"
              onClick={onSignOut}
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </header>

        <main style={{ flex: 1, width: '100%', boxSizing: 'border-box' }}>{children}</main>
      </div>
    </div>
  )
}
