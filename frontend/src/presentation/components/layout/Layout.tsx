// frontend/src/presentation/components/layout/Layout.tsx
import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { JiraProvider } from '@/presentation/context/JiraContext'
import { ReportGenerationProvider } from '@/presentation/context/ReportGenerationContext'
import Header from './Header'
import Sidebar from './Sidebar'
import MobileTabBar from './MobileTabBar'

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false)
  return (
    <JiraProvider>
      <ReportGenerationProvider>
      <div className="relative flex h-screen bg-apple-bg overflow-hidden">
        <div className="hidden xl:flex">
          <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
        </div>
        <div className="flex min-h-0 flex-col flex-1 min-w-0">
          <Header />
          <main className="min-h-0 flex-1 overflow-y-auto px-4 md:px-6 3xl:px-8 py-4 md:py-6 3xl:py-8 pb-24 xl:pb-6 3xl:pb-8">
            <Outlet />
          </main>
        </div>
        <MobileTabBar />
      </div>
      </ReportGenerationProvider>
    </JiraProvider>
  )
}
