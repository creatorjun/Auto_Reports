// frontend/src/presentation/components/layout/MobileTabBar.tsx
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Gauge, History, Building2, HardDrive, Plus } from 'lucide-react'
import { useTrigger } from '@/presentation/hooks/useTrigger'
import { useUiStore } from '@/presentation/state/uiStore'
import LazyGenerateReportModal from '@/presentation/components/common/LazyGenerateReportModal'

const tabs = [
  { to: '/',        label: '대시보드', icon: <LayoutDashboard size={20} /> },
  { to: '/sla-dashboard', label: 'SLA 대시보드', icon: <Gauge size={20} /> },
  { to: '/history', label: '히스토리',   icon: <History        size={20} /> },
  { to: '/sites',   label: '사이트',     icon: <Building2      size={20} /> },
  { to: '/storage', label: '보관함',     icon: <HardDrive      size={20} /> },
]

export default function MobileTabBar() {
  const { isTriggerLoading } = useUiStore()
  const [showModal, setShowModal] = useState(false)

  useTrigger()

  return (
    <>
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-20
                   bg-white/90 backdrop-blur-xl border-t border-apple-divider/80
                   flex items-center justify-around px-1 h-16 safe-area-inset-bottom"
      >
        {tabs.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex min-w-0 flex-col items-center gap-1 px-1.5 py-1 rounded-xl transition-colors ${
                isActive ? 'text-brand-600' : 'text-apple-light'
              }`
            }
          >
            {icon}
            <span className="max-w-full truncate text-[10px] font-medium">{label}</span>
          </NavLink>
        ))}

        <button
          onClick={() => setShowModal(true)}
          disabled={isTriggerLoading}
          title="보고서 생성"
          className="flex min-w-0 flex-col items-center gap-1 px-1.5 py-1 rounded-xl
                     text-brand-600 transition-colors
                     disabled:opacity-40 disabled:cursor-not-allowed active:scale-95"
        >
          {isTriggerLoading ? (
            <span className="w-5 h-5 flex items-center justify-center">
              <span className="w-4 h-4 border-2 border-brand-600/30 border-t-brand-600 rounded-full animate-spin" />
            </span>
          ) : (
            <Plus size={20} />
          )}
          <span className="text-[10px] font-medium">
            {isTriggerLoading ? '생성 중' : '생성'}
          </span>
        </button>
      </nav>

      {showModal && <LazyGenerateReportModal onClose={() => setShowModal(false)} />}
    </>
  )
}
