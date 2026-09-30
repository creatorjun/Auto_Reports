// frontend/src/presentation/pages/IssueManagementPage.tsx
import { useMemo, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import type { Semester } from '@/domain/Dashboard'
import type { ElapsedDaysComparison } from '@/domain/Issue'
import { filterIssuesByColumns, filterManagedIssues } from '@/domain/IssueManagement'
import { sortDashboardStatuses } from '@/domain/DashboardStatusPolicy'
import { useIssueManagement } from '@/presentation/hooks/useIssueManagement'
import IssueTypeFilter from '@/presentation/components/common/IssueTypeFilter'
import RecentIssuesWidget from '@/presentation/components/charts/RecentIssuesWidget'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

export default function IssueManagementPage() {
  const query = useIssueManagement()
  const [types, setTypes] = useState<Set<string> | null>(null)
  const [statuses, setStatuses] = useState<Set<string> | null>(null)
  const [semester, setSemester] = useState<Semester | null>(null)
  const [titleSearch, setTitleSearch] = useState('')
  const [elapsed, setElapsed] = useState<number | null>(null)
  const [comparison, setComparison] = useState<ElapsedDaysComparison>('gte')
  const issues = query.data?.issues
  const options = useMemo(() => ({
    types: [...new Set(issues?.map((issue) => issue.type) ?? [])].sort(),
    statuses: sortDashboardStatuses(issues?.map((issue) => issue.status) ?? []),
  }), [issues])
  const details = useMemo(() => filterIssuesByColumns(filterManagedIssues(issues ?? [], types, statuses, semester, null), { summary: titleSearch }), [issues, types, statuses, semester, titleSearch])
  const toggle = (current: Set<string> | null, all: string[], value: string) => {
    const next = new Set(current ?? all)
    if (next.has(value)) next.delete(value)
    else next.add(value)
    return next.size === all.length && all.every((item) => next.has(item)) ? null : next
  }

  return (
    <div className="dashboard-view space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-apple-dark">이슈 관리</h1>
          <p className="mt-1 text-ui-sm text-apple-mid">TACEA 전체 요청 · 완료 항목 포함 · 30초마다 변경분 동기화</p>
          <p className="mt-1 text-xs text-apple-light" aria-live="polite">{query.data?.synced_at ? `마지막 동기화 ${new Date(query.data.synced_at).toLocaleString('ko-KR')}` : '전체 이슈를 수집하고 있습니다.'}{query.data?.refreshing ? ' · 동기화 중' : ''}</p>
        </div>
        <button type="button" onClick={() => void query.refetch()} disabled={query.isFetching} className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-ui-sm font-semibold text-white disabled:opacity-50">
          <RefreshCw size={16} className={query.isFetching || query.data?.refreshing ? 'animate-spin' : ''} />새로고침
        </button>
      </div>
      {(query.isError || query.data?.error) && <p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{query.data?.error ?? '이슈 조회에 실패했습니다. 기존 목록을 유지하며 자동 재시도합니다.'}</p>}
      <IssueTypeFilter issueTypes={options.types} statuses={options.statuses} selectedTypes={types} selectedStatuses={statuses} selectedSemester={semester} supported statusSupported semesterSupported
        titleSearch={titleSearch} onTitleSearchChange={setTitleSearch}
        onToggle={(value) => setTypes((current) => toggle(current, options.types, value))}
        onStatusToggle={(value) => setStatuses((current) => toggle(current, options.statuses, value))}
        onSemesterChange={setSemester}
        onReset={() => { setTypes(null); setStatuses(null); setSemester(null); setTitleSearch('') }} />
      {!query.data?.initialized && !query.data?.error && !query.isError ? <LoadingSpinner text="TACEA 전체 이슈 수집 중..." /> : (
        <RecentIssuesWidget columnSearch title="전체 이슈 현황" paginationResetKey={JSON.stringify([types === null ? null : [...types].sort(), statuses === null ? null : [...statuses].sort(), semester, elapsed, comparison, titleSearch])} details={details} elapsedDaysThreshold={elapsed} elapsedDaysComparison={comparison} onElapsedDaysFilterChange={(value, condition) => { setElapsed(value); setComparison(condition) }} />
      )}
    </div>
  )
}
