// frontend/tests/annualIssueDetails.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')
const modules = new Map()
const charts = Object.fromEntries([
  'Bar', 'BarChart', 'CartesianGrid', 'Cell', 'LabelList', 'Legend', 'Pie', 'PieChart',
  'ResponsiveContainer', 'Tooltip', 'XAxis', 'YAxis',
].map((name) => [name, ({ children, ...props }) => React.createElement(name, props, children)]))
const modalStub = (name) => ({ default: (props) => React.createElement(name, props, props.headerSlot) })

function loadSource(relative) {
  const base = path.join(sourceRoot, relative)
  const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
  assert.ok(filename, `Missing source module: ${relative}`)
  if (modules.has(filename)) return modules.get(filename).exports
  const module = { exports: {} }
  modules.set(filename, module)
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
    fileName: filename,
  }).outputText
  new Function('require', 'module', 'exports', compiled)((dependency) => {
    if (dependency === 'recharts') return charts
    if (dependency === '@/presentation/components/common/IssueTableModal') return modalStub('IssueTableModal')
    if (dependency === './AnnualIssueDetailsModal') return modalStub('AnnualIssueDetailsModal')
    if (dependency === './AnnualRemoteIssueDetailsModal') return modalStub('AnnualRemoteIssueDetailsModal')
    if (dependency === '@/presentation/context/JiraContext') return { useJira: () => ({ jiraBrowse: 'https://jira.example.test/browse' }) }
    if (dependency === '@/presentation/components/common/IssueTypeBadge') return { IssueTypeBadge: ({ type }) => React.createElement('span', null, type) }
    if (dependency === '@/presentation/components/common/StatusBadge') return { StatusBadge: ({ status }) => React.createElement('span', null, status) }
    if (dependency.startsWith('@/')) return loadSource(dependency.slice(2))
    if (dependency.startsWith('.')) return loadSource(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)))
    return require(dependency)
  }, module, module.exports)
  return module.exports
}

const { default: AnnualIssueDetailsModal } = loadSource('presentation/components/annual/AnnualIssueDetailsModal')
const { default: RedeploymentAnnualSection } = loadSource('presentation/components/annual/RedeploymentAnnualSection')
const { DashboardExportProvider } = loadSource('presentation/context/DashboardExportContext')

function render(t, component, props, exportMode = false) {
  let view
  const content = React.createElement(component, props)
  act(() => { view = TestRenderer.create(exportMode ? React.createElement(DashboardExportProvider, null, content) : content) })
  t.after(() => act(() => view.unmount()))
  return view
}

function textOf(node) {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  return node.children.map(textOf).join('')
}

function button(view, label) {
  return view.root.findAllByType('button').find((node) => node.props['aria-label'] === label || textOf(node) === label)
}

function click(node, ...args) {
  assert.ok(node, 'Expected an accessible button or chart segment')
  act(() => node.props.onClick(...args))
}

function select(view, label, value) {
  const fieldLabel = view.root.findAllByType('label').find((node) => textOf(node) === label)
  assert.ok(fieldLabel, `Missing label: ${label}`)
  const field = view.root.findAllByType('select').find((node) => node.props.id === fieldLabel.props.htmlFor)
  assert.ok(field, `Missing labelled select: ${label}`)
  act(() => field.props.onChange({ target: { value } }))
}

function search(view, value) {
  act(() => view.root.findByType('input').props.onChange({ target: { value } }))
}

function visibleKeys(view) {
  return view.root.findByType('IssueTableModal').props.data.map((issue) => issue.key)
}

function localDetails(view) {
  assert.equal(view.root.findAllByType('AnnualRemoteIssueDetailsModal').length, 0)
  return view.root.findByType('AnnualIssueDetailsModal').props
}

function statusMessages(view) {
  return view.root.findAll((node) => node.props.role === 'status').map(textOf)
}

