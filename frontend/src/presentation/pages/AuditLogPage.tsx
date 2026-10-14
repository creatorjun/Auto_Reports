// frontend/src/presentation/pages/AuditLogPage.tsx
import { useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, RefreshCw, Search, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { RequestError } from '@/application/errors/RequestError'
import { auditDefaultFilters, auditEventLabel, auditFilterError, auditLogQuery, visibleAuditDetails } from '@/application/services/auditLog'
import type { AuditLogFilters } from '@/application/services/auditLog'
import type { AuditLogEntry } from '@/domain/AuditLog'
import { useAuditLogs } from '@/presentation/hooks/useAuditLogs'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'

const fieldClass = 'w-full rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control text-apple-dark focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30'
const buttonClass = 'inline-flex items-center justify-center gap-2 rounded-xl border border-apple-divider bg-apple-surface px-4 py-2.5 text-control font-medium text-apple-dark transition-colors hover:bg-apple-gray disabled:cursor-not-allowed disabled:opacity-40'
const timestampFormatter = new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' })

function timestampLabel(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '확인 불가' : timestampFormatter.format(date)
}

function AuditDetails({ entry }: { entry: AuditLogEntry }) {
  const details = visibleAuditDetails(entry.details)
  if (!details.length) return <span className="text-apple-light">추가 정보 없음</span>
  return (
    <details className="min-w-44 max-w-xl">
      <summary className="cursor-pointer select-none text-brand-600 focus-visible:outline-brand-400">상세 보기 <span className="text-apple-light">({details.length})</span></summary>
      <dl className="mt-3 space-y-2 rounded-xl bg-apple-gray p-3 text-caption">
        {details.map(([key, value]) => (
          <div key={key} className="grid grid-cols-[minmax(70px,1fr)_minmax(0,3fr)] gap-3">
            <dt className="break-words text-apple-mid">{key}</dt>
            <dd className="whitespace-pre-wrap break-all text-apple-dark">{value || '확인 불가'}</dd>
          </div>
        ))}
      </dl>
    </details>
  )
}

export default function AuditLogPage() {
  const [draft, setDraft] = useState<AuditLogFilters>(() => auditDefaultFilters())
  const [filters, setFilters] = useState(draft)
  const [page, setPage] = useState(0)
  const [validation, setValidation] = useState<string | null>(null)
  const request = useMemo(() => auditLogQuery(filters, page), [filters, page])
  const logs = useAuditLogs(request)
  const data = logs.data
  const status = logs.error instanceof RequestError ? logs.error.status : null
  const denied = status === 401 || status === 403 || !logs.allowed
  const pageCount = Math.min(100, Math.max(1, Math.ceil((data?.total ?? 0) / request.limit)))
  const events = Array.from(new Set([...(data?.events ?? []), draft.event].filter(Boolean))).sort()
  const update = (key: keyof AuditLogFilters, value: string) => setDraft((current) => ({ ...current, [key]: value }))

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    const error = auditFilterError(draft)
    setValidation(error)
    if (error) return
    if (JSON.stringify(draft) === JSON.stringify(filters) && page === 0) void logs.refetch()
    setFilters({ ...draft })
    setPage(0)
  }

  const reset = () => {
    const defaults = auditDefaultFilters()
    setDraft(defaults)
    setFilters(defaults)
    setPage(0)
    setValidation(null)
  }

  return (
    <main className="mx-auto flex w-full max-w-content flex-col gap-6 px-4 py-6 md:px-6 3xl:max-w-none">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-caption font-medium text-brand-600"><ShieldCheck size={16} />관리자 전용</div>
          <h1 className="text-page-title font-semibold tracking-tight text-apple-dark">감사로그</h1>
          <p className="mt-2 text-label text-apple-mid">로그인과 주요 작업의 기록을 최신순으로 확인합니다. 시간 기준: 한국 표준시 (KST)</p>
        </div>
        <button type="button" className={buttonClass} onClick={() => void logs.refetch()} disabled={logs.isFetching || !logs.allowed}>
          <RefreshCw size={16} className={logs.isFetching ? 'animate-spin' : ''} />새로고침
        </button>
      </header>

      <form onSubmit={submit} className="rounded-2xl border border-apple-divider bg-apple-surface p-4 shadow-sm md:p-5">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
          <label className="flex flex-col gap-2 text-control-label font-medium text-apple-mid">시작일<input type="date" value={draft.start_date} onChange={(event) => update('start_date', event.target.value)} className={fieldClass} /></label>
          <label className="flex flex-col gap-2 text-control-label font-medium text-apple-mid">종료일<input type="date" value={draft.end_date} onChange={(event) => update('end_date', event.target.value)} className={fieldClass} /></label>
          <label className="flex flex-col gap-2 text-control-label font-medium text-apple-mid">이벤트<select value={draft.event} onChange={(event) => update('event', event.target.value)} className={fieldClass}>
            <option value="">전체 이벤트</option>{events.map((event) => <option key={event} value={event}>{auditEventLabel(event)}</option>)}
          </select></label>
          <label className="flex flex-col gap-2 text-control-label font-medium text-apple-mid">사용자<input type="text" autoComplete="off" maxLength={200} placeholder="사용자 검색" value={draft.username} onChange={(event) => update('username', event.target.value)} className={fieldClass} /></label>
          <label className="flex flex-col gap-2 text-control-label font-medium text-apple-mid">IP 주소<input type="text" autoComplete="off" maxLength={200} placeholder="IP 주소 검색" value={draft.ip} onChange={(event) => update('ip', event.target.value)} className={fieldClass} /></label>
          <label className="flex flex-col gap-2 text-control-label font-medium text-apple-mid">검색어<input type="search" maxLength={200} placeholder="이벤트·작업 내용 검색" value={draft.search} onChange={(event) => update('search', event.target.value)} className={fieldClass} /></label>
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-end gap-2">
          {validation && <p role="alert" className="mr-auto text-label text-red-600">{validation}</p>}
          <button type="button" onClick={reset} className={buttonClass}>초기화</button>
          <button type="submit" disabled={logs.isFetching || !logs.allowed} className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-control font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40"><Search size={16} />조회</button>
        </div>
      </form>

      {!!data?.warnings.length && <div role="status" className="rounded-xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-label text-apple-dark">{data.warnings.map((warning, index) => <p key={index}>{warning}</p>)}</div>}
      {(data?.total ?? 0) > request.limit * 100 && <p role="status" className="rounded-xl border border-apple-divider bg-apple-surface px-4 py-3 text-label text-apple-mid">최대 100페이지까지 조회할 수 있습니다. 더 이전 기록은 날짜 범위를 좁혀 조회해 주세요.</p>}

      {logs.isError || denied ? (
        <div role="alert" className="rounded-2xl border border-apple-divider bg-apple-surface p-10 text-center">
          <h2 className="text-section-title font-semibold text-apple-dark">{denied ? '감사로그 조회 권한을 확인해 주세요' : '감사로그를 불러오지 못했습니다'}</h2>
          <p className="mt-2 text-label text-apple-mid">{status === 401 ? '로그인이 만료되었습니다. 다시 로그인해 주세요.' : denied ? '관리자 계정으로 로그인하면 조회할 수 있습니다.' : '잠시 후 다시 조회해 주세요.'}</p>
          {denied ? <Link to="/login" className={`${buttonClass} mt-5`}>로그인 화면</Link> : <button type="button" className={`${buttonClass} mt-5`} onClick={() => void logs.refetch()}>다시 조회</button>}
        </div>
      ) : (
        <section aria-label="감사로그 조회 결과" aria-busy={logs.isFetching} className="overflow-hidden rounded-2xl border border-apple-divider bg-apple-surface shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-apple-divider px-5 py-4">
            <h2 className="text-section-title font-semibold text-apple-dark">조회 결과 <span className="ml-2 tabular-nums text-brand-600">{data ? `${data.total.toLocaleString('ko-KR')}건` : '조회 중'}</span></h2>
            <span className="text-caption text-apple-light">최신순 · 페이지당 {request.limit}건</span>
          </div>
          {logs.isPending ? <div className="py-16"><LoadingSpinner text="감사로그 조회 중..." /></div> : !data?.items.length ? <p role="status" className="px-6 py-16 text-center text-label text-apple-mid">조회 조건에 해당하는 감사로그가 없습니다.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px] border-collapse text-left text-body">
                <thead className="bg-apple-gray text-label text-apple-mid"><tr>
                  {['발생 시각 (KST)', '이벤트', '사용자', 'IP 주소', '작업 상세'].map((label) => <th key={label} scope="col" className="px-5 py-3 font-medium">{label}</th>)}
                </tr></thead>
                <tbody className="divide-y divide-apple-divider/60">
                  {data.items.map((entry, index) => <tr key={`${request.offset + index}-${entry.timestamp}-${entry.event}`} className="align-top hover:bg-apple-gray/40">
                    <td className="whitespace-nowrap px-5 py-4 text-label tabular-nums text-apple-mid">{timestampLabel(entry.timestamp)}</td>
                    <td className="px-5 py-4"><span className="whitespace-nowrap font-medium text-apple-dark">{auditEventLabel(entry.event)}</span><span className="mt-1 block text-caption text-apple-light">{entry.event}</span></td>
                    <td className="max-w-52 break-words px-5 py-4 text-apple-dark">{entry.username || '확인 불가'}</td>
                    <td className="max-w-52 break-all px-5 py-4 font-mono text-label text-apple-mid">{entry.ip || '확인 불가'}</td>
                    <td className="px-5 py-4 text-label"><AuditDetails entry={entry} /></td>
                  </tr>)}
                </tbody>
              </table>
            </div>
          )}
          <div className="flex items-center justify-between gap-3 border-t border-apple-divider px-5 py-4">
            <button className={buttonClass} type="button" disabled={page === 0 || logs.isFetching} onClick={() => setPage((current) => current - 1)}><ChevronLeft size={16} />이전</button>
            <span className="text-caption tabular-nums text-apple-mid">{page + 1} / {data ? pageCount : '—'} 페이지</span>
            <button className={buttonClass} type="button" disabled={!data || page + 1 >= pageCount || logs.isFetching} onClick={() => setPage((current) => current + 1)}>다음<ChevronRight size={16} /></button>
          </div>
        </section>
      )}
    </main>
  )
}
