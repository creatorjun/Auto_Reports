import { NavLink } from 'react-router-dom'

const links = [
  { to: '/',        icon: '📊', label: '대시보드' },
  { to: '/history', icon: '🗂️', label: '보고서 히스토리' }
]

export default function Sidebar() {
  return (
    <aside className="w-52 bg-white border-r border-gray-200 flex flex-col py-6 px-3 gap-1">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 mb-3">메뉴</p>
      {links.map(({ to, icon, label }) => (
        <NavLink
          key={to} to={to} end={to === '/'}
          className={({ isActive }) =>
            `flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
              isActive ? 'bg-brand-50 text-brand-700' : 'text-gray-600 hover:bg-gray-50'
            }`
          }
        >
          <span>{icon}</span>{label}
        </NavLink>
      ))}
    </aside>
  )
}
