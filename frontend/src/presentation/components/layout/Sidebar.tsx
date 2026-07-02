// frontend/src/presentation/components/layout/Sidebar.tsx
import { NavLink } from 'react-router-dom'

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

export default function Sidebar() {
  return (
    <aside className="w-56 bg-white border-r border-apple-divider/80 flex flex-col py-5 px-3 gap-0.5">
      <p className="text-[10px] font-semibold text-apple-light uppercase tracking-widest px-3 mb-2 mt-1">
        메뉴
      </p>
      {links.map(({ to, icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `nav-link ${isActive ? 'nav-link-active' : ''}`
          }
        >
          {icon}
          <span>{label}</span>
        </NavLink>
      ))}
    </aside>
  )
}
