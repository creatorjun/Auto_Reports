// frontend/src/presentation/context/ApplicationServicesContext.tsx
import { createContext, type ReactNode, useContext } from 'react'

import type { ApplicationServices } from '@/application/ports/ApplicationServices'

const ApplicationServicesContext = createContext<ApplicationServices | null>(null)

export function ApplicationServicesProvider({
  services,
  children,
}: {
  services: ApplicationServices
  children: ReactNode
}) {
  return (
    <ApplicationServicesContext.Provider value={services}>
      {children}
    </ApplicationServicesContext.Provider>
  )
}

export function useApplicationServices(): ApplicationServices {
  const services = useContext(ApplicationServicesContext)
  if (services === null) {
    throw new Error('Application services are not configured')
  }
  return services
}
