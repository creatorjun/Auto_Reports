// frontend/src/presentation/components/layout/Sidebar.tsx
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import TriggerButton from '../common/TriggerButton'

const links = [
  {
    to: '/',
    label: '대시보드',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <rect x="1" y="1" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.9" />
        <rect x="9" y="1" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.5" />
        <rect x="1" y="9" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.5" />
        <rect x="9" y="9" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.3" />
      </svg>
    )
  },
  {
    to: '/history',
    label: '보고서 히스토리',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <rect x="2" y="2" width="12" height="2" rx="1" fill="currentColor" />
        <rect x="2" y="6" width="9" height="2" rx="1" fill="currentColor" opacity="0.6" />
        <rect x="2" y="10" width="11" height="2" rx="1" fill="currentColor" opacity="0.6" />
        <rect x="2" y="14" width="6" height="1.5" rx="0.75" fill="currentColor" opacity="0.4" />
      </svg>
    )
  }
]

function CollapseIcon({ collapsed }: { collapsed: boolean }) {
  return collapsed ? (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ) : (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={`${
        collapsed ? 'w-14' : 'w-56'
      } bg-white border-r border-apple-divider/80 flex flex-col py-5 px-2 transition-all duration-250 ease-in-out`}
    >
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center w-8 h-8 rounded-xl text-apple-light hover:bg-apple-gray hover:text-apple-dark transition-all duration-200 mb-2 self-end"
        title={collapsed ? '사이드바 펼치기' : '사이드바 접기'}
      >
        <CollapseIcon collapsed={collapsed} />
      </button>

      <div className="flex flex-col gap-0.5 flex-1">
        {links.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              `nav-link ${
                collapsed ? 'justify-center px-0' : ''
              } ${isActive ? 'nav-link-active' : ''}`
            }
          >
            <span className="flex-shrink-0">{icon}</span>
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </div>

      <div className={`mt-auto pt-4 border-t border-apple-divider/60 ${
        collapsed ? 'flex justify-center' : ''
      }`}>
        <TriggerButton collapsed={collapsed} />
      </div>
    </aside>
  )
}
