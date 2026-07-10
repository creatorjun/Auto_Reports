// frontend/src/presentation/components/charts/TrendLineChart.tsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts'

interface Props {
  created: number
  resolved: number
  onBarClick?: (key: '생성' | '해결') => void
}

export default function TrendLineChart({ created, resolved, onBarClick }: Props) {
  const data = [
    { name: '이번 주', '생성': created, '해결': resolved },
  ]

  const handleClick = (payload: { activeDataKey?: string }) => {
    const key = payload?.activeDataKey
    if (key === '생성' || key === '해결') onBarClick?.(key)
  }

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">⚖️ 생성 vs 해결</h3>
      <ResponsiveContainer width="100%" height={360}>
        <BarChart data={data} onClick={onBarClick ? handleClick : undefined}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend
            layout="horizontal"
            verticalAlign="bottom"
            align="center"
            iconType="circle"
            iconSize={7}
            formatter={(value: string) => (
              <span
                style={{ fontSize: 11, color: '#86868b', cursor: onBarClick ? 'pointer' : 'default' }}
                onClick={() => {
                  if (value === '생성' || value === '해결') onBarClick?.(value)
                }}
              >
                {value}
              </span>
            )}
          />
          <Bar dataKey="생성" fill="#3b82f6" radius={[6, 6, 0, 0]} style={onBarClick ? { cursor: 'pointer' } : undefined}>
            {data.map((_, i) => <Cell key={i} />)}
          </Bar>
          <Bar dataKey="해결" fill="#22c55e" radius={[6, 6, 0, 0]} style={onBarClick ? { cursor: 'pointer' } : undefined}>
            {data.map((_, i) => <Cell key={i} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {onBarClick && (
        <p className="text-center text-[11px] text-apple-light mt-1">막대를 클릭하면 이슈 목록을 확인할 수 있습니다</p>
      )}
    </div>
  )
}
