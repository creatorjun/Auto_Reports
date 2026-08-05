// frontend/src/presentation/pages/PartnerManagementPage.tsx
import { useState } from 'react'
import type { PartnerOrg, PartnerMember } from '@/domain/Partner'
import PartnerOrgPanel from '@/presentation/components/partner/PartnerOrgPanel'
import PartnerMemberPanel from '@/presentation/components/partner/PartnerMemberPanel'
import PartnerIssuePanel from '@/presentation/components/partner/PartnerIssuePanel'

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
          <PartnerOrgPanel
            selectedOrgId={selectedOrg?.id ?? null}
            onSelect={handleSelectOrg}
          />
        </div>
        <div className="bg-white border border-apple-divider rounded-2xl shadow-sm overflow-hidden">
          <PartnerMemberPanel
            orgId={selectedOrg?.id ?? null}
            orgName={selectedOrg?.name ?? ''}
            selectedAccountId={selectedMember?.account_id ?? null}
            onSelect={handleSelectMember}
          />
        </div>
        <div className="bg-white border border-apple-divider rounded-2xl shadow-sm overflow-hidden">
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
