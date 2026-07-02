import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts'

interface IssueDetail {
  key: string
  summary: string
  type: string
  resolution_h: number
  res_breached: boolean
}

export default function ResolutionTimeChart({ details }: { details: IssueDetail[] }) {
  if (!details?.length) return null
  const data = details.slice(0, 15).map(d => ({
    key: d.key,
    hours: d.resolution_h,
    fill: d.res_breached ? '#ef4444' : '#22c55e'
  }))
  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">🕐 해결시간 분포 (상위 15건)</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="key" tick={{ fontSize: 9 }} angle={-35} textAnchor="end" />
          <YAxis tick={{ fontSize: 11 }} unit="h" />
          <Tooltip formatter={(v) => [`${v}h`]} />
          <ReferenceLine y={720} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: 'SLA 30d', fontSize: 10 }} />
          <Bar dataKey="hours" radius={[4, 4, 0, 0]}>
            {data.map((d, i) => <Cell key={i} fill={d.fill} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="text-xs text-gray-400 mt-1">🟥 SLA 위반   🟢 SLA 만족</p>
    </div>
  )
}
