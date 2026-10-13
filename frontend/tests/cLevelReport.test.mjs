// frontend/tests/cLevelReport.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import ts from 'typescript'
import { read, write, utils } from 'xlsx'
import pdfMake from 'pdfmake'
import { getDocument } from 'pdfjs-dist/legacy/build/pdf.mjs'

const require = createRequire(import.meta.url)
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const sourceRoot = path.join(root, 'src')
function loader(overrides = {}) {
  const modules = new Map()
  function load(relative) {
    const base = path.join(sourceRoot, relative)
    const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
    assert.ok(filename, `Missing module ${relative}`)
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX }, fileName: filename }).outputText
    new Function('require', 'module', 'exports', compiled)((dependency) => {
      if (dependency in overrides) return overrides[dependency]
      if (dependency.startsWith('@/')) return load(dependency.slice(2))
      if (dependency.startsWith('.')) return load(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)))
      return require(dependency)
    }, module, module.exports)
    return module.exports
  }
  return load
}
const load = loader()
const helpers = load('application/services/cLevelReport')
const { buildCLevelExport } = load('application/services/cLevelExport')
const { buildDashboardExcelWorkbook } = load('infrastructure/export/dashboardExcelWorkbook')
const { buildDashboardPdfDefinition } = load('infrastructure/export/dashboardPdfDefinition')
const selection = { minimumMonths: 1, trendType: 'all', violationMetric: 'all', violationType: 'all' }

function fixture() {
  const types = ['service', 'incident', 'improvement']
  const empty = { created: 0, resolved: 0, unresolved: 0, resolution_rate: null, average_resolution_days: null }
  const measures = { violations: 0, evaluated: 0, met: 0, compliance_rate: null }
  const issue = {
    key: 'TACEA-42', summary: '반복 상태 진입 이슈', issue_type: '인시던트 보고', type: 'incident', type_label: '인시던트', customer_name: '검증 고객사', partner_names: ['파트너A'], reporter: null, assignee: '담당자', tac_assignee: null,
    created_at: '2026-01-01T09:00:00+09:00', updated_at: null, status: '연구소 대기 중', status_category: 'indeterminate', history_complete: true, reopen_count: 1, age_days: 284, age_bucket: '6-12', is_unresolved: true, first_response_at: null,
    timeline: [
      { id: 'first', status: '이슈 리뷰 중', status_id: '1', status_category: 'indeterminate', owner: 'TAC', start_at: '2026-10-06T09:00:00+09:00', end_at: '2026-10-06T10:00:00+09:00', duration_hours: 1, is_current: false, breached_metrics: [] },
      { id: 'second', status: '연구소 대기 중', status_id: '2', status_category: 'indeterminate', owner: '연구소', start_at: '2026-10-06T10:00:00+09:00', end_at: '2026-10-07T09:00:00+09:00', duration_hours: 23, is_current: false, breached_metrics: ['resolution'] },
      { id: 'third', status: '이슈 리뷰 중', status_id: '1', status_category: 'indeterminate', owner: 'TAC', start_at: '2026-10-07T09:00:00+09:00', end_at: '2026-10-07T10:00:00+09:00', duration_hours: 1, is_current: true, breached_metrics: [] },
    ],
    owner_hours: { TAC: 2, '고객·파트너': 0, '연구소': 23, '기타': 0 },
    sla_cycles: [{ metric: 'resolution', cycle_id: '1', start_at: '2026-10-06T09:00:00+09:00', stop_at: null, breach_at: '2026-10-06T17:00:00+09:00', goal_hours: 8, elapsed_hours: null, remaining_hours: null, excess_hours: null, breached: true, paused: null, ongoing: true, historical_elapsed_known: false }], warnings: [],
  }
  const customerIssues = [
    { key: issue.key, type: 'incident', bucket: '6-12', age_days: 284, status: '연구소 대기 중', tac_assignee: '김담당', partner_names: ['파트너A'] },
    { key: 'TACEA-2', type: 'service', bucket: '1-3', age_days: 45, status: '자료 요청 중', tac_assignee: '이담당', partner_names: ['파트너B'] },
  ]
  const violation = { id: 'TACEA-42:resolution:1', issue_key: issue.key, summary: issue.summary, type: 'incident', type_label: '인시던트', customer_name: issue.customer_name, metric: 'resolution', cycle_id: '1', goal_hours: 8, elapsed_hours: null, excess_hours: null, breach_at: '2026-10-06T17:00:00+09:00', status: issue.status, status_at_breach: '연구소 대기 중', owner_at_breach: '연구소', paused: null, is_ongoing: true }
  return {
    period: 'week', start_date: '2026-10-06', end_date: '2026-10-12', as_of: '2026-10-13T00:00:00+09:00', previous_start_date: '2026-09-29', previous_end_date: '2026-10-05', generated_at: '2026-10-13T10:00:00+09:00', policy_version: 'v1', policy_labels: ['생성일 기준 경과, 완료 범주는 Done'], warnings: [], report_token: 'token-1',
    summary: ['all', ...types].map((type) => ({ ...empty, type, label: type === 'all' ? '전체' : helpers.CLEVEL_TYPES.find((entry) => entry.type === type).label, created: type === 'all' ? 4 : 0, previous: { ...empty }, delta: { created: 4, resolved: 0, unresolved: 0 } })),
    trend: Array.from({ length: 8 }, (_, index) => ({ label: `09/${index + 1}`, start_date: '2026-09-01', end_date: '2026-09-07', created: index, resolved: index % 3, unresolved: index === 2 ? null : 5, by_type: types.map((type) => ({ type, label: type, created: 1, resolved: 0, unresolved: null })) })),
    long_term: { buckets: ['1-3', '3-6', '6-12', '12+'].map((id, index) => ({ id, label: `${id}개월`, min_months: [1, 3, 6, 12][index], max_months: [3, 6, 12, null][index], count: index === 0 || index === 2 ? 1 : 0, customer_count: index === 0 || index === 2 ? 1 : 0, by_type: { service: index === 0 ? 1 : 0, incident: index === 2 ? 1 : 0, improvement: 0 } })), customers: [{ customer_key: 'customer1', customer_name: '검증 고객사', partners: ['파트너A', '파트너B'], tac_assignees: ['김담당', '이담당'], total: 2, by_type: { service: 1, incident: 1, improvement: 0 }, buckets: { '1-3': 1, '3-6': 0, '6-12': 1, '12+': 0 }, oldest_days: 284, dominant_status: '자료 요청 중', issue_keys: customerIssues.map((item) => item.key), issues: customerIssues }] },
    sla: { by_type: types.map((type) => ({ type, label: helpers.CLEVEL_TYPES.find((entry) => entry.type === type).label, initial_response: { ...measures }, resolution: { ...measures } })), violation_ticket_count: 1, violation_event_count: 1, delay_reasons: [{ status: '연구소 대기 중', owner: '연구소', count: 1, percentage: 100 }], coverage: { known_cycles: 1, unknown_cycles: 0, issues_without_sla: 0 } },
    violations: [violation], issues: [issue], comments: { [issue.key]: { delay_reason: '분석 대기', action_taken: '고객 안내 완료', prevention_plan: '일정 공유', included: true, updated_at: '2026-10-13T10:00:00+09:00', updated_by: '검토자' }, 'TACEA-99': { delay_reason: '보고 제외 원문', action_taken: '', prevention_plan: '', included: false } },
  }
}

