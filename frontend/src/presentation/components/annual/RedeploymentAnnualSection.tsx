// frontend/src/presentation/components/annual/RedeploymentAnnualSection.tsx
import { useState } from 'react'
import { AlertTriangle, BarChart3, CheckCircle2, Percent, RotateCcw } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { RedeploymentAnalytics } from '@/domain/Dashboard'
import { isDashboardExcludedIssueType } from '@/domain/DashboardIssueTypePolicy'
import { IssueTypeBadge } from '@/presentation/components/common/IssueTypeBadge'
import { useJira } from '@/presentation/context/JiraContext'
import {
  CHART_HEIGHT,
  CHART_LEGEND_COLOR,
  CHART_LEGEND_ICON_SIZE,
  CHART_TICK_FONT_SIZE,
} from '@/presentation/config/constants'
import { CHART_COLORS } from '@/presentation/config/ui'

interface Props {
  data: RedeploymentAnalytics
  year: number
}

const REDEPLOYMENT_PAGE_SIZE = 5
const REDEPLOYMENT_CHART_COLORS = [
  'rgb(var(--color-chart-muted-steel))',
  'rgb(var(--color-chart-muted-sage))',
  'rgb(var(--color-chart-muted-taupe))',
  'rgb(var(--color-chart-muted-mauve))',
  'rgb(var(--color-chart-muted-olive))',
  'rgb(var(--color-chart-muted-teal))',
] as const

function KpiCard({
  label,
  value,
  unit,
  icon,
  tone,
}: {
  label: string
  value: number | string
  unit: string
  icon: React.ReactNode
  tone: string
}) {
  return (
    <div className="card flex items-center justify-between gap-4">
      <div>
        <p className="text-[12px] font-medium text-apple-light">{label}</p>
        <p className="mt-1 text-2xl font-semibold tabular-nums text-apple-dark">
          {typeof value === 'number' ? value.toLocaleString('ko-KR') : value}
          {unit && <span className="ml-1 text-sm font-medium text-apple-light">{unit}</span>}
        </p>
      </div>
      <span className={`flex h-11 w-11 items-center justify-center rounded-2xl ${tone}`}>
        {icon}
      </span>
    </div>
  )
}

