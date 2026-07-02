import { createBrowserRouter } from 'react-router-dom'
import DashboardPage from '@/presentation/pages/DashboardPage'
import HistoryPage from '@/presentation/pages/HistoryPage'
import Layout from '@/presentation/components/layout/Layout'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'history', element: <HistoryPage /> },
      { path: 'reports/:id', element: <DashboardPage /> }
    ]
  }
])
