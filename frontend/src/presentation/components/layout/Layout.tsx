// frontend/src/presentation/components/layout/Layout.tsx
import { Outlet } from 'react-router-dom'
import Header from './Header'
import Sidebar from './Sidebar'

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-white">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto bg-apple-gray/40 p-7">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
