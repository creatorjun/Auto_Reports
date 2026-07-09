// frontend/src/presentation/components/layout/Layout.tsx
import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Header from './Header'
import Sidebar from './Sidebar'
import MobileTabBar from './MobileTabBar'

export default function Layout() {
  const [collapsed, setCollapsed] = useState(true)

  return (
    <div className="flex h-screen overflow-hidden bg-white">
      <div className="hidden md:flex flex-shrink-0">
        <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      </div>

      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        <Header />
        <main className="flex-1 overflow-y-auto bg-apple-gray/40">
          <div className="w-full max-w-content mx-auto
                          px-4 py-4
                          md:px-6 md:py-6
                          xl:px-8 xl:py-8
                          3xl:px-12 3xl:py-10
                          pb-20 md:pb-6 xl:pb-8 3xl:pb-10">
            <Outlet />
          </div>
        </main>
      </div>

      <div className="md:hidden">
        <MobileTabBar />
      </div>
    </div>
  )
}
