// frontend/src/presentation/components/annual/RedeploymentAnnualSection.tsx
import { useId, useState } from 'react'
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
import type { RedeploymentAnalytics, RedeploymentIssue, RedeploymentMonthlyEntry } from '@/domain/Dashboard'
import type { ChartIssuesRequest } from '@/domain/ReportChartDetails'
import { isDashboardExcludedIssueType } from '@/domain/DashboardIssueTypePolicy'
import { IssueTypeBadge } from '@/presentation/components/common/IssueTypeBadge'
import { useJira } from '@/presentation/context/JiraContext'
import { useDashboardExportMode } from '@/presentation/context/DashboardExportContext'
import {
  CHART_HEIGHT,
  CHART_LEGEND_COLOR,
  CATEGORICAL_CHART_COLORS,
} from '@/presentation/config/constants'
import { CHART_COLORS } from '@/presentation/config/ui'
import AnnualIssueDetailsModal from './AnnualIssueDetailsModal'
import AnnualRemoteIssueDetailsModal from './AnnualRemoteIssueDetailsModal'

interface Props {
  data: RedeploymentAnalytics
  year: number
  reportId: number
}

const REDEPLOYMENT_PAGE_SIZE = 5
const REDEPLOYMENT_FONT_SIZE = 13
const REDEPLOYMENT_LEGEND_ICON_SIZE = 10

interface IssueDetails {
  title: string
  total: number
  issues: RedeploymentIssue[]
  request?: ChartIssuesRequest
}

type ShowBreakdown = (name: string | undefined, total: number) => void

const DETAILS_BUTTON_CLASS = 'min-h-11 rounded-lg px-3 py-2 text-sm font-semibold text-apple-dark underline decoration-apple-divider underline-offset-4 transition-colors hover:bg-apple-gray focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500'

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

function MonthlyRedeploymentChart({ data, onDetails }: { data: RedeploymentAnalytics; onDetails: (month: RedeploymentMonthlyEntry, issueType?: string) => void }) {
  const exportMode = useDashboardExportMode()
  const controlId = useId()
  const [monthIndex, setMonthIndex] = useState(0)
  const [selectedType, setSelectedType] = useState('')
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
  const selectedMonth = data.monthly[monthIndex] ?? data.monthly[0]
  const selectedCount = selectedMonth
    ? selectedType
      ? selectedMonth.by_type[selectedType] ?? 0
      : Object.entries(selectedMonth.by_type)
        .filter(([issueType]) => !isDashboardExcludedIssueType(issueType))
        .reduce((sum, [, count]) => sum + count, 0)
    : 0
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
            <Bar isAnimationActive={!exportMode} key={issueType} dataKey={issueType} stackId="redeployment" fill={CATEGORICAL_CHART_COLORS[index % CATEGORICAL_CHART_COLORS.length]} stroke="rgb(var(--color-apple-surface))" strokeWidth={1} radius={index === issueTypes.length - 1 ? [5, 5, 0, 0] : 0} cursor={exportMode ? undefined : 'pointer'} onClick={exportMode ? undefined : (_entry, entryIndex) => {
              const month = data.monthly[entryIndex]
              if (month) onDetails(month, issueType)
            }} />
          ))}
        </BarChart>
      </ResponsiveContainer>
      {!exportMode && selectedMonth && (
        <div className="mt-4 flex flex-wrap items-end gap-3 border-t border-apple-divider pt-4">
          <div className="min-w-28 flex-1">
            <label htmlFor={`${controlId}-month`} className="mb-1 block text-sm font-medium text-apple-mid">완료 월</label>
            <select id={`${controlId}-month`} value={monthIndex} onChange={(event) => setMonthIndex(Number(event.target.value))} className="min-h-11 w-full rounded-lg border border-apple-divider bg-apple-surface px-3 text-sm text-apple-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
              {data.monthly.map((month, index) => <option key={`${month.year}-${month.month_num}`} value={index}>{month.year}년 {month.month}</option>)}
            </select>
          </div>
          <div className="min-w-36 flex-1">
            <label htmlFor={`${controlId}-type`} className="mb-1 block text-sm font-medium text-apple-mid">요청 유형</label>
            <select id={`${controlId}-type`} value={selectedType} onChange={(event) => setSelectedType(event.target.value)} className="min-h-11 w-full rounded-lg border border-apple-divider bg-apple-surface px-3 text-sm text-apple-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
              <option value="">전체 유형</option>
              {issueTypes.map((issueType) => <option key={issueType} value={issueType}>{issueType}</option>)}
            </select>
          </div>
          <button type="button" onClick={() => onDetails(selectedMonth, selectedType || undefined)} className={DETAILS_BUTTON_CLASS} aria-label={`${selectedMonth.year}년 ${selectedMonth.month} ${selectedType || '전체 유형'} 재배포 ${selectedCount}건 상세 보기`}>{selectedCount.toLocaleString('ko-KR')}건 상세 보기</button>
        </div>
      )}
    </div>
  )
}

