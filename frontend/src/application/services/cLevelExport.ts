// frontend/src/application/services/cLevelExport.ts
import type { CLevelReport } from '@/domain/CLevelReport'
import type { DashboardPdfBlock, DashboardPdfDocument, DashboardPdfSection } from '@/domain/DashboardExport'
import { CLEVEL_AGE_BUCKETS, cLevelDate, cLevelIssueTitle, cLevelMetricLabel, cLevelNumber, cLevelText, cLevelTrendData, filterCLevelCustomers, filterCLevelViolations } from './cLevelReport'

export interface CLevelExportSelection {
  minimumMonths: number
  trendType: string
  violationMetric: string
  violationType: string
}

function table(title: string, headers: string[], rows: (string | number | null)[][]): DashboardPdfBlock {
  return { kind: 'table', title, headers, rows: rows.map((row) => row.map((value) => ({ text: value == null ? '확인 불가' : String(value), value: value == null ? '확인 불가' : value }))) }
}

function xml(value: string): string {
  return value.replace(/[<>&"']/g, (character) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&apos;' })[character] ?? character)
}

function trendBlock(report: CLevelReport, type: string): DashboardPdfBlock {
  const data = cLevelTrendData(report, type)
  const colors = ['#778796', '#65b7cf', '#dbb951']
  const keys = ['created', 'resolved', 'unresolved'] as const
  const max = Math.max(1, ...data.flatMap((point) => keys.map((key) => point[key] ?? 0)))
  const step = 720 / Math.max(data.length, 1)
  const marks = data.map((point, index) => {
    const x = 35 + step * index
    return keys.map((key, series) => {
      const value = point[key]
      const h = value === null ? 0 : 135 * value / max
      return `<rect x="${x + series * 15}" y="${160 - h}" width="12" height="${h}" rx="2" fill="${colors[series]}"/><text x="${x + series * 15 + 6}" y="${154 - h}" text-anchor="middle" font-size="8">${value === null ? '?' : value}</text>`
    }).join('') + `<text x="${x + 20}" y="182" text-anchor="middle" font-size="10">${xml(point.label)}</text>`
  }).join('')
  return {
    kind: 'chart', title: `최근 ${data.length}${report.period === 'week' ? '주' : '개월'} 추이`, subtitle: '기간 내 접수 · 기간 내 해결 · 기간 말 미해결 · ? = 확인 불가',
    svg: `<svg xmlns="http://www.w3.org/2000/svg" width="780" height="200" viewBox="0 0 780 200"><rect width="780" height="200" fill="#ffffff"/>${marks}</svg>`,
    width: 780, height: 200, fullWidth: true, legend: keys.map((_, index) => ({ label: ['접수', '해결', '미해결'][index], color: colors[index] })),
    data: { headers: ['기간', '접수', '해결', '미해결'], rows: data.map((row) => [row.label, row.created, row.resolved, row.unresolved]) },
  }
}

export function buildCLevelExport(report: CLevelReport, selection: CLevelExportSelection, customersOnly = false): DashboardPdfDocument {
  const customers = filterCLevelCustomers(report.long_term.customers, selection.minimumMonths)
  const customerSection: DashboardPdfSection = {
    title: '2. 장기 이슈 관리 대상 고객사', pageBreakBefore: !customersOnly,
    blocks: [
      table('이전 기간 대비 장기 이슈', ['지표', '이전 기간', '증감'], [['장기 이슈 전체', report.long_term.previous_total ?? null, report.long_term.delta_total ?? null], ['12개월 이상', report.long_term.previous_over_12_months ?? null, report.long_term.delta_over_12_months ?? null]]),
      table('경과 구간별 현황', ['구간', '미해결', '고객사', '단순문의', '인시던트', '개선'], report.long_term.buckets.map((bucket) => [bucket.label, bucket.count, bucket.customer_count, bucket.by_type.service, bucket.by_type.incident, bucket.by_type.improvement])),
      table(`${selection.minimumMonths}개월 이상 고객사별 장기 미해결`, ['고객사', '파트너', '단순문의', '인시던트', '개선', '합계', '경과 분포 (1~3 / 3~6 / 6~12 / 12+)', '최장 경과', '주요 체류 상태', 'TAC 담당'], customers.map((customer) => [customer.customer_name, customer.partners.join(', ') || '확인 불가', customer.by_type.service, customer.by_type.incident, customer.by_type.improvement, customer.total, CLEVEL_AGE_BUCKETS.map((key) => customer.buckets[key]).join(' / '), `${customer.oldest_days}일`, customer.dominant_status, customer.tac_assignees.join(', ') || '확인 불가'])),
    ],
  }
  const sections: DashboardPdfSection[] = customersOnly ? [customerSection] : [
    { title: '1. 처리 현황', blocks: [
      table('이번 기간 처리 현황', ['유형', '접수', '해결', '미해결', '접수 증감', '해결 증감', '미해결 증감', '해결률', '평균 해결'], report.summary.map((card) => [card.label, card.created, card.resolved, card.unresolved, card.delta.created, card.delta.resolved, card.delta.unresolved, cLevelNumber(card.resolution_rate, '%', 1), cLevelNumber(card.average_resolution_days, '일', 1)])),
      trendBlock(report, selection.trendType),
    ] },
    customerSection,
    { title: '3. SLA 위반 티켓', pageBreakBefore: true, blocks: [
      table('SLA 준수 현황', ['유형', '최초응답 위반', '응답 평가 대상', '응답 준수율', '해결시간 위반', '해결 평가 대상', '해결 준수율'], report.sla.by_type.map((entry) => [entry.label, entry.initial_response.violations, entry.initial_response.evaluated, cLevelNumber(entry.initial_response.compliance_rate, '%', 1), entry.resolution.violations, entry.resolution.evaluated, cLevelNumber(entry.resolution.compliance_rate, '%', 1)])),
      table('기한 도래 시점의 체류 상태', ['상태', '책임 구간', '건수', '비중'], report.sla.delay_reasons.map((reason) => [reason.status, cLevelText(reason.owner), reason.count, cLevelNumber(reason.percentage, '%', 1)])),
      table('위반 목록', ['티켓', '고객사 · 제목', '유형', '위반 구분', '초과', 'SLA 기한', '현재 상태', '기한 시점 상태'], filterCLevelViolations(report.violations, selection.violationMetric, selection.violationType).map((issue) => [issue.issue_key, cLevelIssueTitle(issue.customer_name, issue.summary), issue.type_label, cLevelMetricLabel(issue.metric), cLevelNumber(issue.excess_hours, 'h', 1), cLevelDate(issue.breach_at), issue.status, cLevelText(issue.status_at_breach)])),
    ] },
  ]
  if (!customersOnly) {
    for (const [key, comment] of Object.entries(report.comments ?? {})) {
      if (!comment.included) continue
      const issue = report.issues.find((entry) => entry.key === key)
      const blocks: DashboardPdfBlock[] = [
        { kind: 'text', paragraphs: [issue ? cLevelIssueTitle(issue.customer_name, issue.summary) : key, `지연 원인: ${comment.delay_reason || '미작성'}`, `조치 내용: ${comment.action_taken || '미작성'}`, `재발 방지 · 향후 계획: ${comment.prevention_plan || '미작성'}`, `저장자: ${cLevelText(comment.updated_by)} · ${cLevelDate(comment.updated_at)}`] },
      ]
      if (issue) {
        blocks.push(table('처리 과정', ['상태', '책임 구간', '시작', '종료', '체류 시간', '기한 도래 구간'], issue.timeline.map((segment) => [segment.status, segment.owner, cLevelDate(segment.start_at), cLevelDate(segment.end_at), cLevelNumber(segment.duration_hours, 'h', 1), segment.breached_metrics.map(cLevelMetricLabel).join(', ')])))
        blocks.push(table('SLA 측정 주기', ['구분', '목표', '실제 소요', '초과', '기한', '상태'], issue.sla_cycles.map((cycle) => [cLevelMetricLabel(cycle.metric), cLevelNumber(cycle.goal_hours, 'h', 1), cLevelNumber(cycle.elapsed_hours, 'h', 1), cLevelNumber(cycle.excess_hours, 'h', 1), cLevelDate(cycle.breach_at), cycle.breached === null ? '확인 불가' : cycle.breached ? '위반' : cycle.ongoing ? cycle.paused ? '일시 정지' : '진행 중' : '준수'])))
        if (issue.warnings.length) blocks.push({ kind: 'text', title: '확인 사항', paragraphs: issue.warnings })
      }
      sections.push({ title: `보고용 코멘트 · ${key}`, pageBreakBefore: true, blocks })
    }
  }
  sections.push({ title: '집계 기준', blocks: [{ kind: 'text', paragraphs: [...report.policy_labels, `정책 버전: ${report.policy_version}`, `기준 시점: ${cLevelDate(report.as_of)}`, ...report.warnings] }] })
  return {
    title: customersOnly ? '고객사별 장기 미해결 현황' : report.snapshot?.title || '집중(특별) 관리 보고',
    period: `${report.start_date} ~ ${report.end_date}`,
    generatedAt: cLevelDate(report.generated_at),
    filters: [report.period === 'week' ? '주간 보고' : '월간 보고', `비교 기간 ${report.previous_start_date} ~ ${report.previous_end_date}`, `장기 이슈 ${selection.minimumMonths}개월 이상`, ...(report.snapshot ? [`저장자 ${report.snapshot.saved_by} · 저장 시각 ${cLevelDate(report.snapshot.saved_at)}`] : [])],
    sections,
  }
}
