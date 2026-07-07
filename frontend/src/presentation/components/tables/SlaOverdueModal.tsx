// frontend/src/presentation/components/tables/SlaOverdueModal.tsx
import { useEffect } from 'react'

const JIRA_BASE = 'https://seculayer.atlassian.net/browse'

export interface OverdueIssue {
  key: string
  summary: string
  type: string
  created: string
  resp_status: string
  over_h: number
}

interface Props {
  issues: OverdueIssue[]
  total: number
  onClose: () => void
}

export default function SlaOverdueModal({ issues, total, onClose }: Props) {
  // ESC 키 닫기
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl mx-4 max-h-[85vh] flex flex-col">
        {/* 헤더 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-apple-divider/60">
          <div>
            <h2 className="text-[15px] font-semibold text-apple-dark">SLA 초과 이슈 상세</h2>
            <p className="text-[12px] text-apple-light mt-0.5">30일 이상 미해결 이슈 · 총 {total}건 (초과시간 내림차순)</p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-apple-gray text-apple-light hover:text-apple-dark transition-colors"
          >
            ✕
          </button>
        </div>

        {/* 테이블 영역 (스크롤) */}
        <div className="overflow-y-auto flex-1 px-6 py-4">
          {/* PC 테이블 */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-apple-divider/60">
                  {['이슈 번호', '제목', '유형', '생성일시', '응답상태', '초과시간'].map(h => (
                    <th key={h} className="text-left pb-3 text-[11px] font-semibold text-apple-light uppercase tracking-wider whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-apple-divider/40">
                {issues.map((d) => (
                  <tr key={d.key} className="hover:bg-apple-gray/50 transition-colors duration-150">
                    <td className="py-2.5 pr-4">
                      <a
                        href={`${JIRA_BASE}/${d.key}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[12px] font-mono font-medium text-brand-600 hover:text-brand-700 hover:underline whitespace-nowrap"
                      >
                        {d.key}
                      </a>
                    </td>
                    <td className="py-2.5 text-[12px] text-apple-dark/80 max-w-xs truncate pr-4">{d.summary}</td>
                    <td className="py-2.5 text-[12px] text-apple-light whitespace-nowrap pr-4">{d.type}</td>
                    <td className="py-2.5 text-[12px] text-apple-light tabular-nums whitespace-nowrap pr-4">{d.created}</td>
                    <td className="py-2.5 whitespace-nowrap pr-4">
                      <span className={d.resp_status === '종료' ? 'badge-good' : 'badge-warning'}>
                        {d.resp_status}
                      </span>
                    </td>
                    <td className="py-2.5 text-[12px] tabular-nums whitespace-nowrap">
                      <span className="font-semibold text-red-500">+{d.over_h}h</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 모바일 카드 */}
          <div className="md:hidden divide-y divide-apple-divider/40">
            {issues.map((d) => (
              <div key={d.key} className="py-3 flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <a
                    href={`${JIRA_BASE}/${d.key}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[12px] font-mono font-medium text-brand-600 hover:underline"
                  >
                    {d.key}
                  </a>
                  <span className="text-[12px] font-semibold text-red-500">+{d.over_h}h</span>
                </div>
                <p className="text-[12px] text-apple-dark/80 leading-snug">{d.summary}</p>
                <div className="flex flex-wrap gap-2 text-[11px] text-apple-light">
                  <span>{d.type}</span>
                  <span>·</span>
                  <span>{d.created}</span>
                  <span>·</span>
                  <span className={d.resp_status === '종료' ? 'text-green-600' : 'text-amber-600'}>{d.resp_status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 푸터 */}
        <div className="px-6 py-3 border-t border-apple-divider/60 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg text-[13px] font-medium bg-apple-gray hover:bg-apple-divider text-apple-dark transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  )
}
