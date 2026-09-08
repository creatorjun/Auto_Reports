// frontend/src/presentation/context/DashboardExportContext.tsx
import { createContext, useContext } from 'react'

const DashboardExportContext = createContext(false)

export function DashboardExportProvider({ children }: { children: React.ReactNode }) {
  return <DashboardExportContext.Provider value={true}>{children}</DashboardExportContext.Provider>
}

export const useDashboardExportMode = () => useContext(DashboardExportContext)
