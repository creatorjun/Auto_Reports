// frontend/src/presentation/pages/PartnerManagementPage.tsx
import { useCallback, useMemo, useState } from 'react'
import type { PartnerOrg, PartnerMember } from '@/domain/Partner'
import type { Semester } from '@/domain/Dashboard'
import PartnerOrgPanel from '@/presentation/components/partner/PartnerOrgPanel'
import PartnerMemberPanel from '@/presentation/components/partner/PartnerMemberPanel'
import PartnerIssuePanel from '@/presentation/components/partner/PartnerIssuePanel'
import IssueTypeFilter from '@/presentation/components/common/IssueTypeFilter'
import { useLatestReport } from '@/presentation/hooks/useReport'
import { resolveDashboardFilterContract } from '@/application/services/dashboardData'
import { sortDashboardStatuses } from '@/domain/DashboardStatusPolicy'
import { isLicenseIssueType } from '@/domain/DashboardIssueTypePolicy'

export default function PartnerManagementPage() {
  const [organizationQuery, setOrganizationQuery] = useState('')
  const [memberQuery,       setMemberQuery]       = useState('')
  const [issueQuery,        setIssueQuery]        = useState('')
  const [selectedOrg,       setSelectedOrg]       = useState<PartnerOrg | null>(null)
  const [selectedMember,    setSelectedMember]    = useState<PartnerMember | null>(null)
  const [selectedIssueTypes, setSelectedIssueTypes] = useState<Set<string> | null>(null)
  const [selectedStatuses, setSelectedStatuses] = useState<Set<string> | null>(null)
  const [loadedPartnerStatuses, setLoadedPartnerStatuses] = useState<string[]>([])
  const [selectedSemester, setSelectedSemester] = useState<Semester | null>(null)
  const latestReport = useLatestReport()
  const reportFilter = useMemo(
    () => latestReport.data ? resolveDashboardFilterContract(latestReport.data) : null,
    [latestReport.data],
  )
  const issueTypes = useMemo(() => (reportFilter?.issueTypes ?? []).filter((issueType) => !isLicenseIssueType(issueType)), [reportFilter])
  const reportStatusTypes = reportFilter?.statusTypes ?? []
  const statusTypes = useMemo(
    () => sortDashboardStatuses([...reportStatusTypes, ...loadedPartnerStatuses]),
    [loadedPartnerStatuses, reportStatusTypes],
  )
  const reportYear = reportFilter?.reportYear ?? new Date().getFullYear()
  const supportsIssueTypeFiltering = reportFilter?.supportsIssueTypeFiltering ?? false
  const supportsStatusFiltering = statusTypes.length > 0
  const supportsSemesterFiltering = reportFilter?.supportsSemesterFiltering ?? false
  const effectiveIssueTypes = supportsIssueTypeFiltering ? selectedIssueTypes : null
  const effectiveStatuses = supportsStatusFiltering ? selectedStatuses : null
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

  const handleStatusToggle = (status: string) => {
    setSelectedStatuses((current) => {
      const next = new Set(current ?? statusTypes)
      if (next.has(status)) next.delete(status)
      else next.add(status)
      return next.size === statusTypes.length ? null : next
    })
  }

  const handlePartnerStatusesChange = useCallback((statuses: string[]) => {
    setLoadedPartnerStatuses((current) => {
      const next = sortDashboardStatuses([...current, ...statuses])
      return next.length === current.length && next.every((status, index) => status === current[index])
        ? current
        : next
    })
  }, [])

  const issueLabel = selectedMember
    ? `${selectedMember.display_name} 이슈`
    : selectedOrg
    ? `${selectedOrg.name} 전체 이슈`
    : '이슈'

  return (
    <div className="flex w-full min-w-0 flex-col gap-4 xl:h-full">
      <div className="flex-shrink-0">
        <div>
          <h1 className="text-page-title font-semibold text-apple-dark">파트너 관리</h1>
        </div>
      </div>
      {latestReport.isLoading ? (
        <div className="card flex min-h-24 items-center justify-center text-label text-apple-light animate-pulse">필터 불러오는 중...</div>
      ) : (
        <IssueTypeFilter
          issueTypes={issueTypes}
          statuses={statusTypes}
          selectedTypes={selectedIssueTypes}
          selectedStatuses={selectedStatuses}
          selectedSemester={selectedSemester}
          supported={supportsIssueTypeFiltering}
          statusSupported={supportsStatusFiltering}
          semesterSupported={supportsSemesterFiltering}
          onToggle={handleIssueTypeToggle}
          onStatusToggle={handleStatusToggle}
          onSemesterChange={setSelectedSemester}
          onToggleAll={(selected) => {
            if (supportsIssueTypeFiltering) setSelectedIssueTypes(selected ? null : new Set())
            if (supportsStatusFiltering) setSelectedStatuses(selected ? null : new Set())
          }}
        />
      )}
      <div className="grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2 xl:min-h-80 xl:flex-1 xl:grid-cols-[220px_220px_minmax(0,1fr)]">
        <div className="h-80 min-w-0 overflow-hidden rounded-2xl border border-apple-divider bg-apple-surface shadow-sm xl:h-auto">
          <PartnerOrgPanel
            selectedOrgId={selectedOrg?.id ?? null}
            searchQuery={organizationQuery}
            onSearchChange={setOrganizationQuery}
            onSelect={handleSelectOrg}
          />
        </div>
        <div className="h-80 min-w-0 overflow-hidden rounded-2xl border border-apple-divider bg-apple-surface shadow-sm xl:h-auto">
          <PartnerMemberPanel
            orgId={selectedOrg?.id ?? null}
            orgName={selectedOrg?.name ?? ''}
            selectedAccountId={selectedMember?.account_id ?? null}
            searchQuery={memberQuery}
            onSearchChange={setMemberQuery}
            onSelect={setSelectedMember}
          />
        </div>
        <div className="h-96 min-w-0 overflow-hidden rounded-2xl border border-apple-divider bg-apple-surface shadow-sm md:col-span-2 xl:col-span-1 xl:h-auto">
          <PartnerIssuePanel
            orgId={selectedOrg?.id ?? null}
            accountId={selectedMember?.account_id ?? null}
            label={issueLabel}
            searchQuery={issueQuery}
            onSearchChange={setIssueQuery}
            issueTypes={issueTypes}
            selectedIssueTypes={effectiveIssueTypes}
            selectedStatuses={effectiveStatuses}
            selectedSemester={effectiveSemester}
            reportYear={reportYear}
            onStatusesChange={handlePartnerStatusesChange}
          />
        </div>
      </div>
    </div>
  )
}
