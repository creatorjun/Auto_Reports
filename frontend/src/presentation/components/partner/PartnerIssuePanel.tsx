// frontend/src/presentation/components/partner/PartnerIssuePanel.tsx
import { useQuery } from '@tanstack/react-query'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useJira } from '@/presentation/context/JiraContext'
import PartnerPanelHeader from './PartnerPanelHeader'
import PartnerIssueRow from './PartnerIssueRow'
import PartnerSearchInput from './PartnerSearchInput'
import {
  matchesPartnerSearch,
  normalizePartnerSearch,
  type PartnerIssue,
} from '@/domain/Partner'

export default function PartnerIssuePanel({
  orgId,
  accountId,
  label,
  searchQuery,
  onSearchChange,
}: {
  orgId: string | null
  accountId: string | null
  label: string
  searchQuery: string
  onSearchChange: (value: string) => void
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
  const normalizedQuery = normalizePartnerSearch(searchQuery)
  const visibleIssues = normalizedQuery
    ? issues.filter((issue) => (
        matchesPartnerSearch(issue.key, normalizedQuery)
        || matchesPartnerSearch(issue.summary, normalizedQuery)
      ))
    : issues

  if (!orgId) {
    return (
      <div className="flex flex-col h-full">
        <PartnerPanelHeader title="이슈" />
        <div className="border-b border-apple-divider px-3 py-2.5">
          <PartnerSearchInput
            value={searchQuery}
            onChange={onSearchChange}
            placeholder="이슈 번호·제목 필터"
            ariaLabel="이슈 필터"
            disabled
          />
        </div>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-apple-light">← 조직을 선택하세요</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <PartnerPanelHeader title={label} count={visibleIssues.length} loading={isLoading} />
      <div className="border-b border-apple-divider px-3 py-2.5">
        <PartnerSearchInput
          value={searchQuery}
          onChange={onSearchChange}
          placeholder="이슈 번호·제목 필터"
          ariaLabel="이슈 필터"
        />
      </div>
      <div className="flex-1 overflow-y-auto">
        {visibleIssues.map((issue) => (
          <PartnerIssueRow key={issue.key} issue={issue} jiraBrowse={jiraBrowse} />
        ))}
        {!isLoading && visibleIssues.length === 0 && (
          <p className="px-4 py-8 text-sm text-apple-light text-center">
            {normalizedQuery ? '검색 결과 없음' : '이슈 없음'}
          </p>
        )}
      </div>
    </div>
  )
}
