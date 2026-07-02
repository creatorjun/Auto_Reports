// frontend/src/presentation/pages/HistoryPage.tsx
import { Link } from 'react-router-dom'
import { useAllReports } from '@/infrastructure/hooks/useReport'
import LoadingSpinner from '@/presentation/components/common/LoadingSpinner'
import { format } from 'date-fns'
import { ko } from 'date-fns/locale'

const sentimentLabel: Record<string, string> = {
  good: 'badge-good',
  warning: 'badge-warning',
  critical: 'badge-critical'
}
const sentimentText: Record<string, string> = {
  good: '양호', warning: '주의', critical: '경고'
}

export default function HistoryPage() {
  const { data, isLoading } = useAllReports()

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-5 max-w-[1400px]">
      <div>
        <h1 className="text-[22px] font-semibold text-apple-dark tracking-tight">보고서 히스토리</h1>
        <p className="text-[13px] text-apple-light mt-1">자동 생성된 TAC 주간 보고서 목록</p>
      </div>
      <div className="card overflow-hidden p-0">
        <table className="w-full">
          <thead className="border-b border-apple-divider/60">
            <tr>
              {['ID', '데이터 범위', '생성 시각', 'AI 상태', ''].map((h, i) => (
                <th key={i} className="text-left px-6 py-3.5 text-[11px] font-semibold text-apple-light uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-apple-divider/40">
            {(data ?? []).map((r) => (
              <tr key={r.id} className="hover:bg-apple-gray/60 transition-colors duration-150">
                <td className="px-6 py-3.5 text-[12px] font-mono text-apple-light">#{r.id}</td>
                <td className="px-6 py-3.5 text-[13px] text-apple-dark">{r.week_start} – {r.week_end}</td>
                <td className="px-6 py-3.5 text-[13px] text-apple-light tabular-nums">
                  {format(new Date(r.created_at), 'MM/dd HH:mm', { locale: ko })}
                </td>
                <td className="px-6 py-3.5">
                  {r.sentiment
                    ? <span className={sentimentLabel[r.sentiment]}>{sentimentText[r.sentiment]}</span>
                    : <span className="text-apple-divider text-[12px]">—</span>
                  }
                </td>
                <td className="px-6 py-3.5 text-right">
                  <Link
                    to={`/reports/${r.id}`}
                    className="text-[12px] text-brand-600 hover:text-brand-700 font-medium transition-colors"
                  >
                    상세 보기
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data?.length && (
          <p className="text-center text-[13px] text-apple-light py-16">보고서가 없습니다.</p>
        )}
      </div>
    </div>
  )
}