test('unknown values never become zero; zero remains a numeric zero', () => {
  for (const value of [null, undefined, NaN, Infinity]) assert.equal(helpers.cLevelNumber(value, 'h', 1), '확인 불가')
  assert.equal(helpers.cLevelNumber(0, 'h', 1), '0h')
  assert.equal(helpers.cLevelText(''), '확인 불가')
  assert.equal(helpers.cLevelText('미지정'), '확인 불가')
  assert.equal(helpers.cLevelDate(null), '확인 불가')
  assert.equal(helpers.cLevelDate('not-a-date'), '확인 불가')
  assert.equal(helpers.cLevelDate('2026-10-12T15:15:00Z'), '2026-10-13 00:15')
})

test('customer prefixes appear exactly once in detail and export titles', () => {
  assert.equal(helpers.cLevelIssueTitle('한전KDN', '[한전KDN] 보고서 생성'), '[한전KDN] 보고서 생성')
  assert.equal(helpers.cLevelIssueTitle('한전KDN', '보고서 생성'), '[한전KDN] 보고서 생성')
  assert.equal(helpers.cLevelIssueSummary('한전KDN', '[한전KDN] 보고서 생성'), '보고서 생성')
  const report = fixture()
  report.issues[0].summary = '[검증 고객사] 보고서 생성'
  report.violations[0].summary = report.issues[0].summary
  const document = JSON.stringify(buildCLevelExport(report, selection))
  assert.match(document, /\[검증 고객사\] 보고서 생성/)
  assert.doesNotMatch(document, /\[검증 고객사\] \[검증 고객사\]/)
})

