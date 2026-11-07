import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import { ThemeProvider } from './providers/ThemeProvider'
import { ToastProvider } from './components/common/Toast'
import { ErrorBoundary } from './components/common/ErrorBoundary'
import { AppShell } from './components/layout/AppShell'
import { PermissionDeniedState } from './components/common/FeedbackStates'

// Landing & Auth
import { LandingPage } from './features/landing/LandingPage'
import { AuthPage } from './pages/AuthPage'

// Features & Pages
import { ReviewsListPage } from './features/reviews/components/ReviewsListPage'
import { NewReviewPage } from './features/reviews/components/NewReviewPage'
import { ReviewDetailPage } from './features/reviews/components/ReviewDetailPage'
import { DashboardPage } from './pages/DashboardPage'
import { ReviewerQueuePage } from './features/approvals/components/ReviewerQueuePage'
import { ApprovalManagerScreen } from './features/approvals/components/ApprovalManagerScreen'
import { RulesPage } from './features/brand/components/RulesPage'
import { FactsPage } from './features/brand/components/FactsPage'
import { AssetsPage } from './features/brand/components/AssetsPage'
import { GuidelinesPage } from './features/brand/components/GuidelinesPage'
import { MemberManagementPage } from './features/settings/components/MemberManagementPage'
import { WorkspaceSettingsPage } from './features/settings/components/WorkspaceSettingsPage'
import { AuditTrailPage } from './features/settings/components/AuditTrailPage'
import { InsightsDashboard } from './features/insights/components/InsightsDashboard'
import { GuidelineHealthPage } from './features/intelligence/components/GuidelineHealthPage'
import { PrecedentLedgerPage } from './features/intelligence/components/PrecedentLedgerPage'
import { FixVerificationView } from './features/intelligence/components/FixVerificationView'
import { ModelSettingsPage } from './features/intelligence/components/ModelSettingsPage'
import { WorkflowPage } from './pages/WorkflowPage'

import { User } from './types/api'
import { apiClient, getToken, setToken } from './lib/api'

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [workspaceName, setWorkspaceName] = useState('Brand Workspace')
  const [checking, setChecking] = useState(Boolean(getToken()))
  const navigate = useNavigate()

  useEffect(() => {
    let alive = true
    const token = getToken()
    if (!token) {
      setChecking(false)
      return
    }

    apiClient
      .getMe()
      .then((data) => {
        if (alive) setUser(data)
      })
      .catch(() => {
        setToken(null)
        if (alive) setUser(null)
      })
      .finally(() => {
        if (alive) setChecking(false)
      })

    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    if (!user) return
    let alive = true
    apiClient
      .getWorkspace()
      .then((ws) => {
        if (alive && ws.name) setWorkspaceName(ws.name)
      })
      .catch(() => { })
    return () => {
      alive = false
    }
  }, [user])

  const handleSignOut = () => {
    setToken(null)
    setUser(null)
    navigate('/')
  }

  if (checking) {
    return (
      <div className="app-loading" style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem' }}>
        <ShieldCheck size={26} color="var(--accent, #6366f1)" />
        <span>Preparing your workspace…</span>
      </div>
    )
  }

  return (
    <ThemeProvider>
      <ToastProvider>
        <ErrorBoundary>
          {!user ? (
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<AuthPage onSignedIn={setUser} initialMode="login" />} />
              <Route path="/signup" element={<AuthPage onSignedIn={setUser} initialMode="register" />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          ) : (
            <AppShell user={user} workspaceName={workspaceName} onSignOut={handleSignOut}>
              <Routes>
                {/* Modern /app/... hierarchy */}
                <Route path="/app/dashboard" element={<DashboardPage />} />
                <Route path="/app/reviews" element={<ReviewsListPage />} />
                <Route path="/app/reviews/new" element={<NewReviewPage />} />
                <Route path="/app/reviews/:id" element={<ReviewDetailPage user={user} />} />
                <Route path="/app/reviewer/queue" element={<ReviewerQueuePage />} />
                <Route path="/app/approvals" element={<WorkflowPage role={user.role} />} />
                <Route path="/app/approvals/:id" element={<ApprovalManagerScreen />} />
                <Route path="/app/brand/guidelines" element={<GuidelinesPage />} />
                <Route path="/app/brand/rules" element={<RulesPage userRole={user.role} />} />
                <Route path="/app/brand/facts" element={<FactsPage />} />
                <Route path="/app/brand/assets" element={<AssetsPage />} />
                <Route path="/app/brand/guideline-health" element={<GuidelineHealthPage />} />
                <Route path="/app/insights" element={<InsightsDashboard />} />
                <Route path="/app/precedents" element={<PrecedentLedgerPage />} />
                <Route path="/app/intelligence/precedents" element={<PrecedentLedgerPage />} />
                <Route path="/app/intelligence/fix-verify" element={<FixVerificationView />} />
                <Route path="/app/settings/models" element={<ModelSettingsPage />} />
                <Route path="/app/audit" element={<AuditTrailPage currentUserRole={user.role} />} />
                <Route
                  path="/app/settings/profile"
                  element={<MemberManagementPage currentUserId={user.id} currentUserRole={user.role} />}
                />
                <Route
                  path="/app/settings/workspace"
                  element={<WorkspaceSettingsPage currentUserRole={user.role} />}
                />
                <Route
                  path="/app/settings/members"
                  element={<MemberManagementPage currentUserId={user.id} currentUserRole={user.role} />}
                />
                <Route
                  path="/app/unauthorized"
                  element={<PermissionDeniedState onBack={() => navigate('/app/dashboard')} />}
                />

                {/* Legacy route redirects under /app/ structure */}
                <Route path="/reviews" element={<Navigate to="/app/reviews" replace />} />
                <Route path="/knowledge" element={<Navigate to="/app/brand/rules" replace />} />
                <Route path="/rules" element={<Navigate to="/app/brand/rules" replace />} />
                <Route path="/facts" element={<Navigate to="/app/brand/facts" replace />} />
                <Route path="/assets" element={<Navigate to="/app/brand/assets" replace />} />
                <Route path="/members" element={<Navigate to="/app/settings/workspace" replace />} />
                <Route path="/audit" element={<Navigate to="/app/audit" replace />} />
                <Route path="/guideline-health" element={<Navigate to="/app/brand/guideline-health" replace />} />
                <Route path="/insights" element={<Navigate to="/app/insights" replace />} />
                <Route path="/reviewer-queue" element={<Navigate to="/app/reviewer/queue" replace />} />
                <Route path="/review-workflow" element={<Navigate to="/app/approvals" replace />} />

                {/* Fallback */}
                <Route path="/" element={<Navigate to="/app/dashboard" replace />} />
                <Route path="*" element={<Navigate to="/app/dashboard" replace />} />
              </Routes>
            </AppShell>
          )}
        </ErrorBoundary>
      </ToastProvider>
    </ThemeProvider>
  )
}