function fixtureAnalytics() {
  const issue = (key, type, month, resolved, cause, assignee, partners) => ({ key, summary: `${key} 제목`, type, month, resolved, cause, assignee, partners, priority: '보통' })
  return {
    resolved_total: 20,
    redeployment_total: 5,
    redeployment_rate: 25,
    analytics_total: 4,
    classification_complete: true,
    monthly: [
      { month: '1월', year: 2026, month_num: 1, total: 3, by_type: { '개선': 1, '인시던트': 1, '라이선스': 1 } },
      { month: '2월', year: 2026, month_num: 2, total: 1, by_type: { '서비스 요청': 1 } },
      { month: '3월', year: 2026, month_num: 3, total: 0, by_type: {} },
    ],
    by_cause: { '제품 결함': 2, '설정 변경': 1, '연도 이월': 1, '미발생': 0 },
    by_assignee: { '김담당': 2, '이담당': 2, '빈담당': 0 },
    partner_matrix: {
      '파트너 A': { '개선': 1, '인시던트': 1, CVE: 1, '라이선스': 1 },
      '파트너 B': { '서비스 요청': 1, '인시던트': 1, '개선': 1 },
    },
    latest_issues: [
      issue('ANNUAL-1', '개선', '2026-01', '2026-03-04 10:00', '제품 결함', '김담당', ['파트너 A']),
      issue('ANNUAL-2', '서비스 요청', '2026-02', '2026-01-10 10:00', '설정 변경', '이담당', ['파트너 B']),
      issue('ANNUAL-3', '인시던트', '2026-01', '2026-01-14 10:00', '제품 결함', '김담당', ['파트너 A', '파트너 B']),
      issue('EXCLUDED-1', '라이선스', '2026-01', '2026-01-14 10:00', '제품 결함', '김담당', ['파트너 A']),
      issue('PREVIOUS-1', '개선', '2025-01', '2026-01-12 10:00', '연도 이월', '이담당', ['파트너 B']),
    ],
    source_jqls: {},
  }
}

function renderRedeployment(t, exportMode = false) {
  return render(t, RedeploymentAnnualSection, { data: fixtureAnalytics(), year: 2026, reportId: 42 }, exportMode)
}

test('annual details search tickets, summaries and partners without changing the source rows', (t) => {
  const issues = [
    { key: 'TAC-101', summary: '방화벽 정책 변경', type: '개선', partners: ['동부 파트너'] },
    { key: 'TAC-202', summary: '수집기 재시작', type: '인시던트', partners: ['서부 파트너'] },
    { key: 'OPS-303', summary: 'Queue restart', type: '서비스 요청', assignee: '김담당' },
  ]
  const original = structuredClone(issues)
  const view = render(t, AnnualIssueDetailsModal, { title: '상세', total: 3, issues, onClose() {} })
  search(view, '  tac-202  ')
  assert.deepEqual(visibleKeys(view), ['TAC-202'])
  search(view, '방화벽 정책')
  assert.deepEqual(visibleKeys(view), ['TAC-101'])
  search(view, '동부 파트너')
  assert.deepEqual(visibleKeys(view), ['TAC-101'])
  search(view, 'QUEUE')
  assert.deepEqual(visibleKeys(view), ['OPS-303'])
  search(view, '존재하지 않는 검색어')
  assert.deepEqual(visibleKeys(view), [])
  assert.deepEqual(statusMessages(view), ['검색 조건에 맞는 이슈가 없습니다.'])
  search(view, '')
  assert.deepEqual(visibleKeys(view), ['TAC-101', 'TAC-202', 'OPS-303'])
  assert.deepEqual(issues, original)
})

test('annual details page through all tickets in groups of twenty and reset the page on search', (t) => {
  const issues = Array.from({ length: 45 }, (_, index) => ({ key: `TAC-${index + 1}`, summary: `이슈 ${index + 1}`, type: '개선' }))
  const view = render(t, AnnualIssueDetailsModal, { title: '상세', total: 45, issues, onClose() {} })
  const encountered = [...visibleKeys(view)]
  assert.equal(encountered.length, 20)
  assert.equal(button(view, '이전').props.disabled, true)
  click(button(view, '다음'))
  assert.equal(visibleKeys(view).length, 20)
  encountered.push(...visibleKeys(view))
  click(button(view, '다음'))
  assert.deepEqual(visibleKeys(view), ['TAC-41', 'TAC-42', 'TAC-43', 'TAC-44', 'TAC-45'])
  encountered.push(...visibleKeys(view))
  assert.deepEqual(encountered, issues.map((issue) => issue.key))
  assert.equal(button(view, '다음').props.disabled, true)
  click(button(view, '이전'))
  assert.equal(visibleKeys(view)[0], 'TAC-21')
  search(view, 'TAC-45')
  assert.deepEqual(visibleKeys(view), ['TAC-45'])
  assert.equal(button(view, '이전').props.disabled, true)
  assert.equal(button(view, '다음').props.disabled, true)
})