function CauseChart({ values, onDetails }: { values: Record<string, number>; onDetails: ShowBreakdown }) {
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
              <Pie data={data} dataKey="value" nameKey="name" outerRadius={118} paddingAngle={1} isAnimationActive={!exportMode} stroke="rgb(var(--color-apple-surface))" strokeWidth={2} cursor={exportMode ? undefined : 'pointer'} onClick={exportMode ? undefined : (_entry, index) => {
                const cause = data[index]
                if (cause) onDetails(cause.name, cause.value)
              }}>
                {data.map((entry, index) => <Cell key={entry.name} fill={CATEGORICAL_CHART_COLORS[index % CATEGORICAL_CHART_COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(value, name) => [`${Number(value).toLocaleString('ko-KR')}건`, String(name)]} />
              {exportMode && <Legend iconType="circle" iconSize={REDEPLOYMENT_LEGEND_ICON_SIZE} wrapperStyle={{ paddingTop: 8 }} formatter={(value: string) => <span style={{ color: CHART_LEGEND_COLOR, fontSize: REDEPLOYMENT_FONT_SIZE, fontWeight: 500 }}>{value}</span>} />}
            </PieChart>
          </ResponsiveContainer>
          {!exportMode && <ul className="divide-y divide-apple-divider/70 border-t border-apple-divider/70">
            {data.map((entry, index) => (
              <li key={entry.name}>
                <button type="button" onClick={() => onDetails(entry.name, entry.value)} className="flex min-h-11 w-full items-center gap-3 rounded-lg px-2 py-2.5 text-left text-sm transition-colors hover:bg-apple-gray focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500" aria-label={`재배포 원인 ${entry.name} ${entry.value}건 상세 보기`}>
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: CATEGORICAL_CHART_COLORS[index % CATEGORICAL_CHART_COLORS.length] }} />
                  <span className="min-w-0 flex-1 break-words font-medium text-apple-dark">{entry.name}</span>
                  <span className="shrink-0 font-semibold tabular-nums text-apple-dark underline decoration-apple-divider underline-offset-4">{entry.value.toLocaleString('ko-KR')}건</span>
                  <span className="w-14 shrink-0 text-right tabular-nums text-apple-mid">{total > 0 ? (entry.value / total * 100).toFixed(1) : '0.0'}%</span>
                </button>
              </li>
            ))}
          </ul>}
        </div>
      ) : <div className="flex items-center justify-center text-ui-sm text-apple-light" style={{ height: CHART_HEIGHT }}>데이터가 없습니다</div>}
      {!exportMode && <button type="button" onClick={() => onDetails(undefined, total)} className={`mt-3 ${DETAILS_BUTTON_CLASS}`}>전체 원인 {total.toLocaleString('ko-KR')}건 상세 보기</button>}
    </div>
  )
}

