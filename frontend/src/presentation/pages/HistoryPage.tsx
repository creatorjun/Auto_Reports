// frontend/src/presentation/pages/HistoryPage.tsx
import { Link } from 'react-router-dom'
import { useAllReports } from '@/infrastructure/hooks/useReport'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import { format } from 'date-fns'
import { ko } from 'date-fns/locale'

const sentimentLabel: Record<string, string> = {
  good: 'badge-good', warning: 'badge-warning', critical: 'badge-critical'
}
const sentimentText: Record<string, string> = {
  good: '양호', warning: '주의', critical: '경고'
}

export default function HistoryPage() {
  const { data, isLoading } = useAllReports()
  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-4 md:space-y-5 3xl:space-y-7">
      <div>
        <h1 className="text-[18px] md:text-[22px] 3xl:text-[26px] font-semibold text-apple-dark tracking-tight">보고서 히스토리</h1>
        <p className="text-[12px] md:text-[13px] 3xl:text-[14px] text-apple-light mt-1">자동 생성된 TAC 주간 보고서 목록</p>
      </div>

      <div className="card overflow-hidden p-0">
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
              {(data ?? []).map((r) => (
                <tr key={r.id} className="hover:bg-apple-gray/60 transition-colors duration-150">
                  <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[12px] 3xl:text-[13px] font-mono text-apple-light">#{r.id}</td>
                  <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-dark">{r.week_start} – {r.week_end}</td>
                  <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-light tabular-nums">
                    {format(new Date(r.created_at), 'MM/dd HH:mm', { locale: ko })}
                  </td>
                  <td className="px-6 py-3.5 3xl:px-8 3xl:py-4">
                    {r.sentiment
                      ? <span className={sentimentLabel[r.sentiment]}>{sentimentText[r.sentiment]}</span>
                      : <span className="text-apple-divider text-[12px]">—</span>
                    }
                  </td>
                  <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-right">
                    <Link to={`/reports/${r.id}`} className="text-[12px] 3xl:text-[13px] text-brand-600 hover:text-brand-700 font-medium transition-colors">
                      상세 보기
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="md:hidden divide-y divide-apple-divider/40">
          {(data ?? []).map((r) => (
            <Link
              key={r.id}
              to={`/reports/${r.id}`}
              className="flex items-center justify-between px-4 py-4 hover:bg-apple-gray/60 transition-colors"
            >
              <div className="flex flex-col gap-1">
                <span className="text-[13px] font-medium text-apple-dark">{r.week_start} – {r.week_end}</span>
                <span className="text-[11px] text-apple-light tabular-nums">
                  #{r.id} · {format(new Date(r.created_at), 'MM/dd HH:mm', { locale: ko })}
                </span>
              </div>
              <div className="flex items-center gap-3">
                {r.sentiment && <span className={sentimentLabel[r.sentiment]}>{sentimentText[r.sentiment]}</span>}
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-apple-light">
                  <path d="M5 3l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            </Link>
          ))}
        </div>

        {!data?.length && <p className="text-center text-[13px] text-apple-light py-16">보고서가 없습니다.</p>}
      </div>
    </div>
  )
}
