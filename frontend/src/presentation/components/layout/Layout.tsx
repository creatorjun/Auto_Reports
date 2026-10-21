// frontend/src/presentation/components/layout/Layout.tsx
import { useEffect, useRef, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { JiraProvider } from '@/presentation/context/JiraContext'
import { ReportGenerationProvider } from '@/presentation/context/ReportGenerationContext'
import Header from './Header'
import Sidebar from './Sidebar'
import MobileTabBar from './MobileTabBar'

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false)
  const [accountTrigger, setAccountTrigger] = useState<HTMLButtonElement | null>(null)
  const sidebar = useRef<HTMLDivElement>(null)
  const { pathname } = useLocation()
  useEffect(() => { setAccountTrigger(null) }, [pathname])
  useEffect(() => {
    if (!accountTrigger) return
    sidebar.current?.querySelector('button')?.focus()
    return () => { if (accountTrigger.isConnected) accountTrigger.focus() }
  }, [accountTrigger])
  return (
    <JiraProvider>
      <ReportGenerationProvider>
      <div className="relative flex h-screen bg-apple-bg overflow-hidden">
        {accountTrigger && <button type="button" aria-label="계정 메뉴 바깥 영역 닫기" onClick={() => setAccountTrigger(null)} className="fixed inset-0 z-40 bg-black/20 xl:hidden" />}
        <div ref={sidebar} className={accountTrigger ? 'fixed inset-y-0 left-0 z-40 flex max-w-[calc(100vw-2rem)] xl:static xl:max-w-none' : 'hidden xl:flex'} onKeyDown={(event) => {
          if (event.key === 'Escape' && !(event.target as HTMLElement).closest('[role="dialog"]')) setAccountTrigger(null)
        }}>
          <Sidebar collapsed={accountTrigger ? false : collapsed} setCollapsed={setCollapsed} mobileOpen={!!accountTrigger} onCloseMobile={() => setAccountTrigger(null)} />
        </div>
        <div className="flex min-h-0 flex-col flex-1 min-w-0">
          <Header />
          <main className="min-h-0 flex-1 overflow-y-auto px-4 md:px-6 3xl:px-8 py-4 md:py-6 3xl:py-8 pb-24 xl:pb-6 3xl:pb-8">
            <Outlet />
          </main>
        </div>
        <MobileTabBar onOpenAccount={setAccountTrigger} accountExpanded={!!accountTrigger} />
      </div>
      </ReportGenerationProvider>
    </JiraProvider>
  )
}
