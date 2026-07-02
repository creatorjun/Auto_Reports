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
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-900">🗂️ 보고서 히스토리</h1>
      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="text-left px-6 py-3 font-semibold text-gray-500">ID</th>
              <th className="text-left px-6 py-3 font-semibold text-gray-500">데이터 범위</th>
              <th className="text-left px-6 py-3 font-semibold text-gray-500">생성시각</th>
              <th className="text-left px-6 py-3 font-semibold text-gray-500">AI 상태</th>
              <th className="px-6 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {(data ?? []).map((r) => (
              <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-3 font-mono text-gray-400">#{r.id}</td>
                <td className="px-6 py-3">{r.week_start} ~ {r.week_end}</td>
                <td className="px-6 py-3 text-gray-500">
                  {format(new Date(r.created_at), 'MM/dd HH:mm', { locale: ko })}
                </td>
                <td className="px-6 py-3">
                  {r.sentiment
                    ? <span className={sentimentLabel[r.sentiment]}>{sentimentText[r.sentiment]}</span>
                    : <span className="text-gray-300">-</span>
                  }
                </td>
                <td className="px-6 py-3">
                  <Link to={`/reports/${r.id}`} className="text-brand-600 hover:underline text-xs font-medium">
                    상세 보기 →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data?.length && <p className="text-center text-gray-400 py-12">보고서가 없습니다.</p>}
      </div>
    </div>
  )
}
