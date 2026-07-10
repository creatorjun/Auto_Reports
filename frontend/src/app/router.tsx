// frontend/src/app/router.tsx
import { lazy, Suspense } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import Layout from '@/presentation/components/layout/Layout'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

const DashboardPage = lazy(() => import('@/presentation/pages/DashboardPage'))
const HistoryPage   = lazy(() => import('@/presentation/pages/HistoryPage'))
const StoragePage   = lazy(() => import('@/presentation/pages/StoragePage'))

const Fallback = () => <LoadingSpinner text="페이지 로딩 중..." />

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true,          element: <Suspense fallback={<Fallback />}><DashboardPage /></Suspense> },
      { path: 'history',      element: <Suspense fallback={<Fallback />}><HistoryPage /></Suspense> },
      { path: 'reports/:id',  element: <Suspense fallback={<Fallback />}><DashboardPage /></Suspense> },
      { path: 'storage',      element: <Suspense fallback={<Fallback />}><StoragePage /></Suspense> },
    ]
  }
])
