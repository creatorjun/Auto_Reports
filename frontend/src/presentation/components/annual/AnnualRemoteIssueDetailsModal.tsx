// frontend/src/presentation/components/annual/AnnualRemoteIssueDetailsModal.tsx
import { useQuery } from '@tanstack/react-query'
import type { ChartIssuesRequest } from '@/domain/ReportChartDetails'
import { RequestError } from '@/application/errors/RequestError'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import IssueModalShell from '@/presentation/components/common/IssueModalShell'
import AnnualIssueDetailsModal from './AnnualIssueDetailsModal'

interface Props {
  reportId: number
  request: ChartIssuesRequest
  title: string
  total: number
  onClose: () => void
}

export default function AnnualRemoteIssueDetailsModal({ reportId, request, title, total, onClose }: Props) {
  const { reports } = useApplicationServices()
  const query = useQuery({
    queryKey: ['annual-chart-issues', reportId, request],
    queryFn: ({ signal }) => reports.getChartIssues(reportId, request, signal),
    retry: false,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  })

  if (!query.data) {
    const message = query.error instanceof RequestError && typeof query.error.detail === 'string'
      ? query.error.detail
      : '개별 이슈를 조회하지 못했습니다. 잠시 후 다시 시도해 주세요.'
    return (
      <IssueModalShell title={title} subtitle={`차트 집계 ${total.toLocaleString('ko-KR')}건`} size="lg" onClose={onClose}>
        {query.isPending ? <p role="status" className="py-10 text-center text-base text-apple-mid">개별 이슈를 조회하고 있습니다…</p> : (
          <div className="space-y-4 py-6 text-center">
            <p role="alert" className="text-base text-apple-dark">{message}</p>
            <button type="button" onClick={() => void query.refetch()} className="rounded-lg bg-brand-600 px-4 py-2 text-white">다시 조회</button>
          </div>
        )}
      </IssueModalShell>
    )
  }

  const result = query.data
  return (
    <AnnualIssueDetailsModal
      title={title}
      total={total}
      issues={result.issues}
      dateField={request.chart === 'sla_initial' || request.chart === 'sla_resolution' ? 'created' : 'resolved'}
      description={`Jira 현재 데이터 조회 · ${new Date(result.queried_at).toLocaleString('ko-KR')}. 보고서 집계 이후 변경된 이슈가 반영될 수 있습니다.`}
      headerSlot={<>
        {result.truncated && <p role="status" className="rounded-lg bg-amber-50 px-3 py-2 text-amber-800">차트와 동일한 수집 기준으로 원천 {result.source_total.toLocaleString('ko-KR')}건{result.source_total_exact ? '' : ' 이상'} 중 최대 {result.collection_limit?.toLocaleString('ko-KR')}건을 조회한 뒤 선택 조건을 적용했습니다.</p>}
        {query.isError && <p role="alert">갱신에 실패하여 이전 조회 목록을 표시합니다.</p>}
      </>}
      onClose={onClose}
    />
  )
}
