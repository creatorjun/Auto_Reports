// frontend/src/presentation/components/tables/HistoryReportTable.tsx
import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import { ko } from 'date-fns/locale'
import { TrashIcon } from '@/presentation/components/storage/StorageIcons'
import type { ReportSummary } from '@/domain/Report'

const sentimentLabel: Record<string, string> = {
  good: 'badge-good', warning: 'badge-warning', critical: 'badge-critical'
}
const sentimentText: Record<string, string> = {
  good: '양호', warning: '주의', critical: '경고'
}

function ReportRow({ r, onDelete }: { r: ReportSummary; onDelete: (id: number) => void }) {
  const formattedDate = useMemo(
    () => format(new Date(r.created_at), 'MM/dd HH:mm', { locale: ko }),
    [r.created_at]
  )
  return (
    <tr className="hover:bg-apple-gray/60 transition-colors duration-150">
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[12px] 3xl:text-[13px] font-mono text-apple-light">#{r.id}</td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-dark">{r.week_start} – {r.week_end}</td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-light tabular-nums">{formattedDate}</td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4">
        {r.sentiment
          ? <span className={sentimentLabel[r.sentiment]}>{sentimentText[r.sentiment]}</span>
          : <span className="text-apple-divider text-[12px]">—</span>
        }
      </td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4">
        <div className="flex items-center justify-end gap-3">
          <Link
            to={`/reports/${r.id}`}
            className="text-[12px] 3xl:text-[13px] text-brand-600 hover:text-brand-700 font-medium transition-colors"
          >
            상세 보기
          </Link>
          <button
            onClick={() => onDelete(r.id)}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors"
            title="삭제"
          >
            <TrashIcon />
          </button>
        </div>
      </td>
    </tr>
  )
}

function MobileReportRow({ r, onDelete }: { r: ReportSummary; onDelete: (id: number) => void }) {
  const formattedDate = useMemo(
    () => format(new Date(r.created_at), 'MM/dd HH:mm', { locale: ko }),
    [r.created_at]
  )
  return (
    <div className="flex items-center justify-between px-4 py-4 hover:bg-apple-gray/60 transition-colors">
      <Link to={`/reports/${r.id}`} className="flex flex-col gap-1 flex-1 min-w-0">
        <span className="text-[13px] font-medium text-apple-dark">{r.week_start} – {r.week_end}</span>
        <span className="text-[11px] text-apple-light tabular-nums">#{r.id} · {formattedDate}</span>
      </Link>
      <div className="flex items-center gap-2 flex-shrink-0">
        {r.sentiment && <span className={sentimentLabel[r.sentiment]}>{sentimentText[r.sentiment]}</span>}
        <Link to={`/reports/${r.id}`}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-apple-light">
            <path d="M5 3l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </Link>
        <button
          onClick={() => onDelete(r.id)}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors"
        >
          <TrashIcon />
        </button>
      </div>
    </div>
  )
}

export function HistoryReportTable({
  data,
  onDelete,
}: {
  data: ReportSummary[]
  onDelete: (id: number) => void
}) {
  return (
    <>
      <div className="hidden md:block">
        <table className="w-full">
          <thead className="border-b border-apple-divider/60">
            <tr>
              {['ID', '데이터 범위', '생성 시각', 'AI 상태', ''].map((h, i) => (
                <th key={i} className="text-left px-6 py-3.5 3xl:px-8 3xl:py-4 text-[11px] 3xl:text-[12px] font-semibold text-apple-light uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-apple-divider/40">
            {data.map((r) => (
              <ReportRow key={r.id} r={r} onDelete={onDelete} />
            ))}
          </tbody>
        </table>
      </div>
      <div className="md:hidden divide-y divide-apple-divider/40">
        {data.map((r) => (
          <MobileReportRow key={r.id} r={r} onDelete={onDelete} />
        ))}
      </div>
    </>
  )
}
