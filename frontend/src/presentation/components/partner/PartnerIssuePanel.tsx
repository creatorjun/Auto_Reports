// frontend/src/presentation/components/partner/PartnerIssuePanel.tsx
import { useQuery } from '@tanstack/react-query'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useJira } from '@/presentation/context/JiraContext'
import PartnerPanelHeader from './PartnerPanelHeader'
import PartnerIssueRow from './PartnerIssueRow'
import type { PartnerIssue } from '@/domain/Partner'

export default function PartnerIssuePanel({
  orgId,
  accountId,
  label,
}: {
  orgId: string | null
  accountId: string | null
  label: string
}) {
  const { partners } = useApplicationServices()
  const { jiraBrowse } = useJira()
  const byOrg = useQuery({
    queryKey: ['partner-issues-org', orgId],
    queryFn: () => partners.getIssuesByOrg(orgId!),
    enabled: !!orgId && !accountId,
    staleTime: 60_000,
  })

  const byMember = useQuery({
    queryKey: ['partner-issues-member', accountId],
    queryFn: () => partners.getIssuesByMember(accountId!),
    enabled: !!accountId,
    staleTime: 60_000,
  })

  const isLoading = accountId ? byMember.isLoading : byOrg.isLoading
  const issues: PartnerIssue[] = accountId
    ? (byMember.data ?? [])
    : (byOrg.data ?? [])

  if (!orgId) {
    return (
      <div className="flex flex-col h-full">
        <PartnerPanelHeader title="이슈" />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-apple-light">← 조직을 선택하세요</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <PartnerPanelHeader title={label} count={issues.length} loading={isLoading} />
      <div className="flex-1 overflow-y-auto">
        {issues.map((issue) => (
          <PartnerIssueRow key={issue.key} issue={issue} jiraBrowse={jiraBrowse} />
        ))}
        {!isLoading && issues.length === 0 && (
          <p className="px-4 py-8 text-sm text-apple-light text-center">이슈 없음</p>
        )}
      </div>
    </div>
  )
}
