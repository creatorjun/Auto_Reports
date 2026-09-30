// frontend/src/presentation/hooks/useIssueManagement.ts
import { useQuery } from '@tanstack/react-query'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'

export function useIssueManagement() {
  const { issueManagement } = useApplicationServices()
  return useQuery({
    queryKey: ['issue-management', 'TACEA'],
    queryFn: issueManagement.getIssues,
    staleTime: 0,
    refetchInterval: (query) => query.state.data?.refreshing ? 2000 : 30000,
    refetchOnWindowFocus: true,
  })
}
