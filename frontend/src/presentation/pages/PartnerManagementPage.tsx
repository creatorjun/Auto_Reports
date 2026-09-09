// frontend/src/presentation/pages/PartnerManagementPage.tsx
import { useMemo, useState } from 'react'
import type { PartnerOrg, PartnerMember } from '@/domain/Partner'
import type { Semester } from '@/domain/Dashboard'
import PartnerOrgPanel from '@/presentation/components/partner/PartnerOrgPanel'
import PartnerMemberPanel from '@/presentation/components/partner/PartnerMemberPanel'
import PartnerIssuePanel from '@/presentation/components/partner/PartnerIssuePanel'
import IssueTypeFilter from '@/presentation/components/common/IssueTypeFilter'
import { useLatestReport } from '@/presentation/hooks/useReport'
import { buildDashboardData } from '@/presentation/hooks/useDashboardData'

export default function PartnerManagementPage() {
  const [organizationQuery, setOrganizationQuery] = useState('')
  const [memberQuery,       setMemberQuery]       = useState('')
  const [issueQuery,        setIssueQuery]        = useState('')
  const [selectedOrg,       setSelectedOrg]       = useState<PartnerOrg | null>(null)
  const [selectedMember,    setSelectedMember]    = useState<PartnerMember | null>(null)
  const [selectedIssueTypes, setSelectedIssueTypes] = useState<Set<string> | null>(null)
  const [selectedSemester, setSelectedSemester] = useState<Semester | null>(null)
  const latestReport = useLatestReport()
  const reportFilter = useMemo(
    () => latestReport.data ? buildDashboardData(latestReport.data).filter : null,
    [latestReport.data],
  )
  const issueTypes = reportFilter?.issueTypes ?? []
  const reportYear = reportFilter?.reportYear ?? new Date().getFullYear()
  const supportsIssueTypeFiltering = reportFilter?.supportsIssueTypeFiltering ?? false
  const supportsSemesterFiltering = reportFilter?.supportsSemesterFiltering ?? false
  const effectiveIssueTypes = supportsIssueTypeFiltering ? selectedIssueTypes : null
  const effectiveSemester = supportsSemesterFiltering ? selectedSemester : null

  const handleSelectOrg = (org: PartnerOrg) => {
    if (selectedOrg?.id === org.id) return
    setSelectedOrg(org)
    setSelectedMember(null)
  }

  const handleIssueTypeToggle = (issueType: string) => {
    setSelectedIssueTypes((current) => {
      const next = new Set(current ?? issueTypes)
      if (next.has(issueType)) next.delete(issueType)
      else next.add(issueType)
      return next.size === issueTypes.length ? null : next
    })
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
          <p className="mt-1 text-xs text-apple-light">요청 유형·조회 기간은 이슈에 공통 적용되며, 조직·멤버·이슈 검색은 각 영역에서 개별로 동작합니다.</p>
        </div>
      </div>
      {latestReport.isLoading ? (
        <div className="card flex min-h-24 items-center justify-center text-sm text-apple-light animate-pulse">필터 불러오는 중...</div>
      ) : (
        <IssueTypeFilter
          issueTypes={issueTypes}
          selectedTypes={selectedIssueTypes}
          selectedSemester={selectedSemester}
          supported={supportsIssueTypeFiltering}
          semesterSupported={supportsSemesterFiltering}
          onToggle={handleIssueTypeToggle}
          onSemesterChange={setSelectedSemester}
          onReset={() => {
            setSelectedIssueTypes(null)
            setSelectedSemester(null)
          }}
        />
      )}
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
            issueTypes={issueTypes}
            selectedIssueTypes={effectiveIssueTypes}
            selectedSemester={effectiveSemester}
            reportYear={reportYear}
          />
        </div>
      </div>
    </div>
  )
}