test('NEW badge follows a supplied release date and expires after exactly 30 days', () => {
  const released = '2026-10-13T00:00:00+09:00'
  const start = new Date(released).getTime()
  assert.equal(helpers.cLevelNewBadgeVisible(undefined, start), false)
  assert.equal(helpers.cLevelNewBadgeVisible('invalid', start), false)
  assert.equal(helpers.cLevelNewBadgeVisible(released, start - 1), false)
  assert.equal(helpers.cLevelNewBadgeVisible(released, start), true)
  assert.equal(helpers.cLevelNewBadgeVisible(released, start + 30 * 86400000 - 1), true)
  assert.equal(helpers.cLevelNewBadgeVisible(released, start + 30 * 86400000), false)
})

test('age filter recomputes customer totals, partners, owners and dominant status from selected issues without modifying the source', () => {
  const report = fixture()
  const before = structuredClone(report)
  const customers = helpers.filterCLevelCustomers(report.long_term.customers, 6)
  assert.equal(customers.length, 1)
  assert.equal(customers[0].total, 1)
  assert.deepEqual(customers[0].by_type, { service: 0, incident: 1, improvement: 0 })
  assert.deepEqual(customers[0].partners, ['파트너A'])
  assert.deepEqual(customers[0].tac_assignees, ['김담당'])
  assert.equal(customers[0].dominant_status, '연구소 대기 중')
  assert.equal(helpers.filterCLevelCustomers(report.long_term.customers, 12).length, 0)
  assert.deepEqual(report, before)
})

test('violation filters sort known excess before unknown and preserve different SLA cycles', () => {
  const item = fixture().violations[0]
  const data = [item, { ...item, id: 'known-zero', excess_hours: 0 }, { ...item, id: 'largest', excess_hours: 5 }, { ...item, id: 'initial', metric: 'initial_response', excess_hours: 10 }]
  assert.deepEqual(helpers.filterCLevelViolations(data, 'resolution', 'incident').map((row) => row.id), ['largest', 'known-zero', item.id])
  assert.equal(helpers.filterCLevelViolations(data, 'all', 'service').length, 0)
})

test('trend filtering preserves unknown, known zero, and missing type distinctly', () => {
  const report = fixture()
  assert.equal(helpers.cLevelTrendData(report, 'all')[0].created, 0)
  assert.equal(helpers.cLevelTrendData(report, 'all')[2].unresolved, null)
  assert.equal(helpers.cLevelTrendData(report, 'service')[0].created, 1)
  assert.equal(helpers.cLevelTrendData(report, 'missing')[0].created, null)
})

test('summary SLA compliance uses weighted evaluated totals and preserves missing coverage', () => {
  const report = fixture()
  report.sla.by_type[0].resolution = { violations: 1, evaluated: 10, met: 9, compliance_rate: 90 }
  report.sla.by_type[1].resolution = { violations: 1, evaluated: 2, met: 1, compliance_rate: 50 }
  assert.equal(helpers.cLevelSlaCompliance(report, 'resolution'), 10 / 12 * 100)
  report.sla.by_type[2].resolution.evaluated = null
  assert.equal(helpers.cLevelSlaCompliance(report, 'resolution'), null)
  assert.equal(helpers.cLevelSlaCompliance(fixture(), 'initial_response'), null)
})

test('export freezes the selected data, uses section page breaks, preserves repeated timeline stages and omits unchecked comments', () => {
  const report = fixture()
  report.snapshot = { id: 4, title: '저장된 보고서 제목', saved_by: '저장자', saved_at: '2026-10-13T09:00:00+09:00' }
  const document = buildCLevelExport(report, { ...selection, minimumMonths: 6 })
  const serialized = JSON.stringify(document)
  assert.equal(document.title, '저장된 보고서 제목')
  assert.ok(document.filters.some((value) => value.includes('저장자')))
  assert.equal(document.sections[1].pageBreakBefore, true)
  assert.equal(document.sections[2].pageBreakBefore, true)
  assert.match(serialized, /분석 대기/)
  assert.doesNotMatch(serialized, /보고 제외 원문/)
  const timeline = document.sections.flatMap((section) => section.blocks).find((block) => block.title === '처리 과정')
  assert.equal(timeline.rows.filter((row) => row[0].text === '이슈 리뷰 중').length, 2)
  report.comments['TACEA-42'].delay_reason = '저장 후 수정됨'
  report.long_term.customers[0].customer_name = '수정된 고객사'
  assert.equal(JSON.stringify(document), serialized)
})