test('annual details distinguish a true zero from unavailable individual issues', (t) => {
  const empty = render(t, AnnualIssueDetailsModal, { title: '0건', total: 0, issues: [], onClose() {} })
  assert.deepEqual(visibleKeys(empty), [])
  assert.deepEqual(statusMessages(empty), ['해당 조건의 이슈가 없습니다.'])
  const missing = render(t, AnnualIssueDetailsModal, { title: '미수집', total: 3, issues: [], onClose() {} })
  assert.deepEqual(visibleKeys(missing), [])
  assert.deepEqual(statusMessages(missing), [
    '차트 집계와 조회 가능한 상세 건수가 다릅니다. 목록은 확인된 이슈만 표시합니다.',
    '조회 가능한 개별 이슈가 없습니다.',
  ])
})

test('annual details preserve both counts and show only confirmed issues when counts differ', (t) => {
  const view = render(t, AnnualIssueDetailsModal, { title: '상세', total: 8, issues: [{ key: 'TAC-1', summary: '확인된 티켓', type: '개선' }], onClose() {} })
  assert.equal(view.root.findByType('IssueTableModal').props.subtitle, '차트 집계 8건 · 상세 목록 1건')
  assert.deepEqual(visibleKeys(view), ['TAC-1'])
  assert.match(statusMessages(view)[0], /차트 집계와 조회 가능한 상세 건수가 다릅니다/)
})

test('redeployment monthly segments filter on completion month rather than resolved date or another year', (t) => {
  const view = renderRedeployment(t)
  const improvement = view.root.findAllByType('Bar').find((node) => node.props.dataKey === '개선')
  click(improvement, {}, 0)
  assert.equal(localDetails(view).title, '2026년 1월 재배포 · 개선')
  assert.equal(localDetails(view).total, 1)
  assert.deepEqual(localDetails(view).issues.map((issue) => issue.key), ['ANNUAL-1'])
  const service = view.root.findAllByType('Bar').find((node) => node.props.dataKey === '서비스 요청')
  click(service, {}, 1)
  assert.deepEqual(localDetails(view).issues.map((issue) => issue.key), ['ANNUAL-2'])
  assert.equal(localDetails(view).total, 1)
  assert.equal(view.root.findAllByType('Bar').some((node) => node.props.dataKey === '라이선스'), false)
})

test('monthly accessible selectors retain exact totals, exclude license issues and open zero-count details', (t) => {
  const view = renderRedeployment(t)
  click(button(view, '2026년 1월 전체 유형 재배포 2건 상세 보기'))
  assert.equal(localDetails(view).total, 2)
  assert.deepEqual(localDetails(view).issues.map((issue) => issue.key), ['ANNUAL-1', 'ANNUAL-3'])
  select(view, '완료 월', '1')
  select(view, '요청 유형', '인시던트')
  click(button(view, '2026년 2월 인시던트 재배포 0건 상세 보기'))
  assert.equal(localDetails(view).total, 0)
  assert.deepEqual(localDetails(view).issues, [])
  select(view, '완료 월', '2')
  select(view, '요청 유형', '')
  click(button(view, '2026년 3월 전체 유형 재배포 0건 상세 보기'))
  assert.equal(localDetails(view).total, 0)
  assert.deepEqual(localDetails(view).issues, [])
})

test('cause pie and count legend select the same tickets and keep zero causes accessible', (t) => {
  const view = renderRedeployment(t)
  click(view.root.findByType('Pie'), {}, 0)
  assert.equal(localDetails(view).total, 2)
  assert.deepEqual(localDetails(view).issues.map((issue) => issue.key), ['ANNUAL-1', 'ANNUAL-3'])
  click(button(view, '재배포 원인 설정 변경 1건 상세 보기'))
  assert.deepEqual(localDetails(view).issues.map((issue) => issue.key), ['ANNUAL-2'])
  click(button(view, '재배포 원인 미발생 0건 상세 보기'))
  assert.equal(localDetails(view).total, 0)
  assert.deepEqual(localDetails(view).issues, [])
  click(button(view, '전체 원인 4건 상세 보기'))
  assert.equal(localDetails(view).total, 4)
  assert.deepEqual(localDetails(view).issues.map((issue) => issue.key), ['ANNUAL-1', 'ANNUAL-2', 'ANNUAL-3', 'PREVIOUS-1'])
})