function MonthlyRedeploymentChart({ data }: { data: RedeploymentAnalytics }) {
  const issueTypes = Array.from(new Set(
    data.monthly.flatMap((entry) => Object.keys(entry.by_type))
      .filter((issueType) => !isDashboardExcludedIssueType(issueType)),
  ))
  const chartData = data.monthly.map((entry) => {
    const byType = Object.fromEntries(
      Object.entries(entry.by_type)
        .filter(([issueType]) => !isDashboardExcludedIssueType(issueType)),
    )
    return {
      month: entry.month,
      total: Object.values(byType).reduce((sum, count) => sum + count, 0),
      ...byType,
    }
  })
  return (
    <div className="card">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 className="text-ui-base font-semibold text-apple-dark">월별 재배포 추이</h3>
          <p className="mt-0.5 text-ui-xs text-apple-light">요청 유형별 누적 막대</p>
        </div>
        <span className="text-ui-xs font-medium tabular-nums text-[rgb(var(--color-chart-muted-steel))]">통계 대상 {data.analytics_total}건</span>
      </div>
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <BarChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
          <XAxis dataKey="month" tick={{ fontSize: CHART_TICK_FONT_SIZE, fill: CHART_COLORS.axisText }} axisLine={false} tickLine={false} />
          <YAxis allowDecimals={false} tick={{ fontSize: CHART_TICK_FONT_SIZE, fill: CHART_COLORS.axisText }} axisLine={false} tickLine={false} width={34} />
          <Tooltip formatter={(value, name) => [`${Number(value).toLocaleString('ko-KR')}건`, String(name)]} />
          <Legend iconType="circle" iconSize={CHART_LEGEND_ICON_SIZE} formatter={(value: string) => <span style={{ color: CHART_LEGEND_COLOR, fontSize: 11 }}>{value}</span>} />
          {issueTypes.map((issueType, index) => (
            <Bar key={issueType} dataKey={issueType} stackId="redeployment" fill={REDEPLOYMENT_CHART_COLORS[index % REDEPLOYMENT_CHART_COLORS.length]} radius={index === issueTypes.length - 1 ? [5, 5, 0, 0] : 0} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function CauseChart({ values }: { values: Record<string, number> }) {
  const data = Object.entries(values).map(([name, value]) => ({ name, value }))
  return (
    <div className="card">
      <h3 className="text-ui-base font-semibold text-apple-dark">재배포 원인</h3>
      <p className="mt-0.5 text-ui-xs text-apple-light">원인별 건수와 구성비</p>
      {data.length ? (
        <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" outerRadius={118} paddingAngle={1}>
              {data.map((entry, index) => <Cell key={entry.name} fill={REDEPLOYMENT_CHART_COLORS[index % REDEPLOYMENT_CHART_COLORS.length]} />)}
            </Pie>
            <Tooltip formatter={(value, name) => [`${Number(value).toLocaleString('ko-KR')}건`, String(name)]} />
            <Legend iconType="circle" iconSize={CHART_LEGEND_ICON_SIZE} formatter={(value: string) => <span style={{ color: CHART_LEGEND_COLOR, fontSize: 11 }}>{value}</span>} />
          </PieChart>
        </ResponsiveContainer>
      ) : <div className="flex items-center justify-center text-ui-sm text-apple-light" style={{ height: CHART_HEIGHT }}>데이터가 없습니다</div>}
    </div>
  )
}

function AssigneeChart({ values }: { values: Record<string, number> }) {
  const data = Object.entries(values).slice(0, 10).map(([name, value]) => ({ name, value }))
  return (
    <div className="card">
      <h3 className="text-ui-base font-semibold text-apple-dark">담당자별 재배포</h3>
      <p className="mt-0.5 text-ui-xs text-apple-light">상위 10명 기준</p>
      {data.length ? (
        <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
          <BarChart data={data} layout="vertical" margin={{ top: 12, right: 24, left: 18, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} horizontal={false} />
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: CHART_TICK_FONT_SIZE, fill: CHART_COLORS.axisText }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="name" width={92} tick={{ fontSize: CHART_TICK_FONT_SIZE, fill: CHART_COLORS.axisText }} axisLine={false} tickLine={false} />
            <Tooltip formatter={(value) => [`${Number(value).toLocaleString('ko-KR')}건`, '재배포']} />
            <Bar dataKey="value" radius={[0, 6, 6, 0]}>
              {data.map((entry, index) => <Cell key={entry.name} fill={REDEPLOYMENT_CHART_COLORS[index % REDEPLOYMENT_CHART_COLORS.length]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : <div className="flex items-center justify-center text-ui-sm text-apple-light" style={{ height: CHART_HEIGHT }}>데이터가 없습니다</div>}
    </div>
  )
}

function PartnerMatrix({ matrix }: { matrix: Record<string, Record<string, number>> }) {
  const partners = Object.entries(matrix).map(([partner, counts]) => ([
    partner,
    Object.fromEntries(
      Object.entries(counts)
        .filter(([issueType]) => !isDashboardExcludedIssueType(issueType)),
    ),
  ] as const)).filter(([, counts]) => Object.keys(counts).length > 0)
  const issueTypes = Array.from(new Set(partners.flatMap(([, counts]) => Object.keys(counts))))
  const maxCount = Math.max(1, ...partners.flatMap(([, counts]) => Object.values(counts)))
  return (
    <div className="card overflow-hidden">
      <div className="mb-4">
        <h3 className="text-ui-base font-semibold text-apple-dark">파트너사별 재배포 히트맵</h3>
        <p className="mt-0.5 text-ui-xs text-apple-light">파트너사 × 요청 유형 교차 통계</p>
      </div>
      {partners.length ? (
        <div className="overflow-x-auto rounded-xl border border-apple-divider/70">
          <table className="w-full min-w-[640px] border-collapse text-center text-ui-xs">
            <thead className="bg-apple-gray/70 text-apple-mid">
              <tr>
                <th className="px-4 py-3 text-left font-semibold">파트너사</th>
                {issueTypes.map((issueType) => <th key={issueType} className="px-3 py-3 font-semibold">{issueType}</th>)}
                <th className="px-3 py-3 font-semibold">합계</th>
              </tr>
            </thead>
            <tbody>
              {partners.map(([partner, counts]) => {
                const total = Object.values(counts).reduce((sum, count) => sum + count, 0)
                return (
                  <tr key={partner} className="border-t border-apple-divider/60">
                    <th className="max-w-[260px] truncate px-4 py-3 text-left font-medium text-apple-dark" title={partner}>{partner}</th>
                    {issueTypes.map((issueType) => {
                      const count = counts[issueType] ?? 0
                      const opacity = count ? 0.12 + (count / maxCount) * 0.54 : 0
                      return <td key={issueType} className="px-3 py-3 font-semibold tabular-nums text-apple-dark" style={{ backgroundColor: `rgb(var(--color-chart-muted-steel) / ${opacity})` }}>{count || '–'}</td>
                    })}
                    <td className="px-3 py-3 font-semibold tabular-nums text-[rgb(var(--color-chart-muted-steel))]">{total}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : <p className="py-12 text-center text-ui-sm text-apple-light">파트너사 데이터가 없습니다</p>}
    </div>
  )
}

function LatestIssues({ data }: { data: RedeploymentAnalytics }) {
  const { jiraBrowse } = useJira()
  const [page, setPage] = useState(1)
  const issues = data.latest_issues.filter((issue) => !isDashboardExcludedIssueType(issue.type))
  const totalPages = Math.max(1, Math.ceil(issues.length / REDEPLOYMENT_PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const visibleIssues = issues.slice(
    (currentPage - 1) * REDEPLOYMENT_PAGE_SIZE,
    currentPage * REDEPLOYMENT_PAGE_SIZE,
  )
  return (
    <div className="card overflow-hidden">
      <div className="mb-4">
        <h3 className="text-ui-base font-semibold text-apple-dark">최근 완료 재배포 이슈</h3>
        <p className="mt-0.5 text-ui-xs text-apple-light">완료 월 기준 · 총 {issues.length.toLocaleString('ko-KR')}건</p>
      </div>
      {issues.length ? (
        <>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse text-ui-sm">
              <thead className="border-y border-apple-divider/70 bg-apple-gray/50 text-apple-mid">
                <tr>
                  <th className="px-3 py-3 text-center text-ui-xs font-semibold">완료 월</th>
                  <th className="px-3 py-3 text-center text-ui-xs font-semibold">유형</th>
                  <th className="px-3 py-3 text-center text-ui-xs font-semibold">티켓</th>
                  <th className="px-3 py-3 text-left text-ui-xs font-semibold">제목</th>
                  <th className="px-3 py-3 text-center text-ui-xs font-semibold">우선순위</th>
                  <th className="px-3 py-3 text-center text-ui-xs font-semibold">재배포 원인</th>
                </tr>
              </thead>
              <tbody>
                {visibleIssues.map((issue) => (
                  <tr key={issue.key} className="border-b border-apple-divider/60 transition-colors hover:bg-[rgb(var(--color-chart-muted-steel)/0.08)]">
                    <td className="px-3 py-3 text-center tabular-nums text-apple-light">{issue.month}</td>
                    <td className="px-3 py-3 text-center"><IssueTypeBadge type={issue.type} /></td>
                    <td className="px-3 py-3 text-center"><a className="font-mono font-medium text-[rgb(var(--color-chart-muted-steel))] hover:underline" href={`${jiraBrowse}/${issue.key}`} target="_blank" rel="noopener noreferrer">{issue.key}</a></td>
                    <td className="max-w-[360px] truncate px-3 py-3 text-apple-dark" title={issue.summary}>{issue.summary}</td>
                    <td className="px-3 py-3 text-center text-apple-light">{issue.priority}</td>
                    <td className="px-3 py-3 text-center text-apple-light">{issue.cause}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-apple-divider pt-4">
              <span className="text-ui-xs tabular-nums text-apple-light">
                {(currentPage - 1) * REDEPLOYMENT_PAGE_SIZE + 1}–{Math.min(currentPage * REDEPLOYMENT_PAGE_SIZE, issues.length)} / {issues.length}건
              </span>
              <div className="flex flex-wrap gap-1">
                {Array.from({ length: totalPages }).map((_, index) => {
                  const pageNumber = index + 1
                  return (
                    <button
                      key={pageNumber}
                      type="button"
                      aria-label={`${pageNumber}페이지`}
                      onClick={() => setPage(pageNumber)}
                      className={`min-w-8 rounded-lg px-2.5 py-1.5 text-ui-sm font-medium transition-colors ${
                        currentPage === pageNumber
                          ? 'bg-[rgb(var(--color-chart-muted-steel))] text-white'
                          : 'bg-apple-gray text-apple-mid hover:bg-[rgb(var(--color-chart-muted-steel)/0.12)] hover:text-[rgb(var(--color-chart-muted-steel))]'
                      }`}
                    >
                      {pageNumber}
                    </button>
                  )
                })}
              </div>
            </div>
          )}
        </>
      ) : <p className="py-12 text-center text-ui-sm text-apple-light">완료된 재배포 이슈가 없습니다</p>}
    </div>
  )
}

export default function RedeploymentAnnualSection({ data, year }: Props) {
  const classificationComplete = data.classification_complete
  return (
    <section className="space-y-4 md:space-y-5">
      <div className="flex items-center gap-2">
        <BarChart3 size={18} className="text-[rgb(var(--color-chart-muted-steel))]" />
        <h2 className="text-xl font-semibold text-apple-dark">{year}년 재배포 품질 지표</h2>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <KpiCard label="전체 해결 이슈" value={data.resolved_total} unit="건" icon={<CheckCircle2 size={21} />} tone="bg-[rgb(var(--color-chart-muted-sage)/0.16)] text-[rgb(var(--color-chart-muted-sage))]" />
        <KpiCard label="재배포 이슈" value={classificationComplete ? data.redeployment_total : '집계 불가'} unit={classificationComplete ? '건' : ''} icon={<RotateCcw size={21} />} tone="bg-[rgb(var(--color-chart-muted-taupe)/0.16)] text-[rgb(var(--color-chart-muted-taupe))]" />
        <KpiCard label="재배포율" value={classificationComplete ? data.redeployment_rate : '집계 불가'} unit={classificationComplete ? '%' : ''} icon={<Percent size={21} />} tone="bg-[rgb(var(--color-chart-muted-steel)/0.16)] text-[rgb(var(--color-chart-muted-steel))]" />
      </div>
      {!classificationComplete ? (
        <div className="card flex min-h-44 flex-col items-center justify-center gap-2 text-center">
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[rgb(var(--color-chart-muted-olive)/0.16)] text-[rgb(var(--color-chart-muted-olive))]"><AlertTriangle size={22} /></span>
          <p className="text-ui-base font-semibold text-apple-dark">{year}년 재배포 원천 데이터가 기록되지 않았습니다</p>
        </div>
      ) : data.redeployment_total > 0 ? (
        <>
          <MonthlyRedeploymentChart data={data} />
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <CauseChart values={data.by_cause} />
            <AssigneeChart values={data.by_assignee} />
          </div>
          <PartnerMatrix matrix={data.partner_matrix} />
          <LatestIssues key={year} data={data} />
        </>
      ) : (
        <div className="card flex min-h-40 flex-col items-center justify-center gap-2 text-center">
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[rgb(var(--color-chart-muted-sage)/0.16)] text-[rgb(var(--color-chart-muted-sage))]"><CheckCircle2 size={22} /></span>
          <p className="text-ui-base font-semibold text-apple-dark">{year}년 재배포 이슈가 없습니다</p>
        </div>
      )}
    </section>
  )
}
