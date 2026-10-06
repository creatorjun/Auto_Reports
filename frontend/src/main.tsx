// frontend/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './app/App'
import './presentation/styles/palette.css'
import './presentation/styles/index.css'
import { authApi } from '@/infrastructure/api/authApi'
import { partnerApi } from '@/infrastructure/api/partnerApi'
import { reportApi } from '@/infrastructure/api/reportApi'
import { searchApi } from '@/infrastructure/api/searchApi'
import { siteApi } from '@/infrastructure/api/siteApi'
import { slaDashboardApi } from '@/infrastructure/api/slaDashboardApi'
import { issueManagementApi } from '@/infrastructure/api/issueManagementApi'
import { dashboardPdfExporter } from '@/infrastructure/export/dashboardPdfExporter'
import { dashboardExcelExporter } from '@/infrastructure/export/dashboardExcelExporter'
import { storageApi } from '@/infrastructure/api/storageApi'
import { filePreviewParser } from '@/infrastructure/preview/filePreviewParser'
import { configureHttpClient } from '@/infrastructure/api/client'
import { ApplicationServicesProvider } from '@/presentation/context/ApplicationServicesContext'
import { useAuthStore } from '@/presentation/state/authStore'
import { applyTheme, useThemeStore } from '@/presentation/state/themeStore'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 2, staleTime: 1000 * 60 * 5 } }
})

configureHttpClient({
  getAccessToken: () => useAuthStore.getState().accessToken,
  getUsername: () => useAuthStore.getState().username,
  setAuth: (token, username) => useAuthStore.getState().setAuth(token, username),
  clearAuth: () => useAuthStore.getState().clearAuth(),
  redirectToLogin: () => {
    window.location.href = '/login'
  },
})

const services = {
  previewParser: filePreviewParser,
  dashboardExport: { ...dashboardPdfExporter, ...dashboardExcelExporter },
  auth: authApi,
  reports: reportApi,
  sites: siteApi,
  storage: storageApi,
  partners: partnerApi,
  search: searchApi,
  slaDashboard: slaDashboardApi,
  issueManagement: issueManagementApi,
}

applyTheme(useThemeStore.getState().theme)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ApplicationServicesProvider services={services}>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </ApplicationServicesProvider>
  </React.StrictMode>
)
