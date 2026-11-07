import React from 'react'
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
} from 'lucide-react'
import { User } from '../../types/api'
import { ThemeToggle } from '../ThemeToggle'
import { NotificationBell } from './NotificationBell'

interface AppShellProps {
  user: User
  workspaceName?: string
  onSignOut: () => void
  children: React.ReactNode
}

export function AppShell({ user, workspaceName = 'Brand Workspace', onSignOut, children }: AppShellProps) {
  const location = useLocation()
  const roleName = user.role === 'admin' ? 'Guideline owner' : user.role.charAt(0).toUpperCase() + user.role.slice(1)

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
    <div className="app-shell" style={{ minHeight: '100vh', display: 'flex' }}>
      {/* Sidebar Navigation */}
      <aside className="sidebar" style={{ width: '260px', flexShrink: 0 }}>
        <NavLink to="/app/dashboard" className="brand-lockup" aria-label="BrandCourt Home">
          <span className="brand-mark">
            <ShieldCheck size={21} strokeWidth={2.1} />
          </span>
          <span className="brand-word">
            BrandCourt<span className="brand-period">.</span>
            <small>GOVERNANCE PLATFORM</small>
          </span>
        </NavLink>

        {/* Workspace details */}
        <div className="workspace-switcher" style={{ margin: '1rem 0' }}>
          <span className="workspace-avatar">
            {user.full_name
              .split(' ')
              .map((x) => x[0])
              .slice(0, 2)
              .join('')
              .toUpperCase()}
          </span>
          <span className="workspace-switcher__copy">
            <b>{workspaceName}</b>
            <small>{roleName} access</small>
          </span>
        </div>

        <div className="nav-section-label">NAVIGATION</div>
        <nav className="side-nav" aria-label="Workspace navigation">
          {visibleNav.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname.startsWith(item.to)
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`nav-link ${isActive ? 'nav-link--active' : ''}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.65rem',
                  padding: '0.55rem 0.85rem',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  textDecoration: 'none',
                  color: isActive ? 'var(--accent, #818cf8)' : 'var(--color-text-secondary, #cbd5e1)',
                  backgroundColor: isActive ? 'var(--color-bg-subtle, rgba(255, 255, 255, 0.08))' : 'transparent',
                  fontWeight: isActive ? 600 : 400,
                  marginBottom: '0.2rem',
                }}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </nav>

        <div className="nav-section-label nav-section-label--lower" style={{ marginTop: '1.5rem' }}>
          SETTINGS
        </div>
        <NavLink
          to="/app/settings/profile"
          className="nav-link"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.65rem',
            padding: '0.55rem 0.85rem',
            borderRadius: '6px',
            fontSize: '0.85rem',
            textDecoration: 'none',
            color: 'var(--color-text-secondary, #cbd5e1)',
          }}
        >
          <Settings size={16} />
          <span>Profile Settings</span>
        </NavLink>
        {user.role === 'admin' && (
          <NavLink
            to="/app/settings/workspace"
            className="nav-link"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.65rem',
              padding: '0.55rem 0.85rem',
              borderRadius: '6px',
              fontSize: '0.85rem',
              textDecoration: 'none',
              color: 'var(--color-text-secondary, #cbd5e1)',
            }}
          >
            <Users size={16} />
            <span>Workspace Members</span>
          </NavLink>
        )}

        <div className="sidebar-bottom" style={{ marginTop: 'auto', paddingTop: '1.5rem' }}>
          <div className="sidebar-version">
            <span className="version-dot" /> BrandCourt <span>v2.0.0</span>
          </div>
        </div>
      </aside>

      {/* Main Page Area */}
      <div className="app-main" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <header
          className="topbar"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0.75rem 1.5rem',
            borderBottom: '1px solid var(--color-border, rgba(148, 163, 184, 0.15))',
          }}
        >
          <div className="breadcrumbs" style={{ fontSize: '0.85rem', color: 'var(--color-text-muted, #94a3b8)' }}>
            <span>Workspace</span>
            <span className="breadcrumb-slash" style={{ margin: '0 0.5rem' }}>
              /
            </span>
            <strong style={{ color: 'var(--color-text-primary, #ffffff)' }}>{workspaceName}</strong>
          </div>

          <div className="topbar-actions" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <NotificationBell />
            <ThemeToggle />
            <div
              className="profile-avatar"
              title={`${user.full_name} (${roleName})`}
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                backgroundColor: 'var(--accent, #6366f1)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.75rem',
                fontWeight: 700,
              }}
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
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--color-text-muted, #94a3b8)',
                cursor: 'pointer',
                padding: '4px',
              }}
            >
              <LogOut size={16} />
            </button>
          </div>
        </header>

        <main style={{ flex: 1 }}>{children}</main>
      </div>
    </div>
  )
}

