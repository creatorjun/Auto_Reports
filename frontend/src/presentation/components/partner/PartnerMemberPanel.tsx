// frontend/src/presentation/components/partner/PartnerMemberPanel.tsx
import { useQuery } from '@tanstack/react-query'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import PartnerPanelHeader from './PartnerPanelHeader'
import {
  matchesPartnerSearch,
  normalizePartnerSearch,
  type PartnerMember,
} from '@/domain/Partner'

export default function PartnerMemberPanel({
  orgId,
  orgName,
  selectedAccountId,
  searchQuery,
  onSelect,
}: {
  orgId: string | null
  orgName: string
  selectedAccountId: string | null
  searchQuery: string
  onSelect: (member: PartnerMember | null) => void
}) {
  const { partners } = useApplicationServices()
  const { data: members = [], isLoading } = useQuery({
    queryKey: ['partner-members', orgId],
    queryFn: () => partners.getMembers(orgId!),
    enabled: !!orgId,
    staleTime: 5 * 60_000,
  })
  const normalizedQuery = normalizePartnerSearch(searchQuery)
  const organizationMatches = normalizedQuery.length > 0
    && matchesPartnerSearch(orgName, normalizedQuery)
  const filterMembers = normalizedQuery.length > 0 && !organizationMatches
  const visibleMembers = filterMembers
    ? members.filter((member) => matchesPartnerSearch(member.display_name, normalizedQuery))
    : members

  if (!orgId) {
    return (
      <div className="flex flex-col h-full">
        <PartnerPanelHeader title="멤버" />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-apple-light">← 조직을 선택하세요</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <PartnerPanelHeader title={orgName} count={visibleMembers.length} loading={isLoading} />
      <div className="flex-1 overflow-y-auto">
        {!filterMembers && (
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
        )}
        {visibleMembers.map((m) => (
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
        {!isLoading && visibleMembers.length === 0 && (
          <p className="px-4 py-6 text-sm text-apple-light text-center">
            {filterMembers ? '검색 결과 없음' : '멤버 없음'}
          </p>
        )}
      </div>
    </div>
  )
}
