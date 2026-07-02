// frontend/src/presentation/components/tables/IssueDetailTable.tsx
interface IssueDetail {
  key: string
  summary: string
  type: string
  resolution_h: number
  res_breached: boolean
}

export default function IssueDetailTable({ details }: { details: IssueDetail[] }) {
  if (!details?.length) return null
  return (
    <div className="card">
      <h3 className="text-[13px] font-semibold text-apple-dark mb-4">이슈별 해결시간 상세</h3>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-apple-divider/60">
              {['키', '요약', '유형', '해결시간', '상태'].map(h => (
                <th key={h} className="text-left pb-3 text-[11px] font-semibold text-apple-light uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-apple-divider/40">
            {details.map((d) => (
              <tr key={d.key} className="hover:bg-apple-gray/50 transition-colors duration-150">
                <td className="py-2.5 text-[12px] font-mono text-brand-600 font-medium">{d.key}</td>
                <td className="py-2.5 text-[12px] max-w-xs truncate text-apple-dark/80 pr-4">{d.summary}</td>
                <td className="py-2.5 text-[12px] text-apple-light">{d.type}</td>
                <td className="py-2.5 text-[12px] text-apple-dark/80 tabular-nums">{d.resolution_h ? `${d.resolution_h}h` : '—'}</td>
                <td className="py-2.5">
                  <span className={d.res_breached ? 'badge-critical' : 'badge-good'}>
                    {d.res_breached ? 'SLA 위반' : 'SLA 만족'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
