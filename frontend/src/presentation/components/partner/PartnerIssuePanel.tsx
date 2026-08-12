// frontend/src/presentation/components/partner/PartnerIssuePanel.tsx
import { useQuery } from '@tanstack/react-query'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import PartnerPanelHeader from './PartnerPanelHeader'
import type { PartnerIssue } from '@/domain/Partner'

const STAGE_COLOR: Record<number, string> = {
  0: 'bg-gray-100 text-gray-500',
  1: 'bg-blue-100 text-blue-700',
  2: 'bg-yellow-100 text-yellow-700',
  3: 'bg-orange-100 text-orange-700',
  4: 'bg-green-100 text-green-700',
  5: 'bg-purple-100 text-purple-700',
}

function ElapsedBadge({ days }: { days: number }) {
  const color =
    days >= 14 ? 'text-red-500' :
    days >= 7  ? 'text-orange-500' :
                 'text-apple-light'
  return <span className={`text-xs font-medium ${color}`}>{days}일</span>
}

function IssueRow({ issue }: { issue: PartnerIssue }) {
  return (
    <a
      href={issue.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-3 px-4 py-3 border-b border-apple-divider/50 hover:bg-apple-gray transition-colors"
    >
      <span className={`mt-0.5 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold flex-shrink-0 ${STAGE_COLOR[issue.stage] ?? STAGE_COLOR[0]}`}>
        S{issue.stage}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-apple-dark truncate">{issue.summary}</p>
        <p className="text-xs text-apple-light mt-0.5">{issue.key}</p>
      </div>
      <ElapsedBadge days={issue.elapsed_days} />
    </a>
  )
}

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
          <IssueRow key={issue.key} issue={issue} />
        ))}
        {!isLoading && issues.length === 0 && (
          <p className="px-4 py-8 text-sm text-apple-light text-center">이슈 없음</p>
        )}
      </div>
    </div>
  )
}