function AssigneeChart({ values, onDetails }: { values: Record<string, number>; onDetails: ShowBreakdown }) {
  const exportMode = useDashboardExportMode()
  const controlId = useId()
  const [selectedAssignee, setSelectedAssignee] = useState('')
  const data = Object.entries(values).slice(0, 10).map(([name, value]) => ({ name, value }))
  const assignee = data.find((entry) => entry.name === selectedAssignee) ?? data[0]
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
                payload={data.map((entry, index) => ({ value: entry.name, type: 'circle', color: CATEGORICAL_CHART_COLORS[index % CATEGORICAL_CHART_COLORS.length] }))}
                formatter={(value: string) => <span style={{ color: CHART_LEGEND_COLOR, fontSize: REDEPLOYMENT_FONT_SIZE, fontWeight: 500 }}>{value}</span>}
              />
            )}
            <Bar isAnimationActive={!exportMode} dataKey="value" radius={[0, 6, 6, 0]} cursor={exportMode ? undefined : 'pointer'} onClick={exportMode ? undefined : (_entry, index) => {
              const entry = data[index]
              if (entry) onDetails(entry.name, entry.value)
            }}>
              {data.map((entry, index) => <Cell key={entry.name} fill={CATEGORICAL_CHART_COLORS[index % CATEGORICAL_CHART_COLORS.length]} />)}
              <LabelList dataKey="value" position="right" fill={CHART_COLORS.axisText} fontSize={REDEPLOYMENT_FONT_SIZE} formatter={(value: unknown) => Number(value).toLocaleString('ko-KR')} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : <div className="flex items-center justify-center text-ui-sm text-apple-light" style={{ height: CHART_HEIGHT }}>데이터가 없습니다</div>}
      {!exportMode && (
        <div className="mt-4 flex flex-wrap items-end gap-3 border-t border-apple-divider pt-4">
          {assignee && <div className="min-w-36 flex-1">
            <label htmlFor={controlId} className="mb-1 block text-sm font-medium text-apple-mid">담당자</label>
            <select id={controlId} value={assignee.name} onChange={(event) => setSelectedAssignee(event.target.value)} className="min-h-11 w-full rounded-lg border border-apple-divider bg-apple-surface px-3 text-sm text-apple-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
              {data.map((entry) => <option key={entry.name} value={entry.name}>{entry.name}</option>)}
            </select>
          </div>}
          <button type="button" onClick={() => onDetails(assignee?.name, assignee?.value ?? 0)} className={DETAILS_BUTTON_CLASS} aria-label={`${assignee?.name ?? '담당자별'} 재배포 ${assignee?.value ?? 0}건 상세 보기`}>{(assignee?.value ?? 0).toLocaleString('ko-KR')}건 상세 보기</button>
        </div>
      )}
    </div>
  )
}

function PartnerMatrix({ matrix, onDetails }: { matrix: Record<string, Record<string, number>>; onDetails: (partner: string, total: number, issueType?: string) => void }) {
  const exportMode = useDashboardExportMode()
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
                      return <td key={issueType} className="px-4 py-3.5 font-semibold tabular-nums text-apple-dark" style={{ backgroundColor: `rgb(var(--color-chart-created) / ${opacity})` }}>{exportMode ? count || '–' : <button type="button" className={`w-full ${DETAILS_BUTTON_CLASS}`} aria-label={`${partner} ${issueType} 재배포 ${count}건 상세 보기`} onClick={() => onDetails(partner, count, issueType)}>{count.toLocaleString('ko-KR')}</button>}</td>
                    })}
                    <td className="bg-apple-gray/50 px-4 py-3.5 font-bold tabular-nums text-apple-dark">{exportMode ? total.toLocaleString('ko-KR') : <button type="button" className={`w-full ${DETAILS_BUTTON_CLASS}`} aria-label={`${partner} 전체 유형 재배포 ${total}건 상세 보기`} onClick={() => onDetails(partner, total)}>{total.toLocaleString('ko-KR')}</button>}</td>
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
                  <tr key={issue.key} className="border-b border-apple-divider/60 transition-colors hover:bg-[rgb(var(--color-chart-created)/0.08)]">
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
                          ? 'bg-[rgb(var(--color-chart-created))] text-white'
                          : 'bg-apple-gray text-apple-mid hover:bg-[rgb(var(--color-chart-created)/0.12)] hover:text-blue-600'
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

