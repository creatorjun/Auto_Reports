// frontend/src/presentation/pages/PartnerManagementPage.tsx
import { useState } from 'react'
import type { PartnerOrg, PartnerMember } from '@/domain/Partner'
import PartnerOrgPanel from '@/presentation/components/partner/PartnerOrgPanel'
import PartnerMemberPanel from '@/presentation/components/partner/PartnerMemberPanel'
import PartnerIssuePanel from '@/presentation/components/partner/PartnerIssuePanel'

export default function PartnerManagementPage() {
  const [organizationQuery, setOrganizationQuery] = useState('')
  const [memberQuery,       setMemberQuery]       = useState('')
  const [issueQuery,        setIssueQuery]        = useState('')
  const [selectedOrg,       setSelectedOrg]       = useState<PartnerOrg | null>(null)
  const [selectedMember,    setSelectedMember]    = useState<PartnerMember | null>(null)

  const handleSelectOrg = (org: PartnerOrg) => {
    if (selectedOrg?.id === org.id) return
    setSelectedOrg(org)
    setSelectedMember(null)
  }

  const issueLabel = selectedMember
    ? `${selectedMember.display_name} 이슈`
    : selectedOrg
    ? `${selectedOrg.name} 전체 이슈`
    : '이슈'

  return (
    <div className="flex flex-col w-full h-full px-6 py-6 gap-4">
      <div className="flex-shrink-0">
        <div>
          <h1 className="text-xl font-semibold text-apple-dark">파트너 관리</h1>
          <p className="mt-1 text-xs text-apple-light">조직·멤버·이슈를 각 영역에서 개별로 필터링할 수 있습니다.</p>
        </div>
      </div>
      <div className="flex-1 grid grid-cols-[220px_220px_1fr] gap-3 min-h-0">
        <div className="bg-apple-surface border border-apple-divider rounded-2xl shadow-sm overflow-hidden">
          <PartnerOrgPanel
            selectedOrgId={selectedOrg?.id ?? null}
            searchQuery={organizationQuery}
            onSearchChange={setOrganizationQuery}
            onSelect={handleSelectOrg}
          />
        </div>
        <div className="bg-apple-surface border border-apple-divider rounded-2xl shadow-sm overflow-hidden">
          <PartnerMemberPanel
            orgId={selectedOrg?.id ?? null}
            orgName={selectedOrg?.name ?? ''}
            selectedAccountId={selectedMember?.account_id ?? null}
            searchQuery={memberQuery}
            onSearchChange={setMemberQuery}
            onSelect={setSelectedMember}
          />
        </div>
        <div className="bg-apple-surface border border-apple-divider rounded-2xl shadow-sm overflow-hidden">
          <PartnerIssuePanel
            orgId={selectedOrg?.id ?? null}
            accountId={selectedMember?.account_id ?? null}
            label={issueLabel}
            searchQuery={issueQuery}
            onSearchChange={setIssueQuery}
          />
        </div>
      </div>
    </div>
  )
}
