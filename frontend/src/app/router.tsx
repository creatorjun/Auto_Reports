// frontend/src/app/router.tsx
import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import Layout from '@/presentation/components/layout/Layout'
import ProtectedRoute from '@/presentation/components/auth/ProtectedRoute'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

const DashboardPage      = lazy(() => import('@/presentation/pages/DashboardPage'))
const HistoryPage        = lazy(() => import('@/presentation/pages/HistoryPage'))
const StoragePage        = lazy(() => import('@/presentation/pages/StoragePage'))
const StoragePreviewPage = lazy(() => import('@/presentation/pages/StoragePreviewPage'))
const LoginPage          = lazy(() => import('@/presentation/pages/LoginPage'))
const SiteManagementPage = lazy(() => import('@/presentation/pages/SiteManagementPage'))
const SiteCreatePage     = lazy(() => import('@/presentation/pages/SiteCreatePage'))
const SiteDetailPage     = lazy(() => import('@/presentation/pages/SiteDetailPage'))

const Fallback = () => <LoadingSpinner text="페이지 로딩 중..." />

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <Suspense fallback={<Fallback />}><LoginPage /></Suspense>,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      { index: true,             element: <Suspense fallback={<Fallback />}><DashboardPage /></Suspense> },
      { path: 'history',         element: <Suspense fallback={<Fallback />}><HistoryPage /></Suspense> },
      { path: 'reports/:id',     element: <Suspense fallback={<Fallback />}><DashboardPage /></Suspense> },
      { path: 'storage',         element: <Suspense fallback={<Fallback />}><StoragePage /></Suspense> },
      { path: 'storage/preview', element: <Suspense fallback={<Fallback />}><StoragePreviewPage /></Suspense> },
      { path: 'sites',           element: <Suspense fallback={<Fallback />}><SiteManagementPage /></Suspense> },
      { path: 'sites/new',       element: <Suspense fallback={<Fallback />}><SiteCreatePage /></Suspense> },
      { path: 'sites/:id',       element: <Suspense fallback={<Fallback />}><SiteDetailPage /></Suspense> },
    ]
  },
  { path: '*', element: <Navigate to="/login" replace /> },
])
