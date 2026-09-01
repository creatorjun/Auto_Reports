// frontend/src/presentation/pages/PartnerManagementPage.tsx
import { useState } from 'react'
import type { PartnerOrg, PartnerMember } from '@/domain/Partner'
import PartnerOrgPanel from '@/presentation/components/partner/PartnerOrgPanel'
import PartnerMemberPanel from '@/presentation/components/partner/PartnerMemberPanel'
import PartnerIssuePanel from '@/presentation/components/partner/PartnerIssuePanel'
import PartnerSearchInput from '@/presentation/components/partner/PartnerSearchInput'

export default function PartnerManagementPage() {
  const [searchQuery,     setSearchQuery]     = useState('')
  const [selectedOrg,    setSelectedOrg]    = useState<PartnerOrg | null>(null)
  const [selectedMember, setSelectedMember] = useState<PartnerMember | null>(null)

  const handleSelectOrg = (org: PartnerOrg) => {
    if (selectedOrg?.id === org.id) return
    setSelectedOrg(org)
    setSelectedMember(null)
  }

  const handleSearchChange = (value: string) => {
    setSearchQuery(value)
    setSelectedOrg(null)
    setSelectedMember(null)
  }

  const issueLabel = selectedMember
    ? `${selectedMember.display_name} 이슈`
    : selectedOrg
    ? `${selectedOrg.name} 전체 이슈`
    : '이슈'

  return (
    <div className="flex flex-col w-full h-full px-6 py-6 gap-4">
      <div className="flex flex-shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-apple-dark">파트너 관리</h1>
          <p className="mt-1 text-xs text-apple-light">파트너사명과 직원명을 한 번에 검색할 수 있습니다.</p>
        </div>
        <div className="w-full sm:max-w-sm">
          <PartnerSearchInput value={searchQuery} onChange={handleSearchChange} />
        </div>
      </div>
      <div className="flex-1 grid grid-cols-[220px_220px_1fr] gap-3 min-h-0">
        <div className="bg-apple-surface border border-apple-divider rounded-2xl shadow-sm overflow-hidden">
          <PartnerOrgPanel
            selectedOrgId={selectedOrg?.id ?? null}
            searchQuery={searchQuery}
            onSelect={handleSelectOrg}
          />
        </div>
        <div className="bg-apple-surface border border-apple-divider rounded-2xl shadow-sm overflow-hidden">
          <PartnerMemberPanel
            orgId={selectedOrg?.id ?? null}
            orgName={selectedOrg?.name ?? ''}
            selectedAccountId={selectedMember?.account_id ?? null}
            searchQuery={searchQuery}
            onSelect={setSelectedMember}
          />
        </div>
        <div className="bg-apple-surface border border-apple-divider rounded-2xl shadow-sm overflow-hidden">
          <PartnerIssuePanel
            orgId={selectedOrg?.id ?? null}
            accountId={selectedMember?.account_id ?? null}
            label={issueLabel}
          />
        </div>
      </div>
    </div>
  )
}
