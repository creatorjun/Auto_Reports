// frontend/src/presentation/components/tables/WeeklyCreatedModal.tsx
import { useEffect } from 'react'
import { useConfig } from '@/infrastructure/hooks/useConfig'
import { statusBadge } from './statusBadge'

export interface CreatedIssue {
  key: string
  summary: string
  type: string
  status: string
  created: string
}

interface Props {
  issues: CreatedIssue[]
  total: number
  onClose: () => void
}

export default function WeeklyCreatedModal({ issues, total, onClose }: Props) {
  const { data: config } = useConfig()
  const jiraBase = `${config?.jira_base_url ?? 'https://seculayer.atlassian.net'}/browse`

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
        <div className="flex items-center justify-between px-6 py-4 border-b border-apple-divider/60">
          <div>
            <h2 className="text-[15px] font-semibold text-apple-dark">이번 주 생성 이슈</h2>
            <p className="text-[12px] text-apple-light mt-0.5">최근 7일 이내 생성 · 전체 {total}건 (생성일 최신순)</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-apple-gray text-apple-light hover:text-apple-dark transition-colors">✕</button>
        </div>

        <div className="overflow-y-auto flex-1 px-6 py-4">
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-apple-divider/60">
                  {['이슈 번호', '제목', '유형', '현재 상태', '생성일시'].map(h => (
                    <th key={h} className="text-left pb-3 text-[11px] font-semibold text-apple-light uppercase tracking-wider whitespace-nowrap pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-apple-divider/40">
                {issues.map((d) => (
                  <tr
                    key={d.key}
                    onClick={() => window.open(`${jiraBase}/${d.key}`, '_blank', 'noreferrer')}
                    className="hover:bg-apple-gray/50 transition-colors duration-150 cursor-pointer"
                  >
                    <td className="py-2.5 pr-4 text-[12px] font-mono font-medium text-brand-600 whitespace-nowrap">{d.key}</td>
                    <td className="py-2.5 text-[12px] text-apple-dark/80 max-w-xs truncate pr-4">{d.summary}</td>
                    <td className="py-2.5 text-[12px] text-apple-light whitespace-nowrap pr-4">{d.type}</td>
                    <td className="py-2.5 whitespace-nowrap pr-4">{statusBadge(d.status)}</td>
                    <td className="py-2.5 text-[12px] text-apple-light tabular-nums whitespace-nowrap">{d.created}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="md:hidden divide-y divide-apple-divider/40">
            {issues.map((d) => (
              <div
                key={d.key}
                onClick={() => window.open(`${jiraBase}/${d.key}`, '_blank', 'noreferrer')}
                className="py-3 flex flex-col gap-1 cursor-pointer hover:bg-apple-gray/50 rounded-lg px-2 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[12px] font-mono font-medium text-brand-600">{d.key}</span>
                  <span className="text-[11px] text-apple-light tabular-nums">{d.created}</span>
                </div>
                <p className="text-[12px] text-apple-dark/80 leading-snug">{d.summary}</p>
                <div className="flex flex-wrap gap-2 items-center text-[11px] text-apple-light">
                  <span>{d.type}</span><span>·</span>{statusBadge(d.status)}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="px-6 py-3 border-t border-apple-divider/60 flex justify-end">
          <button onClick={onClose} className="px-4 py-1.5 rounded-lg text-[13px] font-medium bg-apple-gray hover:bg-apple-divider text-apple-dark transition-colors">닫기</button>
        </div>
      </div>
    </div>
  )
}
