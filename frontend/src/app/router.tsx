// frontend/src/app/router.tsx
import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import Layout from '@/presentation/components/layout/Layout'
import ProtectedRoute from '@/presentation/components/auth/ProtectedRoute'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import LazyErrorBoundary from '@/presentation/components/common/LazyErrorBoundary'

const DashboardPage          = lazy(() => import('@/presentation/pages/DashboardPage'))
const SlaDashboardPage       = lazy(() => import('@/presentation/pages/SlaDashboardPage'))
const HistoryPage            = lazy(() => import('@/presentation/pages/HistoryPage'))
const StoragePage            = lazy(() => import('@/presentation/pages/StoragePage'))
const StoragePreviewPage     = lazy(() => import('@/presentation/pages/StoragePreviewPage'))
const LoginPage              = lazy(() => import('@/presentation/pages/LoginPage'))
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
      { path: 'sla-dashboard',  element: <Wrap><SlaDashboardPage /></Wrap> },
      { path: 'history',        element: <Wrap><HistoryPage /></Wrap> },
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
