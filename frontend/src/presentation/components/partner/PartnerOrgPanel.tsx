// frontend/src/presentation/components/partner/PartnerOrgPanel.tsx
import { useQuery } from '@tanstack/react-query'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import PartnerPanelHeader from './PartnerPanelHeader'
import PartnerSearchInput from './PartnerSearchInput'
import {
  matchesPartnerSearch,
  normalizePartnerSearch,
  sortPartnerOrganizationsByIssueCount,
  type PartnerOrg,
} from '@/domain/Partner'

export default function PartnerOrgPanel({
  selectedOrgId,
  searchQuery,
  onSearchChange,
  onSelect,
}: {
  selectedOrgId: string | null
  searchQuery: string
  onSearchChange: (value: string) => void
  onSelect: (org: PartnerOrg) => void
}) {
  const { partners } = useApplicationServices()
  const { data: orgs = [], isLoading } = useQuery({
    queryKey: ['partner-orgs'],
    queryFn: partners.getOrganizations,
    staleTime: 5 * 60_000,
  })
  const normalizedQuery = normalizePartnerSearch(searchQuery)
  const visibleOrgs = sortPartnerOrganizationsByIssueCount(
    normalizedQuery
      ? orgs.filter((org) => matchesPartnerSearch(org.name, normalizedQuery))
      : orgs,
  )

  return (
    <div className="flex flex-col h-full">
      <PartnerPanelHeader title="파트너 조직" count={visibleOrgs.length} loading={isLoading} />
      <div className="border-b border-apple-divider px-3 py-2.5">
        <PartnerSearchInput
          value={searchQuery}
          onChange={onSearchChange}
          placeholder="파트너 조직 필터"
          ariaLabel="파트너 조직 필터"
        />
      </div>
      <div className="flex-1 overflow-y-auto">
        {visibleOrgs.map((org) => (
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
            <div className="flex items-center">
              <span className="min-w-0 truncate">{org.name}</span>
              <span className="ml-1 flex-shrink-0 tabular-nums text-apple-light">({org.issue_count.toLocaleString('ko-KR')})</span>
              {selectedOrgId === org.id && (
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="ml-auto flex-shrink-0 pl-2 box-content">
                  <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </div>
          </button>
        ))}
        {!isLoading && visibleOrgs.length === 0 && (
          <p className="px-4 py-6 text-sm text-apple-light text-center">
            {normalizedQuery ? '검색 결과 없음' : '조직 정보 없음'}
          </p>
        )}
      </div>
    </div>
  )
}