test('assignee bars and labelled selectors isolate the correct assignee including zero counts', (t) => {
  const view = renderRedeployment(t)
  const assigneeBar = view.root.findAllByType('Bar').find((node) => node.props.dataKey === 'value')
  click(assigneeBar, {}, 1)
  assert.equal(localDetails(view).total, 2)
  assert.deepEqual(localDetails(view).issues.map((issue) => issue.key), ['ANNUAL-2', 'PREVIOUS-1'])
  select(view, '담당자', '김담당')
  click(button(view, '김담당 재배포 2건 상세 보기'))
  assert.deepEqual(localDetails(view).issues.map((issue) => issue.key), ['ANNUAL-1', 'ANNUAL-3'])
  select(view, '담당자', '빈담당')
  click(button(view, '빈담당 재배포 0건 상세 보기'))
  assert.equal(localDetails(view).total, 0)
  assert.deepEqual(localDetails(view).issues, [])
})

test('partner matrix filters saved tickets locally and queries the source when a type or total is missing', (t) => {
  const view = renderRedeployment(t)
  click(button(view, '파트너 B 서비스 요청 재배포 1건 상세 보기'))
  assert.equal(localDetails(view).total, 1)
  assert.deepEqual(localDetails(view).issues.map((issue) => issue.key), ['ANNUAL-2'])
  click(button(view, '파트너 B 전체 유형 재배포 3건 상세 보기'))
  assert.equal(localDetails(view).total, 3)
  assert.deepEqual(localDetails(view).issues.map((issue) => issue.key), ['ANNUAL-2', 'ANNUAL-3', 'PREVIOUS-1'])
  click(button(view, '파트너 A 서비스 요청 재배포 0건 상세 보기'))
  assert.equal(localDetails(view).total, 0)
  assert.deepEqual(localDetails(view).issues, [])
  click(button(view, '파트너 A CVE 재배포 1건 상세 보기'))
  assert.equal(view.root.findAllByType('AnnualIssueDetailsModal').length, 0)
  let remote = view.root.findByType('AnnualRemoteIssueDetailsModal').props
  assert.equal(remote.reportId, 42)
  assert.equal(remote.total, 1)
  assert.deepEqual(remote.request, { chart: 'redeployment', partner: '파트너 A', issue_type: 'CVE' })
  click(button(view, '파트너 A 전체 유형 재배포 3건 상세 보기'))
  remote = view.root.findByType('AnnualRemoteIssueDetailsModal').props
  assert.equal(remote.total, 3)
  assert.deepEqual(remote.request, { chart: 'redeployment', partner: '파트너 A', issue_type: undefined })
  act(() => remote.onClose())
  assert.equal(view.root.findAllByType('AnnualRemoteIssueDetailsModal').length, 0)
  assert.equal(view.root.findAllByType('th').some((node) => textOf(node) === '라이선스'), false)
})

test('redeployment PDF mode has no detail controls, click handlers or modals and keeps chart data', (t) => {
  const view = renderRedeployment(t, true)
  assert.equal(view.root.findAllByType('button').length, 0)
  assert.equal(view.root.findAllByType('select').length, 0)
  assert.equal(view.root.findAllByType('AnnualIssueDetailsModal').length, 0)
  assert.equal(view.root.findAllByType('AnnualRemoteIssueDetailsModal').length, 0)
  assert.equal(view.root.findAll((node) => typeof node.props.onClick === 'function').length, 0)
  for (const chart of [...view.root.findAllByType('Bar'), ...view.root.findAllByType('Pie')]) assert.equal(chart.props.isAnimationActive, false)
  assert.equal(view.root.findAllByType('BarChart').length, 2)
  assert.equal(view.root.findAllByType('PieChart').length, 1)
  const monthly = view.root.findAllByType('BarChart').find((node) => node.props.layout !== 'vertical')
  assert.equal(monthly.props.data[0].total, 2)
  assert.equal(Object.hasOwn(monthly.props.data[0], '라이선스'), false)
})
