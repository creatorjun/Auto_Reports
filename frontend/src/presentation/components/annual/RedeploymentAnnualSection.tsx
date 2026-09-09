// frontend/src/presentation/components/annual/RedeploymentAnnualSection.tsx
import { useState } from 'react'
import { AlertTriangle, BarChart3, CheckCircle2, Percent, RotateCcw } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
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
import { useDashboardExportMode } from '@/presentation/context/DashboardExportContext'
import {
  CHART_HEIGHT,
  CHART_LEGEND_COLOR,
} from '@/presentation/config/constants'
import { CHART_COLORS } from '@/presentation/config/ui'

interface Props {
  data: RedeploymentAnalytics
  year: number
}

const REDEPLOYMENT_PAGE_SIZE = 5
const REDEPLOYMENT_FONT_SIZE = 13
const REDEPLOYMENT_LEGEND_ICON_SIZE = 10
const REDEPLOYMENT_CHART_COLORS = [
  'rgb(var(--color-redeployment-blue))',
  'rgb(var(--color-redeployment-amber))',
  'rgb(var(--color-redeployment-green))',
  'rgb(var(--color-redeployment-purple))',
  'rgb(var(--color-redeployment-coral))',
  'rgb(var(--color-redeployment-teal))',
  'rgb(var(--color-redeployment-pink))',
  'rgb(var(--color-redeployment-olive))',
  'rgb(var(--color-redeployment-indigo))',
  'rgb(var(--color-redeployment-brown))',
  'rgb(var(--color-redeployment-cyan))',
  'rgb(var(--color-redeployment-slate))',
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
    <div data-pdf-metric="" data-pdf-label={label} data-pdf-value={`${typeof value === 'number' ? value.toLocaleString('ko-KR') : value}${unit}`} className="card flex min-h-28 items-center justify-between gap-4">
      <div className="min-w-0">
        <p className="text-sm font-semibold text-apple-dark">{label}</p>
        <p className="mt-2 text-3xl font-semibold leading-tight tabular-nums text-apple-dark">
          {typeof value === 'number' ? value.toLocaleString('ko-KR') : value}
          {unit && <span className="ml-1.5 text-sm font-medium text-apple-mid">{unit}</span>}
        </p>
      </div>
      <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${tone}`}>
        {icon}
      </span>
    </div>
  )
}

function MonthlyRedeploymentChart({ data }: { data: RedeploymentAnalytics }) {
  const exportMode = useDashboardExportMode()
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
    <div data-pdf-kind="chart" className="card">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 className="text-ui-base font-semibold text-apple-dark">월별 재배포 추이</h3>
          <p className="mt-1 text-sm text-apple-mid">요청 유형별 월간 재배포 건수</p>
        </div>
        <span className="rounded-lg bg-apple-gray px-3 py-1.5 text-sm font-semibold tabular-nums text-apple-dark">통계 대상 {data.analytics_total.toLocaleString('ko-KR')}건</span>
      </div>
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <BarChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
          <XAxis dataKey="month" tick={{ fontSize: REDEPLOYMENT_FONT_SIZE, fill: CHART_COLORS.axisText }} axisLine={false} tickLine={false} minTickGap={18} />
          <YAxis allowDecimals={false} tick={{ fontSize: REDEPLOYMENT_FONT_SIZE, fill: CHART_COLORS.axisText }} axisLine={false} tickLine={false} width={46} />
          <Tooltip formatter={(value, name) => [`${Number(value).toLocaleString('ko-KR')}건`, String(name)]} />
          <Legend iconType="circle" iconSize={REDEPLOYMENT_LEGEND_ICON_SIZE} formatter={(value: string) => <span style={{ color: CHART_LEGEND_COLOR, fontSize: REDEPLOYMENT_FONT_SIZE, fontWeight: 500 }}>{value}</span>} />
          {issueTypes.map((issueType, index) => (
            <Bar isAnimationActive={!exportMode} key={issueType} dataKey={issueType} stackId="redeployment" fill={REDEPLOYMENT_CHART_COLORS[index % REDEPLOYMENT_CHART_COLORS.length]} stroke="rgb(var(--color-apple-surface))" strokeWidth={1} radius={index === issueTypes.length - 1 ? [5, 5, 0, 0] : 0} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function CauseChart({ values }: { values: Record<string, number> }) {
  const exportMode = useDashboardExportMode()
  const data = Object.entries(values).map(([name, value]) => ({ name, value }))
  const total = data.reduce((sum, entry) => sum + entry.value, 0)
  return (
    <div data-pdf-kind="chart" className="card">
      <h3 className="text-ui-base font-semibold text-apple-dark">재배포 원인</h3>
      <p className="mt-1 text-sm text-apple-mid">원인별 건수와 구성비</p>
      {data.length ? (
        <div>
          <ResponsiveContainer width="100%" height={exportMode ? CHART_HEIGHT + 24 : CHART_HEIGHT - 72}>
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" outerRadius={118} paddingAngle={1} isAnimationActive={!exportMode} stroke="rgb(var(--color-apple-surface))" strokeWidth={2}>
                {data.map((entry, index) => <Cell key={entry.name} fill={REDEPLOYMENT_CHART_COLORS[index % REDEPLOYMENT_CHART_COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(value, name) => [`${Number(value).toLocaleString('ko-KR')}건`, String(name)]} />
              {exportMode && <Legend iconType="circle" iconSize={REDEPLOYMENT_LEGEND_ICON_SIZE} wrapperStyle={{ paddingTop: 8 }} formatter={(value: string) => <span style={{ color: CHART_LEGEND_COLOR, fontSize: REDEPLOYMENT_FONT_SIZE, fontWeight: 500 }}>{value}</span>} />}
            </PieChart>
          </ResponsiveContainer>
          {!exportMode && <ul className="divide-y divide-apple-divider/70 border-t border-apple-divider/70">
            {data.map((entry, index) => (
              <li key={entry.name} className="flex items-center gap-3 py-2.5 text-sm">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: REDEPLOYMENT_CHART_COLORS[index % REDEPLOYMENT_CHART_COLORS.length] }} />
                <span className="min-w-0 flex-1 break-words font-medium text-apple-dark">{entry.name}</span>
                <span className="shrink-0 font-semibold tabular-nums text-apple-dark">{entry.value.toLocaleString('ko-KR')}건</span>
                <span className="w-14 shrink-0 text-right tabular-nums text-apple-mid">{total > 0 ? (entry.value / total * 100).toFixed(1) : '0.0'}%</span>
              </li>
            ))}
          </ul>}
        </div>
      ) : <div className="flex items-center justify-center text-ui-sm text-apple-light" style={{ height: CHART_HEIGHT }}>데이터가 없습니다</div>}
    </div>
  )
}

function AssigneeChart({ values }: { values: Record<string, number> }) {
  const exportMode = useDashboardExportMode()
  const data = Object.entries(values).slice(0, 10).map(([name, value]) => ({ name, value }))
  const axisWidth = exportMode ? 156 : 120
  const exportTickLimit = Math.floor((axisWidth - 16) / 14)
  const formatExportTick = (value: string) => {
    const characters = Array.from(value)
    return characters.length > exportTickLimit
      ? `${characters.slice(0, exportTickLimit - 1).join('')}…`
      : value
  }
  return (
    <div data-pdf-kind="chart" className="card">
      <h3 className="text-ui-base font-semibold text-apple-dark">담당자별 재배포</h3>
      <p className="mt-1 text-sm text-apple-mid">상위 10명 기준 · 건수</p>
      {data.length ? (
        <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
          <BarChart data={data} layout="vertical" margin={{ top: 12, right: 44, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} horizontal={false} />
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: REDEPLOYMENT_FONT_SIZE, fill: CHART_COLORS.axisText }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="name" width={axisWidth} tick={{ fontSize: REDEPLOYMENT_FONT_SIZE, fill: CHART_COLORS.axisText }} tickFormatter={exportMode ? formatExportTick : undefined} axisLine={false} tickLine={false} interval={0} />
            <Tooltip formatter={(value) => [`${Number(value).toLocaleString('ko-KR')}건`, '재배포']} />
            {exportMode && (
              <Legend
                iconType="circle"
                iconSize={REDEPLOYMENT_LEGEND_ICON_SIZE}
                payload={data.map((entry, index) => ({ value: entry.name, type: 'circle', color: REDEPLOYMENT_CHART_COLORS[index % REDEPLOYMENT_CHART_COLORS.length] }))}
                formatter={(value: string) => <span style={{ color: CHART_LEGEND_COLOR, fontSize: REDEPLOYMENT_FONT_SIZE, fontWeight: 500 }}>{value}</span>}
              />
            )}
            <Bar isAnimationActive={!exportMode} dataKey="value" radius={[0, 6, 6, 0]}>
              {data.map((entry, index) => <Cell key={entry.name} fill={REDEPLOYMENT_CHART_COLORS[index % REDEPLOYMENT_CHART_COLORS.length]} />)}
              <LabelList dataKey="value" position="right" fill={CHART_COLORS.axisText} fontSize={REDEPLOYMENT_FONT_SIZE} formatter={(value: unknown) => Number(value).toLocaleString('ko-KR')} />
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
    <div data-pdf-kind="table" data-pdf-title="파트너사별 재배포 히트맵" className="card overflow-hidden">
      <div className="mb-4">
        <h3 className="text-ui-base font-semibold text-apple-dark">파트너사별 재배포 히트맵</h3>
        <p className="mt-1 text-sm text-apple-mid">파트너사별 요청 유형과 합계 · 단위: 건</p>
      </div>
      {partners.length ? (
        <div className="overflow-x-auto rounded-xl border border-apple-divider/70">
          <table className="w-full min-w-[640px] border-collapse text-center text-sm">
            <thead className="bg-apple-gray text-apple-dark">
              <tr>
                <th scope="col" className="sticky left-0 z-10 min-w-40 bg-apple-gray px-4 py-3.5 text-left font-semibold">파트너사</th>
                {issueTypes.map((issueType) => <th key={issueType} scope="col" className="whitespace-nowrap px-4 py-3.5 font-semibold">{issueType}</th>)}
                <th scope="col" className="px-4 py-3.5 font-semibold">합계</th>
              </tr>
            </thead>
            <tbody>
              {partners.map(([partner, counts]) => {
                const total = Object.values(counts).reduce((sum, count) => sum + count, 0)
                return (
                  <tr key={partner} className="border-t border-apple-divider/60">
                    <th scope="row" className="sticky left-0 z-10 min-w-40 max-w-[260px] break-words bg-apple-surface px-4 py-3.5 text-left font-medium leading-relaxed text-apple-dark">{partner}</th>
                    {issueTypes.map((issueType) => {
                      const count = counts[issueType] ?? 0
                      const opacity = count ? 0.12 + (count / maxCount) * 0.54 : 0
                      return <td key={issueType} className="px-4 py-3.5 font-semibold tabular-nums text-apple-dark" style={{ backgroundColor: `rgb(var(--color-chart-muted-steel) / ${opacity})` }}>{count || '–'}</td>
                    })}
                    <td className="bg-apple-gray/50 px-4 py-3.5 font-bold tabular-nums text-apple-dark">{total.toLocaleString('ko-KR')}</td>
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
  const exportMode = useDashboardExportMode()
  const { jiraBrowse } = useJira()
  const [page, setPage] = useState(1)
  const issues = data.latest_issues.filter((issue) => !isDashboardExcludedIssueType(issue.type))
  const totalPages = Math.max(1, Math.ceil(issues.length / REDEPLOYMENT_PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const visibleIssues = exportMode ? issues : issues.slice(
    (currentPage - 1) * REDEPLOYMENT_PAGE_SIZE,
    currentPage * REDEPLOYMENT_PAGE_SIZE,
  )
  return (
    <div data-pdf-kind="table" data-pdf-title="최근 완료 재배포 이슈" className="card overflow-hidden">
      <div className="mb-4">
        <h3 className="text-ui-base font-semibold text-apple-dark">최근 완료 재배포 이슈</h3>
        <p className="mt-1 text-sm text-apple-mid">완료 월 기준 · 총 {issues.length.toLocaleString('ko-KR')}건</p>
      </div>
      {issues.length ? (
        <>
          <div className="overflow-x-auto">
            <table data-pdf-table-layout="redeployment" className="w-full min-w-[760px] border-collapse text-sm">
              <thead className="border-y border-apple-divider/70 bg-apple-gray text-apple-dark">
                <tr>
                  <th scope="col" className="whitespace-nowrap px-3 py-3.5 text-center font-semibold">완료 월</th>
                  <th scope="col" className="px-3 py-3.5 text-center font-semibold">유형</th>
                  <th scope="col" className="px-3 py-3.5 text-center font-semibold">티켓</th>
                  <th scope="col" className="px-3 py-3.5 text-left font-semibold">제목</th>
                  <th scope="col" className="whitespace-nowrap px-3 py-3.5 text-center font-semibold">우선순위</th>
                  <th scope="col" className="whitespace-nowrap px-3 py-3.5 text-center font-semibold">재배포 원인</th>
                </tr>
              </thead>
              <tbody>
                {visibleIssues.map((issue) => (
                  <tr key={issue.key} className="border-b border-apple-divider/60 transition-colors hover:bg-[rgb(var(--color-chart-muted-steel)/0.08)]">
                    <td className="whitespace-nowrap px-3 py-4 text-center tabular-nums text-apple-dark">{issue.month}</td>
                    <td className="px-3 py-4 text-center"><IssueTypeBadge type={issue.type} /></td>
                    <td className="whitespace-nowrap px-3 py-4 text-center"><a className="rounded font-mono font-semibold text-apple-dark underline decoration-apple-divider underline-offset-4 hover:decoration-current focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500" href={`${jiraBrowse}/${issue.key}`} target="_blank" rel="noopener noreferrer">{issue.key}</a></td>
                    <td className="min-w-[240px] max-w-[440px] break-words px-3 py-4 leading-relaxed text-apple-dark">{issue.summary}</td>
                    <td className="whitespace-nowrap px-3 py-4 text-center text-apple-dark">{issue.priority}</td>
                    <td className="min-w-28 px-3 py-4 text-center leading-relaxed text-apple-dark">{issue.cause}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!exportMode && totalPages > 1 && (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-apple-divider pt-4">
              <span className="text-sm tabular-nums text-apple-mid">
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
                      aria-current={currentPage === pageNumber ? 'page' : undefined}
                      onClick={() => setPage(pageNumber)}
                      className={`min-h-10 min-w-10 rounded-lg px-3 py-2 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 ${
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
    <section data-pdf-section={`${year}년 재배포 품질 지표`} className="redeployment-analytics space-y-4 md:space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-apple-divider pt-6">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[rgb(var(--color-chart-muted-steel)/0.12)] text-[rgb(var(--color-chart-muted-steel))]"><BarChart3 size={20} /></span>
          <div>
            <h2 className="text-xl font-semibold text-apple-dark">{year}년 재배포 품질 지표</h2>
            <p className="mt-1 text-sm text-apple-mid">재배포 규모와 원인, 담당자 및 파트너사별 현황</p>
          </div>
        </div>
        <span className="rounded-lg bg-apple-gray px-3 py-1.5 text-sm font-medium text-apple-dark">연간 전체 기준</span>
      </div>
      <div data-pdf-kind="metrics" className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <KpiCard label="전체 해결 이슈" value={data.resolved_total} unit="건" icon={<CheckCircle2 size={21} />} tone="bg-[rgb(var(--color-chart-muted-sage)/0.16)] text-[rgb(var(--color-chart-muted-sage))]" />
        <KpiCard label="재배포 이슈" value={classificationComplete ? data.redeployment_total : '집계 불가'} unit={classificationComplete ? '건' : ''} icon={<RotateCcw size={21} />} tone="bg-[rgb(var(--color-chart-muted-taupe)/0.16)] text-[rgb(var(--color-chart-muted-taupe))]" />
        <KpiCard label="재배포율" value={classificationComplete ? data.redeployment_rate : '집계 불가'} unit={classificationComplete ? '%' : ''} icon={<Percent size={21} />} tone="bg-[rgb(var(--color-chart-muted-steel)/0.16)] text-[rgb(var(--color-chart-muted-steel))]" />
      </div>
      {!classificationComplete ? (
        <div data-pdf-kind="text" className="card flex min-h-44 flex-col items-center justify-center gap-2 text-center">
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
        <div data-pdf-kind="text" className="card flex min-h-40 flex-col items-center justify-center gap-2 text-center">
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[rgb(var(--color-chart-muted-sage)/0.16)] text-[rgb(var(--color-chart-muted-sage))]"><CheckCircle2 size={22} /></span>
          <p className="text-ui-base font-semibold text-apple-dark">{year}년 재배포 이슈가 없습니다</p>
        </div>
      )}
    </section>
  )
}