test('Excel preserves numeric counts and literal formula-looking issue text, with unknown text instead of fake zero', () => {
  const report = fixture()
  report.violations[0].summary = '=SUM(1,2)'
  report.summary[0].unresolved = null
  const document = buildCLevelExport(report, selection)
  const workbook = read(write(buildDashboardExcelWorkbook(document), { type: 'buffer', bookType: 'xlsx' }), { type: 'buffer' })
  const processing = workbook.Sheets['이번 기간 처리 현황']
  assert.equal(processing.B2.t, 'n')
  assert.equal(processing.B2.v, 4)
  assert.equal(processing.C2.t, 'n')
  assert.equal(processing.C2.v, 0)
  assert.equal(processing.D2.v, '확인 불가')
  const rows = utils.sheet_to_json(workbook.Sheets['위반 목록'], { header: 1 })
  assert.ok(rows[1][1].includes('=SUM(1,2)'))
  assert.equal(workbook.Sheets['위반 목록'].B2.f, undefined)
})

test('customer-only export follows the age filter and excludes SLA and report comments', () => {
  const document = buildCLevelExport(fixture(), { ...selection, minimumMonths: 6 }, true)
  assert.equal(document.sections[0].pageBreakBefore, false)
  assert.equal(document.sections.some((section) => section.title.startsWith('3.')), false)
  const table = document.sections[0].blocks.find((block) => block.title.includes('고객사별 장기 미해결'))
  assert.equal(table.rows[0][2].value, 0)
  assert.equal(table.rows[0][5].value, 1)
  assert.equal(JSON.stringify(document).includes('분석 대기'), false)
})

test('unfinished non-breached SLA cycles export as pending, not compliance success', () => {
  const report = fixture()
  report.issues[0].sla_cycles[0].breached = false
  let data = buildCLevelExport(report, selection)
  assert.ok(JSON.stringify(data).includes('진행 중'))
  report.issues[0].sla_cycles[0].paused = true
  data = buildCLevelExport(report, selection)
  assert.ok(JSON.stringify(data).includes('일시 정지'))
})

test('gateway forwards period, cancellation, refresh, frozen token and exact comment payload', async () => {
  const calls = []
  const client = Object.fromEntries(['get', 'put', 'post'].map((method) => [method, async (...args) => { calls.push([method, ...args]); return { data: { result: true } } }]))
  const { cLevelReportApi: api } = loader({ './client': { default: client } })('infrastructure/api/cLevelReportApi')
  const signal = new AbortController().signal
  await api.getReport('month', '2026-10-01', true, signal)
  assert.deepEqual(calls[0], ['get', '/c-level-report', { params: { period: 'month', date: '2026-10-01', refresh: true }, signal, timeout: 600000 }])
  const input = { delay_reason: '원인', action_taken: '조치', prevention_plan: '계획', included: true }
  await api.saveComment('TACEA-42', 'frozen-token', input)
  assert.deepEqual(calls[1], ['put', '/c-level-report/comments/TACEA-42', { ...input, report_token: 'frozen-token' }])
  await api.saveSnapshot('frozen-token', '제목')
  assert.deepEqual(calls[2], ['post', '/c-level-report/snapshots', { report_token: 'frozen-token', title: '제목' }])
  await api.getSnapshot(12, signal)
  assert.equal(calls[3][1], '/c-level-report/snapshots/12')
  await api.getSnapshots(20, 40)
  assert.deepEqual(calls[4][2], { params: { limit: 20, offset: 40 } })
})

const chartStubs = Object.fromEntries(['Bar', 'BarChart', 'CartesianGrid', 'Legend', 'ResponsiveContainer', 'Tooltip', 'XAxis', 'YAxis'].map((name) => [name, () => null]))
const uiLoad = loader({ recharts: chartStubs, '@/presentation/context/JiraContext': { useJira: () => ({ jiraBrowse: 'https://jira.example.test/browse' }) } })

