// frontend/src/presentation/pages/PartnerManagementPage.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { partnerApi } from '@/infrastructure/api/partnerApi'
import type { PartnerOrg, PartnerMember, PartnerIssue } from '@/domain/Partner'

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

function PanelHeader({ title, count, loading }: { title: string; count?: number; loading?: boolean }) {
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-apple-divider">
      <span className="text-sm font-semibold text-apple-dark">{title}</span>
      {loading
        ? <span className="text-xs text-apple-light animate-pulse">로딩 중...</span>
        : count !== undefined && <span className="text-xs text-apple-light">{count}개</span>
      }
    </div>
  )
}

function OrgPanel({
  selectedOrgId,
  onSelect,
}: {
  selectedOrgId: string | null
  onSelect: (org: PartnerOrg) => void
}) {
  const { data: orgs = [], isLoading } = useQuery({
    queryKey: ['partner-orgs'],
    queryFn:  partnerApi.getOrganizations,
    staleTime: 5 * 60_000,
  })

  return (
    <div className="flex flex-col h-full">
      <PanelHeader title="파트너 조직" count={orgs.length} loading={isLoading} />
      <div className="flex-1 overflow-y-auto">
        {orgs.map((org) => (
          <button
            key={org.id}
            onClick={() => onSelect(org)}
            className={[
              'w-full text-left px-4 py-2.5 text-sm transition-colors border-b border-apple-divider/50',
              selectedOrgId === org.id
                ? 'bg-blue-50 text-blue-700 font-medium'
                : 'text-apple-dark hover:bg-apple-gray',
            ].join(' ')}
          >
            <div className="flex items-center justify-between">
              <span className="truncate">{org.name}</span>
              {selectedOrgId === org.id && (
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="flex-shrink-0 ml-2">
                  <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </div>
          </button>
        ))}
        {!isLoading && orgs.length === 0 && (
          <p className="px-4 py-6 text-sm text-apple-light text-center">조직 정보 없음</p>
        )}
      </div>
    </div>
  )
}

function MemberPanel({
  orgId,
  orgName,
  selectedAccountId,
  onSelect,
}: {
  orgId: string | null
  orgName: string
  selectedAccountId: string | null
  onSelect: (member: PartnerMember | null) => void
}) {
  const { data: members = [], isLoading } = useQuery({
    queryKey: ['partner-members', orgId],
    queryFn:  () => partnerApi.getMembers(orgId!),
    enabled:  !!orgId,
    staleTime: 5 * 60_000,
  })

  if (!orgId) {
    return (
      <div className="flex flex-col h-full">
        <PanelHeader title="멤버" />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-apple-light">← 조직을 선택하세요</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <PanelHeader title={orgName} count={members.length} loading={isLoading} />
      <div className="flex-1 overflow-y-auto">
        <button
          onClick={() => onSelect(null)}
          className={[
            'w-full text-left px-4 py-2.5 text-sm transition-colors border-b border-apple-divider/50',
            selectedAccountId === null
              ? 'bg-blue-50 text-blue-700 font-medium'
              : 'text-apple-dark hover:bg-apple-gray',
          ].join(' ')}
        >
          전체 이슈 보기
        </button>
        {members.map((m) => (
          <button
            key={m.account_id}
            onClick={() => onSelect(m)}
            className={[
              'w-full text-left px-4 py-2.5 transition-colors border-b border-apple-divider/50',
              selectedAccountId === m.account_id
                ? 'bg-blue-50'
                : 'hover:bg-apple-gray',
            ].join(' ')}
          >
            <p className={[
              'text-sm truncate',
              selectedAccountId === m.account_id ? 'text-blue-700 font-medium' : 'text-apple-dark',
            ].join(' ')}>
              {m.display_name}
            </p>
            {m.email && (
              <p className="text-xs text-apple-light truncate mt-0.5">{m.email}</p>
            )}
          </button>
        ))}
        {!isLoading && members.length === 0 && (
          <p className="px-4 py-6 text-sm text-apple-light text-center">멤버 정보 없음</p>
        )}
      </div>
    </div>
  )
}

function IssuePanel({
  orgId,
  accountId,
  label,
}: {
  orgId: string | null
  accountId: string | null
  label: string
}) {
  const byOrg = useQuery({
    queryKey: ['partner-issues-org', orgId],
    queryFn:  () => partnerApi.getIssuesByOrg(orgId!),
    enabled:  !!orgId && !accountId,
    staleTime: 60_000,
  })

  const byMember = useQuery({
    queryKey: ['partner-issues-member', accountId],
    queryFn:  () => partnerApi.getIssuesByMember(accountId!),
    enabled:  !!accountId,
    staleTime: 60_000,
  })

  const isLoading = accountId ? byMember.isLoading : byOrg.isLoading
  const issues: PartnerIssue[] = accountId
    ? (byMember.data ?? [])
    : (byOrg.data ?? [])

  if (!orgId) {
    return (
      <div className="flex flex-col h-full">
        <PanelHeader title="이슈" />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-apple-light">← 조직을 선택하세요</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <PanelHeader title={label} count={issues.length} loading={isLoading} />
      <div className="flex-1 overflow-y-auto">
        {issues.map((issue) => (
          <div
            key={issue.key}
            className="px-4 py-3 border-b border-apple-divider/50 hover:bg-apple-gray transition-colors"
          >
            <div className="flex items-start justify-between gap-2 mb-1">
              <a
                href={`https://seculayer.atlassian.net/browse/${issue.key}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs font-mono text-blue-600 hover:underline flex-shrink-0"
              >
                {issue.key}
              </a>
              <ElapsedBadge days={issue.elapsed_days} />
            </div>
            <p className="text-sm text-apple-dark leading-snug mb-1.5 line-clamp-2">
              {issue.summary}
            </p>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={[
                'text-xs px-2 py-0.5 rounded-full font-medium',
                STAGE_COLOR[issue.stage_index] ?? 'bg-gray-100 text-gray-500',
              ].join(' ')}>
                {issue.status}
              </span>
              <span className="text-xs text-apple-light">{issue.type}</span>
              {issue.tac_team && issue.tac_team !== '미지정' && (
                <span className="text-xs text-apple-light">담당: {issue.tac_team}</span>
              )}
            </div>
            <p className="text-xs text-apple-light mt-1">{issue.created}</p>
          </div>
        ))}
        {!isLoading && issues.length === 0 && (
          <p className="px-4 py-8 text-sm text-apple-light text-center">이슈 없음</p>
        )}
      </div>
    </div>
  )
}

export default function PartnerManagementPage() {
  const [selectedOrg,    setSelectedOrg]    = useState<PartnerOrg | null>(null)
  const [selectedMember, setSelectedMember] = useState<PartnerMember | null>(null)

  const handleSelectOrg = (org: PartnerOrg) => {
    if (selectedOrg?.id === org.id) return
    setSelectedOrg(org)
    setSelectedMember(null)
  }

  const handleSelectMember = (member: PartnerMember | null) => {
    setSelectedMember(member)
  }

  const issueLabel = selectedMember
    ? `${selectedMember.display_name} 이슈`
    : selectedOrg
    ? `${selectedOrg.name} 전체 이슈`
    : '이슈'

  return (
    <div className="flex flex-col w-full h-full px-6 py-6 gap-4">
      <h1 className="text-xl font-semibold text-apple-dark flex-shrink-0">파트너 관리</h1>
      <div className="flex-1 grid grid-cols-[220px_220px_1fr] gap-3 min-h-0">
        <div className="bg-white border border-apple-divider rounded-2xl shadow-sm overflow-hidden">
          <OrgPanel
            selectedOrgId={selectedOrg?.id ?? null}
            onSelect={handleSelectOrg}
          />
        </div>
        <div className="bg-white border border-apple-divider rounded-2xl shadow-sm overflow-hidden">
          <MemberPanel
            orgId={selectedOrg?.id ?? null}
            orgName={selectedOrg?.name ?? ''}
            selectedAccountId={selectedMember?.account_id ?? null}
            onSelect={handleSelectMember}
          />
        </div>
        <div className="bg-white border border-apple-divider rounded-2xl shadow-sm overflow-hidden">
          <IssuePanel
            orgId={selectedOrg?.id ?? null}
            accountId={selectedMember?.account_id ?? null}
            label={issueLabel}
          />
        </div>
      </div>
    </div>
  )
}
