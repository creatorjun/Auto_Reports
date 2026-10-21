// frontend/src/app/router.tsx
import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import Layout from '@/presentation/components/layout/Layout'
import ProtectedRoute from '@/presentation/components/auth/ProtectedRoute'
import SuperadminRoute from '@/presentation/components/auth/SuperadminRoute'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import LazyErrorBoundary from '@/presentation/components/common/LazyErrorBoundary'

const DashboardPage          = lazy(() => import('@/presentation/pages/DashboardPage'))
const IssueManagementPage    = lazy(() => import('@/presentation/pages/IssueManagementPage'))
const SlaDashboardPage       = lazy(() => import('@/presentation/pages/SlaDashboardPage'))
const SlaViolationPage       = lazy(() => import('@/presentation/pages/SlaViolationPage'))
const SlaStatusPage          = lazy(() => import('@/presentation/pages/SlaStatusPage'))
const RedeploymentPage       = lazy(() => import('@/presentation/pages/RedeploymentPage'))
const HistoryPage            = lazy(() => import('@/presentation/pages/HistoryPage'))
const AuditLogPage           = lazy(() => import('@/presentation/pages/AuditLogPage'))
const SecurityNewsPage       = lazy(() => import('@/presentation/pages/SecurityNewsPage'))
const StoragePage            = lazy(() => import('@/presentation/pages/StoragePage'))
const StoragePreviewPage     = lazy(() => import('@/presentation/pages/StoragePreviewPage'))
const LoginPage              = lazy(() => import('@/presentation/pages/LoginPage'))
const AdminLoginPage         = lazy(() => import('@/presentation/pages/AdminLoginPage'))
const AdminJiraPrivacyPage   = lazy(() => import('@/presentation/pages/AdminJiraPrivacyPage'))
const PrivacyPage            = lazy(() => import('@/presentation/pages/PrivacyPage'))
const TermsPage              = lazy(() => import('@/presentation/pages/TermsPage'))
const SiteManagementPage     = lazy(() => import('@/presentation/pages/SiteManagementPage'))
const SiteCreatePage         = lazy(() => import('@/presentation/pages/SiteCreatePage'))
const SiteDetailPage         = lazy(() => import('@/presentation/pages/SiteDetailPage'))
const PartnerManagementPage  = lazy(() => import('@/presentation/pages/PartnerManagementPage'))

const Fallback = () => <LoadingSpinner text="페이지 로딩 중..." />

const Wrap = ({ children }: { children: React.ReactNode }) => (
  <LazyErrorBoundary>
    <Suspense fallback={<Fallback />}>{children}</Suspense>
  </LazyErrorBoundary>
)

export const router = createBrowserRouter([
  { path: '/login',           element: <Wrap><LoginPage /></Wrap> },
  { path: '/admin',           element: <Wrap><AdminLoginPage /></Wrap> },
  { path: '/admin/jira-privacy', element: <Wrap><AdminJiraPrivacyPage /></Wrap> },
  { path: '/privacy',         element: <Wrap><PrivacyPage /></Wrap> },
  { path: '/terms',           element: <Wrap><TermsPage /></Wrap> },
  { path: '/storage/preview', element: <Wrap><StoragePreviewPage /></Wrap> },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      { index: true,            element: <Wrap><DashboardPage /></Wrap> },
      { path: 'redeployments', element: <Wrap><RedeploymentPage /></Wrap> },
      { path: 'sla-violations', element: <Wrap><SlaViolationPage /></Wrap> },
      { path: 'sla-status', element: <Wrap><SlaStatusPage /></Wrap> },
      { path: 'sla-violations/history/:id', element: <Wrap><SlaViolationPage /></Wrap> },
      { path: 'issues',         element: <Wrap><IssueManagementPage /></Wrap> },
      { path: 'security-news',  element: <Wrap><SecurityNewsPage /></Wrap> },
      { path: 'sla-dashboard',  element: <Wrap><SlaDashboardPage /></Wrap> },
      { path: 'history',        element: <Wrap><HistoryPage /></Wrap> },
      { path: 'audit-logs', element: <SuperadminRoute><Wrap><AuditLogPage /></Wrap></SuperadminRoute> },
      { path: 'reports/annual/:year', element: <Wrap><DashboardPage /></Wrap> },
      { path: 'reports/:id',    element: <Wrap><DashboardPage /></Wrap> },
      { path: 'partners',       element: <Wrap><PartnerManagementPage /></Wrap> },
      { path: 'storage',        element: <Wrap><StoragePage /></Wrap> },
      { path: 'sites',          element: <Wrap><SiteManagementPage /></Wrap> },
      { path: 'sites/new',      element: <Wrap><SiteCreatePage /></Wrap> },
      { path: 'sites/:id',      element: <Wrap><SiteDetailPage /></Wrap> },
      { path: 'sites/:id/edit', element: <Wrap><SiteCreatePage /></Wrap> },
    ],
  },
  { path: '*', element: <Navigate to="/login" replace /> },
])
