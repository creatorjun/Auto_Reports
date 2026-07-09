// frontend/src/app/context/JiraContext.tsx
import { createContext, useContext, useMemo } from 'react'
import { useConfig } from '@/infrastructure/hooks/useConfig'
import { DEFAULT_JIRA_BASE_URL } from '@/shared/constants'

interface JiraContextValue {
  jiraBase: string
  jiraBrowse: string
}

const JiraContext = createContext<JiraContextValue>({
  jiraBase:   DEFAULT_JIRA_BASE_URL,
  jiraBrowse: `${DEFAULT_JIRA_BASE_URL}/browse`,
})

export function JiraProvider({ children }: { children: React.ReactNode }) {
  const { data: config } = useConfig()
  const value = useMemo(() => {
    const base = config?.jira_base_url ?? DEFAULT_JIRA_BASE_URL
    return { jiraBase: base, jiraBrowse: `${base}/browse` }
  }, [config?.jira_base_url])

  return <JiraContext.Provider value={value}>{children}</JiraContext.Provider>
}

export const useJira = () => useContext(JiraContext)