export default function RedeploymentAnnualSection({ data, year, reportId }: Props) {
  const exportMode = useDashboardExportMode()
  const [details, setDetails] = useState<IssueDetails | null>(null)
  const classificationComplete = data.classification_complete
  const issues = data.latest_issues.filter((issue) => !isDashboardExcludedIssueType(issue.type))
  const showMonthlyDetails = (month: RedeploymentMonthlyEntry, issueType?: string) => {
    const total = Object.entries(month.by_type)
      .filter(([type]) => !isDashboardExcludedIssueType(type) && (!issueType || type === issueType))
      .reduce((sum, [, count]) => sum + count, 0)
    setDetails({
      title: `${month.year}년 ${month.month} 재배포 · ${issueType || '전체 유형'}`,
      total,
      issues: issues.filter((issue) => issue.month.startsWith(`${month.year}-`) && Number(issue.month.slice(5, 7)) === month.month_num && (!issueType || issue.type === issueType)),
    })
  }
  const showCauseDetails: ShowBreakdown = (cause, total) => setDetails({
    title: `${year}년 재배포 원인 · ${cause ?? '전체 원인'}`,
    total,
    issues: issues.filter((issue) => cause === undefined || issue.cause === cause),
  })
  const showAssigneeDetails: ShowBreakdown = (assignee, total) => setDetails({
    title: `${year}년 담당자별 재배포 · ${assignee ?? '전체 담당자'}`,
    total,
    issues: issues.filter((issue) => assignee === undefined || issue.assignee === assignee),
  })
  const showPartnerDetails = (partner: string, total: number, issueType?: string) => {
    const partnerIssues = issues.filter((issue) => issue.partners.includes(partner) && (!issueType || issue.type === issueType))
    setDetails({
      title: `${year}년 ${partner} 재배포 · ${issueType || '전체 유형'}`,
      total,
      issues: partnerIssues,
      request: partnerIssues.length !== total ? { chart: 'redeployment', partner, issue_type: issueType } : undefined,
    })
  }
  return (
    <section data-pdf-section={`${year}년 재배포 품질 지표`} className="redeployment-analytics space-y-4 md:space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-apple-divider pt-6">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[rgb(var(--color-chart-created)/0.12)] text-blue-600"><BarChart3 size={20} /></span>
          <div>
            <h2 className="text-xl font-semibold text-apple-dark">{year}년 재배포 품질 지표</h2>
            <p className="mt-1 text-sm text-apple-mid">재배포 규모와 원인, 담당자 및 파트너사별 현황</p>
          </div>
        </div>
        <span className="rounded-lg bg-apple-gray px-3 py-1.5 text-sm font-medium text-apple-dark">연간 전체 기준</span>
      </div>
      <div data-pdf-kind="metrics" className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <KpiCard label="전체 해결 이슈" value={data.resolved_total} unit="건" icon={<CheckCircle2 size={21} />} tone="bg-[rgb(var(--color-chart-resolved)/0.16)] text-green-600" />
        <KpiCard label="재배포 이슈" value={classificationComplete ? data.redeployment_total : '집계 불가'} unit={classificationComplete ? '건' : ''} icon={<RotateCcw size={21} />} tone="bg-[rgb(var(--color-chart-orange)/0.16)] text-orange-700" />
        <KpiCard label="재배포율" value={classificationComplete ? data.redeployment_rate : '집계 불가'} unit={classificationComplete ? '%' : ''} icon={<Percent size={21} />} tone="bg-[rgb(var(--color-chart-created)/0.16)] text-blue-600" />
      </div>
      {!classificationComplete ? (
        <div data-pdf-kind="text" className="card flex min-h-44 flex-col items-center justify-center gap-2 text-center">
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[rgb(var(--color-chart-warning)/0.16)] text-amber-600"><AlertTriangle size={22} /></span>
          <p className="text-ui-base font-semibold text-apple-dark">{year}년 재배포 원천 데이터가 기록되지 않았습니다</p>
        </div>
      ) : data.redeployment_total > 0 ? (
        <>
          <MonthlyRedeploymentChart data={data} onDetails={showMonthlyDetails} />
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <CauseChart values={data.by_cause} onDetails={showCauseDetails} />
            <AssigneeChart values={data.by_assignee} onDetails={showAssigneeDetails} />
          </div>
          <PartnerMatrix matrix={data.partner_matrix} onDetails={showPartnerDetails} />
          <LatestIssues key={year} data={data} />
        </>
      ) : (
        <div data-pdf-kind="text" className="card flex min-h-40 flex-col items-center justify-center gap-2 text-center">
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[rgb(var(--color-chart-resolved)/0.16)] text-green-600"><CheckCircle2 size={22} /></span>
          <p className="text-ui-base font-semibold text-apple-dark">{year}년 재배포 이슈가 없습니다</p>
        </div>
      )}
      {!exportMode && details && (details.request
        ? <AnnualRemoteIssueDetailsModal reportId={reportId} request={details.request} title={details.title} total={details.total} onClose={() => setDetails(null)} />
        : <AnnualIssueDetailsModal title={details.title} total={details.total} issues={details.issues} onClose={() => setDetails(null)} />)}
    </section>
  )
}