test('overview renders unknown aggregate and SLA coverage instead of a zero-violation claim', () => {
  const report = fixture()
  report.summary[0].unresolved = null
  report.long_term.buckets[0].count = null
  report.long_term.unknown_status_issue_count = 1
  report.sla.violation_ticket_count = null
  report.sla.violation_event_count = null
  report.sla.coverage = { known_cycles: 0, unknown_cycles: 2, issues_without_sla: 3 }
  report.sla.delay_reasons = []
  report.violations = []
  const { default: Overview } = uiLoad('presentation/components/clevel/CLevelOverview')
  const html = renderToStaticMarkup(React.createElement(Overview, { report, selection, setSelection() {}, onSelectIssue() {}, onExportCustomers() {}, exporting: false }))
  assert.match(html, /SLA 위반 확인 불가/)
  assert.match(html, /위반 구간 확인 불가/)
  assert.match(html, /측정 확인 불가/)
  assert.doesNotMatch(html, /NaN/)
  assert.doesNotMatch(html, /선택한 조건에 해당하는 SLA 위반이 없습니다/)
})

test('detail preserves repeated stages, deadline, default report inclusion, unknown historical durations and frozen edit protection', () => {
  const { default: Detail } = uiLoad('presentation/components/clevel/CLevelIssueDetail')
  const issue = fixture().issues[0]
  const editable = renderToStaticMarkup(React.createElement(Detail, { issue, readonly: false, saving: false, saveError: '', onClose() {}, onSave: async () => true }))
  assert.equal((editable.match(/이슈 리뷰 중/g) ?? []).length, 2)
  assert.match(editable, /SLA 기한 도래/)
  assert.match(editable, /2026-10-06 17:00/)
  assert.match(editable, /과거|선택한 기준 시점/)
  assert.match(editable, /type="checkbox" checked=""/)
  assert.match(editable, /role="dialog" aria-modal="true"/)
  const frozen = renderToStaticMarkup(React.createElement(Detail, { issue, readonly: true, saving: false, saveError: '', onClose() {}, onSave: async () => true }))
  assert.equal((frozen.match(/textarea disabled=""/g) ?? []).length, 3)
  assert.match(frozen, /저장 시점의 보고 내용/)
})

test('SLA cycle picker numbers first-response and resolution cycles independently', () => {
  const { default: Detail } = uiLoad('presentation/components/clevel/CLevelIssueDetail')
  const issue = fixture().issues[0]
  issue.sla_cycles = [{ ...issue.sla_cycles[0], metric: 'initial_response' }, issue.sla_cycles[0], { ...issue.sla_cycles[0], cycle_id: '2' }]
  const html = renderToStaticMarkup(React.createElement(Detail, { issue, readonly: false, saving: false, saveError: '', onClose() {}, onSave: async () => true }))
  assert.match(html, /최초응답 · 1번째 측정/)
  assert.match(html, /해결시간 · 1번째 측정/)
  assert.match(html, /해결시간 · 2번째 측정/)
  assert.doesNotMatch(html, /해결시간 · 3번째 측정/)
})

test('actual C-Level PDF contains Korean, all sections, comments and explicit landscape section boundaries', async () => {
  const regular = path.join(sourceRoot, 'assets/fonts/NanumGothic-Regular.ttf')
  const bold = path.join(sourceRoot, 'assets/fonts/NanumGothic-Bold.ttf')
  pdfMake.setUrlAccessPolicy(() => false)
  pdfMake.setLocalAccessPolicy((file) => [regular, bold].includes(path.resolve(file)))
  pdfMake.addFonts({ NanumGothic: { normal: regular, bold, italics: regular, bolditalics: bold } })
  const definition = buildDashboardPdfDefinition(buildCLevelExport(fixture(), selection))
  assert.equal(definition.pageOrientation, 'landscape')
  assert.ok(definition.content.filter((item) => item.pageBreak === 'before').length >= 3)
  const bytes = await pdfMake.createPdf(definition).getBuffer()
  const pdf = await getDocument({ data: new Uint8Array(bytes), useSystemFonts: true, disableFontFace: true }).promise
  const pages = []
  for (let index = 1; index <= pdf.numPages; index++) {
    const page = await pdf.getPage(index)
    assert.ok(page.view[2] > page.view[3])
    const content = await page.getTextContent()
    pages.push(content.items.map((item) => item.str).join('').replace(/\s+/g, ''))
  }
  const text = pages.join('\n')
  assert.match(text, /처리현황/)
  assert.match(text, /장기이슈/)
  assert.match(text, /SLA위반/)
  assert.match(text, /분석대기/)
  assert.match(text, /확인불가/)
  assert.doesNotMatch(text, /보고제외원문/)
  assert.notEqual(pages.findIndex((text) => text.includes('2.장기이슈')), pages.findIndex((text) => text.includes('3.SLA위반')))
  await pdf.destroy()
})
