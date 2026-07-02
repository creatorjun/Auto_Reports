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
      <h3 className="text-sm font-semibold text-gray-700 mb-3">📋 이슈별 해결시간 상세</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left border-b border-gray-100">
              <th className="pb-2 font-semibold text-gray-500">키</th>
              <th className="pb-2 font-semibold text-gray-500">요약</th>
              <th className="pb-2 font-semibold text-gray-500">유형</th>
              <th className="pb-2 font-semibold text-gray-500">해결시간</th>
              <th className="pb-2 font-semibold text-gray-500">상태</th>
            </tr>
          </thead>
          <tbody>
            {details.map((d) => (
              <tr key={d.key} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="py-1.5 font-mono text-brand-600">{d.key}</td>
                <td className="py-1.5 max-w-xs truncate text-gray-600">{d.summary}</td>
                <td className="py-1.5 text-gray-500">{d.type}</td>
                <td className="py-1.5">{d.resolution_h ? `${d.resolution_h}h` : '-'}</td>
                <td className="py-1.5">
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
