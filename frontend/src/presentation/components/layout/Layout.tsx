// frontend/src/presentation/components/layout/Layout.tsx
import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Header from './Header'
import Sidebar from './Sidebar'
import MobileTabBar from './MobileTabBar'

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="flex h-screen overflow-hidden bg-white">
      <div className="hidden md:flex">
        <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      </div>

      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        <Header />
        <main className="flex-1 overflow-y-auto bg-apple-gray/40 p-4 md:p-7 pb-20 md:pb-7">
          <Outlet />
        </main>
      </div>

      <div className="md:hidden">
        <MobileTabBar />
      </div>
    </div>
  )
}
