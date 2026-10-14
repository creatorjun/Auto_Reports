// frontend/tests/slaViolations.test.mjs
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
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query')
const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')

function sourceLoader(overrides = {}) {
  const modules = new Map()
  function load(relative) {
    if (Object.hasOwn(overrides, relative)) return overrides[relative]
    const base = path.join(sourceRoot, relative)
    const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
    assert.ok(filename, `Missing module ${relative}`)
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX }, fileName: filename }).outputText
    new Function('require', 'module', 'exports', compiled)((dependency) => {
      if (Object.hasOwn(overrides, dependency)) return overrides[dependency]
      if (dependency.startsWith('@/')) return load(dependency.slice(2))
      if (dependency.startsWith('.')) return load(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)).replaceAll('\\', '/'))
      return require(dependency)
    }, module, module.exports)
    return module.exports
  }
  return load
}

const load = sourceLoader()
const { slaDateRange, slaToday, slaTicketsForMetric, slaPartnersLabel } = load('application/services/slaViolationReport')
const { slaCreatedDate } = load('presentation/utils/slaViolationFormatters')
const { defaultSlaSelectedStatuses, filterSlaViolationTickets, slaViolationFilterOptions } = load('domain/SlaViolationFilters')
const { sortSlaViolationTickets } = load('domain/SlaViolationSort')
const { filterSlaViolationScope, filterSlaViolationDetails, slaViolationCounts, slaViolationStatuses, slaViolationTimeline } = load('domain/SlaViolationOverview')
const ticket = {
  key: 'TACEA-1234', summary: '[서울 교통공사] MF2 컴포넌트 개선의 건', issue_type: '서비스 요청', created_at: '2026-05-05T16:00:00Z', elapsed_days: 123,
  customer: '서울교통공사', partners: [], reporter: '김영준 과장', assignee: '조장희 수석', tac_assignee: '한준희 선임', current_status: '결과 대기 중',
  status_durations: [{ status: '할일', hours: 3.25 }, { status: '연구소 검토 중', hours: 120.5 }],
  breaches: [{ metric: 'initial_response', breached_at: '2026-05-06T04:00:00Z', status: '할일' }, { metric: 'resolution', breached_at: '2026-05-08T06:00:00Z', status: '연구소 검토 중' }], warnings: [],
}
const report = { id: 10, period: 'month', selected_date: '2026-05-06', start_date: '2026-05-01', end_date: '2026-05-31', generated_at: '2026-10-14T03:00:00Z', generated_by: 'admin', ticket_count: 1, initial_response_count: 1, resolution_count: 1, tickets: [ticket], warnings: [] }

function deferred() {
  let resolve
  let reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

async function settle() { await act(async () => { await new Promise((resolve) => setTimeout(resolve, 10)) }) }
async function until(predicate) {
  const deadline = Date.now() + 2500
  while (!predicate()) { assert.ok(Date.now() < deadline, 'Timed out waiting for query state'); await settle() }
}

function textOf(node) {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textOf).join(' ')
  return node?.children ? textOf(node.children) : ''
}

test('overview counts tickets once per metric and separates the intersection from total violations', () => {
  const rows = [
    { ...ticket, breaches: [...ticket.breaches, ticket.breaches[0]] },
    { ...ticket, key: 'T-2', current_status: '자료 요청 중', breaches: [ticket.breaches[0]] },
    { ...ticket, key: 'T-3', current_status: '자료 요청 중', breaches: [ticket.breaches[1]] },
    { ...ticket, key: 'T-4', breaches: [] },
  ]
  const original = structuredClone(rows)
  assert.deepEqual(slaViolationCounts(rows), { all: 3, initial_response: 2, resolution: 2, both: 1 })
  assert.deepEqual(filterSlaViolationScope(rows, 'both').map((row) => row.key), ['TACEA-1234'])
  assert.deepEqual(slaViolationStatuses(filterSlaViolationScope(rows, 'all')), [{ status: '자료 요청 중', count: 2 }, { status: '결과 대기 중', count: 1 }])
  assert.deepEqual(slaViolationCounts([]), { all: 0, initial_response: 0, resolution: 0, both: 0 })
  assert.deepEqual(rows, original)
})

test('overview timeline uses KST creation dates across year boundaries and retains zero and leap-day buckets', () => {
  const rows = [
    { ...ticket, key: 'T-1', created_at: '2025-12-31T14:59:59Z' },
    { ...ticket, key: 'T-2', created_at: '2025-12-31T15:00:00Z' },
    { ...ticket, key: 'T-3', created_at: '2026-01-04T15:00:00Z' },
    { ...ticket, key: 'T-4', created_at: 'invalid' },
  ]
  const week = slaViolationTimeline({ period: 'week', start_date: '2025-12-29', end_date: '2026-01-04' }, rows)
  assert.equal(week.buckets.length, 7)
  assert.deepEqual(week.buckets.filter((bucket) => bucket.count), [
    { key: '2025-12-31', label: '12/31', count: 1 }, { key: '2026-01-01', label: '1/1', count: 1 },
  ])
  assert.equal(week.unassigned, 2)
  const year = slaViolationTimeline({ period: 'year', start_date: '2026-01-01', end_date: '2026-12-31' }, rows)
  assert.equal(year.buckets.length, 12)
  assert.deepEqual(year.buckets[0], { key: '2026-01', label: '1월', count: 2 })
  assert.equal(year.buckets[11].count, 0)
  const leap = slaViolationTimeline({ period: 'month', start_date: '2024-02-01', end_date: '2024-02-29' }, [{ ...ticket, created_at: '2024-02-28T15:00:00Z' }])
  assert.equal(leap.buckets.length, 29)
  assert.deepEqual(leap.buckets[28], { key: '2024-02-29', label: '2/29', count: 1 })
})

test('overview drilldowns intersect creation bucket, current status and normalized ticket searches', () => {
  const rows = [ticket, { ...ticket, key: 'T-2', customer: '다른 고객', partners: ['파트너'], created_at: '2026-06-01T00:00:00Z', current_status: '자료 요청 중' }]
  const original = structuredClone(rows)
  const keys = (...filters) => filterSlaViolationDetails(rows, ...filters).map((row) => row.key)
  assert.deepEqual(keys('year', '결과 대기 중', '2026-05', '  TACEA-1234  '), [ticket.key])
  assert.deepEqual(keys('month', null, '2026-05-06', '본사'), [ticket.key])
  assert.deepEqual(keys('year', null, '2026-05', '한준희'), [ticket.key])
  assert.deepEqual(keys('year', '자료 요청 중', '2026-05', ''), [])
  assert.deepEqual(keys('year', '자료 요청 중', null, '파트너'), ['T-2'])
  assert.deepEqual(keys('year', null, null, '없는 검색어'), [])
  assert.deepEqual(rows, original)
})

test('overview cards, charts and search filter existing lists together while respecting default excluded statuses', (t) => {
  const instance = sourceLoader({ 'presentation/context/JiraContext': { useJira: () => ({ jiraBrowse: 'https://jira.example/browse' }) } })
  const Content = instance('presentation/components/sla-violations/SlaViolationReportContent').default
  const List = instance('presentation/components/sla-violations/SlaViolationList').default
  const rows = [
    ticket,
    { ...ticket, key: 'T-2', current_status: '자료 요청 중', created_at: '2026-06-01T00:00:00Z', breaches: [ticket.breaches[0]] },
    { ...ticket, key: 'T-3', current_status: '자료 요청 중', breaches: [ticket.breaches[1]] },
    { ...ticket, key: 'T-closed', current_status: '닫힘' },
    { ...ticket, key: 'T-held', current_status: '보류 중' },
  ]
  const snapshot = { ...report, period: 'year', start_date: '2026-01-01', end_date: '2026-12-31', tickets: rows }
  const original = structuredClone(snapshot)
  let view
  act(() => { view = TestRenderer.create(React.createElement(Content, { key: snapshot.id, report: snapshot })) })
  t.after(() => act(() => view.unmount()))
  const click = (label) => act(() => view.root.findByProps({ 'aria-label': label }).props.onClick())
  const keys = () => view.root.findAllByType(List).map((list) => list.findAllByType('a').map((link) => link.props.href.split('/').at(-1)))
  const search = (value) => act(() => view.root.findByProps({ type: 'search' }).props.onChange({ target: { value } }))
  assert.equal(view.root.findByProps({ 'aria-label': '전체 위반 티켓 3건 보기' }).props['aria-pressed'], true)
  click('최초응답 위반 2건 보기')
  assert.deepEqual(keys(), [[ticket.key, 'T-2']])
  click('자료 요청 중 위반 티켓 1건 보기')
  click('2026-06 생성 위반 티켓 1건 보기')
  assert.deepEqual(keys(), [['T-2']])
  search('TACEA')
  assert.deepEqual(keys(), [[]])
  act(() => view.root.findAllByType('button').find((button) => textOf(button) === '상세 필터 초기화').props.onClick())
  assert.deepEqual(keys(), [[ticket.key, 'T-2'], [ticket.key, 'T-3']])
  click('동시 위반 1건 보기')
  assert.deepEqual(keys(), [[ticket.key], [ticket.key]])
  act(() => view.update(React.createElement(Content, { key: snapshot.id, report: { ...snapshot, tickets: [...rows] } })))
  assert.equal(view.root.findByProps({ 'aria-label': '동시 위반 1건 보기' }).props['aria-pressed'], true)
  act(() => view.update(React.createElement(Content, { key: 11, report: { ...snapshot, id: 11 } })))
  assert.equal(view.root.findByProps({ 'aria-label': '전체 위반 티켓 3건 보기' }).props['aria-pressed'], true)
  assert.deepEqual(snapshot, original)
})

test('duration bars use visible elapsed hours, omit closed time, and retain tiny percentages', () => {
  const Durations = load('presentation/components/sla-violations/SlaStatusDurations').default
  const values = [{ status: '할 일', hours: 25 }, { status: '구현 중', hours: 74.99 }, { status: '연구소 검토 중', hours: 0.01 }, { status: '닫힘', hours: 900 }]
  const original = structuredClone(values)
  const view = TestRenderer.create(React.createElement(Durations, { durations: values }))
  const chart = view.root.findByProps({ role: 'img' })
  assert.deepEqual(chart.children.map((child) => child.props.style.width), ['25%', '74.99%', '0.01%'])
  assert.match(textOf(chart.children[0]), /할 일.*25%/)
  assert.match(textOf(chart.children[1]), /구현 중.*75%/)
  assert.equal(chart.children[2].props.title, '연구소 검토 중 · 0.01시간 · <0.1%')
  assert.match(chart.props['aria-label'], /연구소 검토 중 <0.1%/)
  assert.match(textOf(view.toJSON()), /25\s*시간/)
  assert.doesNotMatch(textOf(view.toJSON()), /900|각 상태별 체류 기간|보고서 생성 시점까지/)
  assert.deepEqual(values, original)
  view.unmount()
})

test('duration bars do not fabricate proportions for zero, empty, or incomplete histories', () => {
  const Durations = load('presentation/components/sla-violations/SlaStatusDurations').default
  for (const durations of [null, [], [{ status: 'Closed', hours: 10 }], [{ status: '할 일', hours: 0 }]]) {
    const view = TestRenderer.create(React.createElement(Durations, { durations }))
    assert.equal(view.root.findAllByProps({ role: 'img' }).length, 0)
    assert.doesNotMatch(textOf(view.toJSON()), /NaN|Infinity/)
    if (durations === null) assert.match(textOf(view.toJSON()), /이력이 불완전/)
    if (durations?.[0]?.hours === 0) assert.match(textOf(view.toJSON()), /0%/)
    view.unmount()
  }
})

function hookSetup(t, gateway) {
  const instance = sourceLoader()
  const { ApplicationServicesProvider } = instance('presentation/context/ApplicationServicesContext')
  const hooks = instance('presentation/hooks/useSlaViolations')
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } })
  let query
  let mutation
  function Probe() { query = hooks.useSlaViolationReport(); mutation = hooks.useGenerateSlaViolationReport(); return null }
  const element = React.createElement(ApplicationServicesProvider, { services: { slaViolations: gateway } }, React.createElement(QueryClientProvider, { client }, React.createElement(Probe)))
  let view
  act(() => { view = TestRenderer.create(element) })
  t.after(() => { act(() => view.unmount()); client.clear() })
  return { client, hooks, get query() { return query }, get mutation() { return mutation }, unmount: () => act(() => view.unmount()), remount: () => act(() => { view = TestRenderer.create(element) }) }
}

test('period selection follows Monday weeks, leap-year months, and cross-year boundaries', () => {
  assert.deepEqual(slaDateRange('week', '2026-01-04'), { start: '2025-12-29', end: '2026-01-04' })
  assert.deepEqual(slaDateRange('week', '2026-01-05'), { start: '2026-01-05', end: '2026-01-11' })
  assert.deepEqual(slaDateRange('month', '2024-02-29'), { start: '2024-02-01', end: '2024-02-29' })
  assert.deepEqual(slaDateRange('month', '2026-12-31'), { start: '2026-12-01', end: '2026-12-31' })
  assert.deepEqual(slaDateRange('year', '2026-10-14'), { start: '2026-01-01', end: '2026-12-31' })
  for (const invalid of ['', '2026-02-29', '2026-13-01', 'junk', '0000-01-01']) assert.equal(slaDateRange('week', invalid), null)
  assert.equal(slaToday(new Date('2026-10-13T15:00:00Z')), '2026-10-14')
  assert.equal(slaCreatedDate(ticket.created_at), '2026-05-06')
})

test('metric lists include dual breaches in both groups exactly once and preserve partner certainty', () => {
  const firstOnly = { ...ticket, key: 'TACEA-2', breaches: [ticket.breaches[0], ticket.breaches[0]] }
  assert.deepEqual(slaTicketsForMetric([ticket, firstOnly], 'initial_response').map((item) => item.key), ['TACEA-1234', 'TACEA-2'])
  assert.deepEqual(slaTicketsForMetric([ticket, firstOnly], 'resolution').map((item) => item.key), ['TACEA-1234'])
  assert.equal(slaPartnersLabel([]), '본사')
  assert.equal(slaPartnersLabel(null), '확인 불가')
  assert.equal(slaPartnersLabel(['에이치씨인포', '파트너2']), '에이치씨인포, 파트너2')
})

test('SLA columns sort naturally by number, Korean text, type, actual creation time, and numeric age', () => {
  const rows = [
    { ...ticket, key: 'TACEA-10', summary: '나 고객사', issue_type: '서비스 요청', created_at: '2026-06-30T17:00:00Z', elapsed_days: 100 },
    { ...ticket, key: 'TACEA-2', summary: '다 고객사', issue_type: '인시던트', created_at: '2026-07-01T01:00:00+09:00', elapsed_days: 9 },
    { ...ticket, key: 'TACEA-1', summary: '가 고객사', issue_type: '개선', created_at: '2026-07-01T02:30:00+09:00', elapsed_days: 20 },
  ]
  const original = structuredClone(rows)
  const expected = {
    key: ['TACEA-1', 'TACEA-2', 'TACEA-10'],
    summary: ['TACEA-1', 'TACEA-10', 'TACEA-2'],
    issue_type: ['TACEA-1', 'TACEA-10', 'TACEA-2'],
    created_at: ['TACEA-2', 'TACEA-10', 'TACEA-1'],
    elapsed_days: ['TACEA-2', 'TACEA-1', 'TACEA-10'],
  }
  assert.strictEqual(sortSlaViolationTickets(rows, null), rows)
  for (const [key, ascending] of Object.entries(expected)) {
    assert.deepEqual(sortSlaViolationTickets(rows, { key, direction: 'asc' }).map((row) => row.key), ascending)
    assert.deepEqual(sortSlaViolationTickets(rows, { key, direction: 'desc' }).map((row) => row.key), [...ascending].reverse())
  }
  assert.deepEqual(rows, original)
})

test('SLA sorting preserves tied rows, equivalent offsets, legacy unknown types, and filter membership', () => {
  const rows = [
    { ...ticket, key: 'TACEA-20', issue_type: null, created_at: '2026-07-01T00:00:00+09:00' },
    { ...ticket, key: 'TACEA-3', issue_type: undefined, created_at: '2026-06-30T15:00:00Z' },
    { ...ticket, key: 'TACEA-1', issue_type: '인시던트', created_at: '2026-06-30T14:59:59Z' },
  ]
  for (const direction of ['asc', 'desc']) {
    assert.deepEqual(sortSlaViolationTickets(rows.slice(0, 2), { key: 'created_at', direction }), rows.slice(0, 2))
    assert.deepEqual(sortSlaViolationTickets(rows.slice(0, 2), { key: 'issue_type', direction }), rows.slice(0, 2))
  }
  const filtered = filterSlaViolationTickets(rows, new Set(['확인 불가']), null, 'h2')
  assert.deepEqual(sortSlaViolationTickets(filtered, { key: 'key', direction: 'asc' }).map((row) => row.key), ['TACEA-3', 'TACEA-20'])
  assert.deepEqual(sortSlaViolationTickets([], { key: 'elapsed_days', direction: 'asc' }), [])
  const sameDisplay = [{ ...ticket, key: 'TACEA-10', issue_type: '라이센스' }, { ...ticket, key: 'TACEA-2', issue_type: '라이선스' }]
  for (const direction of ['asc', 'desc']) assert.deepEqual(sortSlaViolationTickets(sameDisplay, { key: 'issue_type', direction }), sameDisplay)
})

test('SLA filter options include every saved type and explicitly retain legacy unknown types', () => {
  const rows = ['라이선스', '승인된 서비스 요청', '케이스', null, undefined, ''].map((issue_type, index) => ({ ...ticket, key: `T-${index}`, issue_type }))
  const original = structuredClone(rows)
  const options = slaViolationFilterOptions(rows)
  assert.deepEqual(new Set(options.issueTypes), new Set(['라이선스', '승인된 서비스 요청', '케이스', '확인 불가']))
  assert.equal(options.unknownTypeCount, 3)
  assert.deepEqual(options.statuses, ['결과 대기 중'])
  assert.strictEqual(filterSlaViolationTickets(rows, null, null, null), rows)
  assert.deepEqual(filterSlaViolationTickets(rows, new Set(['확인 불가']), null, null).map((row) => row.key), ['T-3', 'T-4', 'T-5'])
  assert.deepEqual(filterSlaViolationTickets(rows, new Set(), null, null), [])
  assert.deepEqual(filterSlaViolationTickets(rows, null, new Set(), null), [])
  assert.deepEqual(rows, original)
  const unknownStatusRows = [{ ...ticket, current_status: '' }, { ...ticket, current_status: '   ' }, { ...ticket, current_status: ' 닫힘 ' }]
  assert.deepEqual(slaViolationFilterOptions(unknownStatusRows).statuses, ['닫힘', '확인 불가'])
  assert.deepEqual(filterSlaViolationTickets(unknownStatusRows, null, new Set(['확인 불가']), null), unknownStatusRows.slice(0, 2))
  assert.deepEqual(filterSlaViolationTickets(unknownStatusRows, null, new Set(['닫힘']), null), unknownStatusRows.slice(2))
})

test('SLA type, saved current status, and KST creation semester filters intersect without dropping other years', () => {
  const rows = [
    { ...ticket, key: 'JUNE', created_at: '2026-06-30T14:59:59Z' },
    { ...ticket, key: 'JULY', created_at: '2026-06-30T15:00:00Z' },
    { ...ticket, key: 'DECEMBER', created_at: '2025-12-31T14:59:59Z', current_status: '닫힘' },
    { ...ticket, key: 'JANUARY', created_at: '2025-12-31T15:00:00Z', issue_type: '케이스' },
  ]
  assert.deepEqual(filterSlaViolationTickets(rows, null, null, 'h1').map((row) => row.key), ['JUNE', 'JANUARY'])
  assert.deepEqual(filterSlaViolationTickets(rows, null, null, 'h2').map((row) => row.key), ['JULY', 'DECEMBER'])
  assert.deepEqual(filterSlaViolationTickets(rows, new Set(['서비스 요청']), new Set(['결과 대기 중']), 'h2').map((row) => row.key), ['JULY'])
  assert.deepEqual(filterSlaViolationTickets(rows, null, new Set(['할일']), null), [])
})

test('SLA defaults exclude only closed, rejected, and on-hold aliases and allow explicit inclusion', () => {
  const statuses = ['결과 대기 중', '닫힘', '반려됨', '보류 중', '보류중', ' Closed ', '닫혀', '취소됨', '중복 이슈', '']
  const rows = statuses.map((current_status, index) => ({ ...ticket, key: `T-${index}`, current_status }))
  const original = structuredClone(rows)
  const selected = defaultSlaSelectedStatuses(rows)
  assert.deepEqual(filterSlaViolationTickets(rows, null, selected, null).map((row) => row.key), ['T-0', 'T-7', 'T-8', 'T-9'])
  assert.equal(filterSlaViolationTickets(rows, null, null, null).length, statuses.length)
  assert.deepEqual(rows, original)
  assert.equal(defaultSlaSelectedStatuses([ticket]), null)
  assert.equal(defaultSlaSelectedStatuses([]), null)
  assert.equal(defaultSlaSelectedStatuses([{ ...ticket, current_status: '닫힘' }]).size, 0)
})

test('SLA page filters both metric lists immediately, preserves same-report choices, and resets for a new report', (t) => {
  const rows = [ticket, { ...ticket, key: 'TACEA-2', issue_type: '케이스', current_status: '닫힘', created_at: '2026-07-01T00:00:00+09:00', breaches: [ticket.breaches[0]] }, { ...ticket, key: 'TACEA-3', issue_type: null, breaches: [ticket.breaches[1]] }]
  let current = { ...report, tickets: rows, ticket_count: 3, initial_response_count: 2, resolution_count: 2 }
  const original = structuredClone(current)
  let generationCalls = 0
  const setCurrentReport = () => {}
  const instance = sourceLoader({
    'react-router-dom': { useParams: () => ({}), useNavigate: () => () => {}, Link: ({ children, to, ...props }) => React.createElement('a', { href: to, ...props }, children) },
    'presentation/context/JiraContext': { useJira: () => ({ jiraBrowse: 'https://jira.example/browse' }) },
    'presentation/state/reportStore': { useReportStore: (selector) => selector({ setCurrentReport }) },
    'presentation/hooks/useSlaViolations': { useSlaViolationReport: () => ({ data: current }), useGenerateSlaViolationReport: () => ({ mutate: () => { generationCalls += 1 } }) },
  })
  const Page = instance('presentation/pages/SlaViolationPage').default
  const List = instance('presentation/components/sla-violations/SlaViolationList').default
  let view
  act(() => { view = TestRenderer.create(React.createElement(Page)) })
  t.after(() => act(() => view.unmount()))
  const click = (name) => act(() => view.root.findAllByType('button').find((button) => textOf(button).trim() === name).props.onClick())
  const metricKeys = () => view.root.findAllByType(List).map((list) => list.findAllByType('a').map((link) => link.props.href.split('/').at(-1)))
  const metricCounts = () => view.root.findAllByType(List).map((list) => Number(textOf(list).match(/(\d+)\s*건/)[1]))
  assert.deepEqual(metricKeys(), [['TACEA-1234'], ['TACEA-1234', 'TACEA-3']])
  assert.match(textOf(view.toJSON()), /요청 유형이 저장되지 않은 티켓\s+1\s*건/)
  assert.equal(view.root.findAllByProps({ 'aria-label': '이슈 제목 검색' }).length, 0)
  click('필터 펼치기')
  click('확인 불가')
  assert.deepEqual(metricKeys(), [['TACEA-1234'], ['TACEA-1234']])
  click('닫힘')
  assert.deepEqual(metricKeys(), [['TACEA-1234', 'TACEA-2'], ['TACEA-1234']])
  click('닫힘')
  assert.deepEqual(metricKeys(), [['TACEA-1234'], ['TACEA-1234']])
  assert.deepEqual(metricCounts(), [1, 1])
  act(() => view.root.findAllByProps({ 'aria-label': 'TACEA-1234 상세 펼치기' })[0].props.onClick())
  current = { ...current, tickets: current.tickets.map((row) => ({ ...row })) }
  act(() => view.update(React.createElement(Page)))
  assert.deepEqual(metricKeys(), [['TACEA-1234'], ['TACEA-1234']])
  assert.equal(view.root.findAllByProps({ 'aria-label': 'TACEA-1234 상세 접기' }).length, 1)
  click('하반기')
  assert.deepEqual(metricKeys(), [[], []])
  assert.match(textOf(view.toJSON()), /선택한 필터에 맞는\s+최초응답 위반\s+티켓이 없습니다/)
  click('전체 선택')
  assert.deepEqual(metricKeys(), [['TACEA-2'], []])
  click('하반기')
  click('전체 해제')
  assert.deepEqual(metricKeys(), [[], []])
  click('전체 선택')
  assert.deepEqual(metricKeys(), [['TACEA-1234', 'TACEA-2'], ['TACEA-1234', 'TACEA-3']])
  click('케이스')
  current = { ...current, id: 11 }
  act(() => view.update(React.createElement(Page)))
  assert.deepEqual(metricKeys(), [['TACEA-1234'], ['TACEA-1234', 'TACEA-3']])
  assert.equal(view.root.findAllByProps({ 'aria-label': 'TACEA-1234 상세 접기' }).length, 0)
  assert.equal(generationCalls, 0)
  assert.deepEqual({ ...current, id: report.id }, original)
})

test('API preserves generation scope, long request timeout, read cancellation, and history pagination', async () => {
  const calls = []
  const client = { get: async (...args) => { calls.push(['GET', ...args]); return { data: report } }, post: async (...args) => { calls.push(['POST', ...args]); return { data: report } } }
  const api = sourceLoader({ 'infrastructure/api/client': { default: client } })('infrastructure/api/slaViolationApi').slaViolationApi
  const signal = new AbortController().signal
  assert.equal(await api.generate({ period: 'month', date: '2026-05-06' }), report)
  await api.getLatest(signal)
  await api.getById(10, signal)
  await api.getHistory(20, 40, signal)
  assert.deepEqual(calls, [
    ['POST', '/sla-violations', { period: 'month', date: '2026-05-06' }, { timeout: 600_000 }],
    ['GET', '/sla-violations/latest', { signal }], ['GET', '/sla-violations/10', { signal }],
    ['GET', '/sla-violations/history', { params: { limit: 20, offset: 40 }, signal }],
  ])
})

test('latest report is fetched again on menu return and pending reads are cancelled on leave', async (t) => {
  const pending = deferred()
  let reads = 0
  let signal
  const state = hookSetup(t, { getLatest: async (abort) => { signal = abort; reads += 1; return reads === 1 ? report : pending.promise } })
  await until(() => state.query.isSuccess)
  state.unmount()
  state.remount()
  await until(() => reads === 2)
  state.unmount()
  assert.equal(signal.aborted, true)
  pending.resolve({ ...report, id: 11 })
})

test('generation cancels stale latest reads and stores the new snapshot and invalidates history', async (t) => {
  const oldRead = deferred()
  const generation = deferred()
  let reads = 0
  let staleSignal
  const state = hookSetup(t, { getLatest: async (signal) => { reads += 1; if (reads === 1) return report; staleSignal = signal; return oldRead.promise }, generate: async () => generation.promise })
  await until(() => state.query.isSuccess)
  state.client.setQueryData([...state.hooks.SLA_VIOLATION_KEYS.history, 0, 20], [report])
  void state.client.invalidateQueries({ queryKey: state.hooks.SLA_VIOLATION_KEYS.latest })
  await until(() => reads === 2)
  act(() => state.mutation.mutate({ period: 'year', date: '2026-10-14' }))
  await until(() => state.mutation.isPending)
  assert.equal(staleSignal.aborted, true)
  const created = { ...report, id: 11, period: 'year' }
  generation.resolve(created)
  await until(() => state.mutation.isSuccess)
  oldRead.resolve(report)
  await settle()
  assert.equal(state.client.getQueryData(state.hooks.SLA_VIOLATION_KEYS.latest).id, 11)
  assert.equal(state.client.getQueryData(state.hooks.SLA_VIOLATION_KEYS.report(11)), created)
  assert.equal(state.client.getQueryState([...state.hooks.SLA_VIOLATION_KEYS.history, 0, 20]).isInvalidated, true)
})

test('failed generation keeps the last saved report intact', async (t) => {
  const state = hookSetup(t, { getLatest: async () => report, generate: async () => { throw new Error('Jira unavailable') } })
  await until(() => state.query.isSuccess)
  act(() => state.mutation.mutate({ period: 'year', date: '2026-10-14' }))
  await until(() => state.mutation.isError)
  assert.equal(state.query.data, report)
})

test('ticket rows start folded, use a separate accessible disclosure, and show only this metric breach state', (t) => {
  const instance = sourceLoader({ 'presentation/context/JiraContext': { useJira: () => ({ jiraBrowse: 'https://jira.example/browse' }) } })
  const List = instance('presentation/components/sla-violations/SlaViolationList').default
  let view
  act(() => { view = TestRenderer.create(React.createElement(List, { tickets: [ticket], metric: 'initial_response' })) })
  t.after(() => act(() => view.unmount()))
  const link = view.root.findByType('a')
  assert.equal(link.props.target, '_blank')
  assert.equal(link.props.rel, 'noopener noreferrer')
  assert.equal(link.props.href, 'https://jira.example/browse/TACEA-1234')
  assert.match(textOf(link), /2026-05-06/)
  assert.match(textOf(link), /123/)
  assert.match(textOf(link), /서비스 요청/)
  for (const label of ['번호', '제목', '유형', '생성일', '경과일']) assert.equal(view.root.findByProps({ 'aria-label': `${label} 오름차순 정렬` }).props['aria-pressed'], false)
  const disclosure = () => view.root.findAllByType('button').find((button) => button.props['aria-controls'])
  assert.equal(disclosure().props['aria-expanded'], false)
  assert.equal(link.findAllByType('button').length, 0)
  assert.doesNotMatch(textOf(view.toJSON()), /김영준 과장/)
  act(() => disclosure().props.onClick())
  assert.equal(disclosure().props['aria-expanded'], true)
  const content = textOf(view.toJSON())
  for (const value of ['본사', '김영준 과장', '조장희 수석', '한준희 선임', '결과 대기 중', '3.25', '120.5', '2026. 05. 06.']) assert.ok(content.includes(value), value)
  assert.doesNotMatch(content, /2026\. 05\. 08\./)
  act(() => disclosure().props.onClick())
  assert.doesNotMatch(textOf(view.toJSON()), /김영준 과장/)
  act(() => view.update(React.createElement(List, { tickets: [{ ...ticket, issue_type: null }], metric: 'resolution' })))
  assert.match(textOf(view.root.findByType('a')), /확인 불가/)
  assert.equal(disclosure().props['aria-expanded'], false)
})

test('each SLA list keeps independent sorting and widths through filtering and same-report refresh', (t) => {
  const rows = [{ ...ticket, key: 'TACEA-10', elapsed_days: 100 }, { ...ticket, key: 'TACEA-2', elapsed_days: 9 }, { ...ticket, key: 'TACEA-1', elapsed_days: 20 }]
  const original = structuredClone(rows)
  const instance = sourceLoader({ 'presentation/context/JiraContext': { useJira: () => ({ jiraBrowse: 'https://jira.example/browse' }) } })
  const Content = instance('presentation/components/sla-violations/SlaViolationReportContent').default
  const List = instance('presentation/components/sla-violations/SlaViolationList').default
  let current = { ...report, tickets: rows }
  const element = () => React.createElement(Content, { key: current.id, report: current })
  let view
  act(() => { view = TestRenderer.create(element()) })
  t.after(() => act(() => view.unmount()))
  const list = (metric = 'initial_response') => view.root.findAllByType(List).find((node) => node.props.metric === metric)
  const keys = (metric) => list(metric).findAllByType('a').map((node) => node.props.href.split('/').at(-1))
  const click = (name) => act(() => list().findByProps({ 'aria-label': name }).props.onClick())
  click('번호 오름차순 정렬')
  assert.deepEqual(keys(), ['TACEA-1', 'TACEA-2', 'TACEA-10'])
  assert.deepEqual(keys('resolution'), ['TACEA-10', 'TACEA-2', 'TACEA-1'])
  click('번호 오름차순 정렬 중, 내림차순 정렬')
  assert.deepEqual(keys(), ['TACEA-10', 'TACEA-2', 'TACEA-1'])
  click('경과일 오름차순 정렬')
  assert.deepEqual(keys(), ['TACEA-2', 'TACEA-1', 'TACEA-10'])
  click('TACEA-2 상세 펼치기')
  click('경과일 오름차순 정렬 중, 내림차순 정렬')
  assert.deepEqual(keys(), ['TACEA-10', 'TACEA-1', 'TACEA-2'])
  const separator = (metric) => list(metric).findByProps({ role: 'separator', 'aria-label': '번호 열 너비 조절' })
  const initialWidth = separator().props['aria-valuenow']
  act(() => separator().props.onKeyDown({ key: 'ArrowRight', shiftKey: false, preventDefault() {}, stopPropagation() {} }))
  assert.equal(separator().props['aria-valuenow'], initialWidth + 1)
  assert.equal(separator('resolution').props['aria-valuenow'], initialWidth)
  current = { ...current, tickets: rows.filter((row) => row.key !== 'TACEA-1').map((row) => ({ ...row })) }
  act(() => view.update(element()))
  assert.deepEqual(keys(), ['TACEA-10', 'TACEA-2'])
  assert.equal(separator().props['aria-valuenow'], initialWidth + 1)
  assert.equal(list().findByProps({ 'aria-label': 'TACEA-2 상세 접기' }).props['aria-expanded'], true)
  act(() => list().findByType('select').props.onChange({ target: { value: 'key' } }))
  assert.deepEqual(keys(), ['TACEA-2', 'TACEA-10'])
  current = { ...report, id: 11, tickets: rows }
  act(() => view.update(element()))
  assert.deepEqual(keys(), ['TACEA-10', 'TACEA-2', 'TACEA-1'])
  assert.equal(separator().props['aria-valuenow'], initialWidth)
  assert.equal(list().findByProps({ 'aria-label': 'TACEA-2 상세 펼치기' }).props['aria-expanded'], false)
  assert.deepEqual(rows, original)
})

test('SLA column resizing clamps adjacent widths without moving other columns or changing the total', () => {
  const { DEFAULT_SLA_COLUMN_WIDTHS: widths, resizeSlaColumnWidths: resize } = load('presentation/components/sla-violations/SlaViolationTableHeader')
  const original = { ...widths }
  for (const delta of [-100, -0.03, 0.1, 100]) {
    const changed = resize(widths, 'key', 'summary', delta)
    assert.ok(Math.abs(Object.values(changed).reduce((sum, value) => sum + value, 0) - 1) < 1e-12)
    assert.ok(changed.key >= 0.08 && changed.summary >= 0.18 - 1e-12)
    for (const key of ['issue_type', 'created_at', 'elapsed_days']) assert.equal(changed[key], widths[key])
  }
  assert.strictEqual(resize(widths, 'key', 'summary', NaN), widths)
  assert.deepEqual(widths, original)
})

test('SLA resize pointer capture cancels cleanly and never sorts or follows a row link', (t) => {
  const Header = sourceLoader()('presentation/components/sla-violations/SlaViolationTableHeader').default
  const { DEFAULT_SLA_COLUMN_WIDTHS: widths } = load('presentation/components/sla-violations/SlaViolationTableHeader')
  const previousWindow = globalThis.window
  globalThis.window = { getComputedStyle: () => ({ paddingLeft: '4px', paddingRight: '4px', columnGap: '16px' }) }
  t.after(() => { if (previousWindow === undefined) delete globalThis.window; else globalThis.window = previousWindow })
  let sorts = 0
  const deltas = []
  let view
  act(() => { view = TestRenderer.create(React.createElement(Header, { label: '최초응답 위반', widths, sort: null, onSort: () => { sorts += 1 }, onResize: (...args) => deltas.push(args) }), { createNodeMock: () => ({ getBoundingClientRect: () => ({ width: 1008 }) }) }) })
  t.after(() => act(() => view.unmount()))
  const handle = view.root.findByProps({ role: 'separator', 'aria-label': '번호 열 너비 조절' })
  const captured = new Set()
  const currentTarget = { focus() {}, setPointerCapture: (id) => captured.add(id), hasPointerCapture: (id) => captured.has(id), releasePointerCapture: (id) => captured.delete(id) }
  const event = (clientX, pointerId = 1) => ({ clientX, pointerId, button: 0, currentTarget, preventDefault() {}, stopPropagation() {} })
  act(() => handle.props.onPointerDown(event(10)))
  assert.ok(captured.has(1))
  act(() => handle.props.onPointerMove(event(103.6)))
  assert.equal(deltas.length, 1)
  assert.ok(Math.abs(deltas[0][2] - 0.1) < 1e-12)
  act(() => handle.props.onPointerMove(event(150, 2)))
  assert.equal(deltas.length, 1)
  act(() => handle.props.onPointerCancel(event(103.6)))
  assert.equal(captured.size, 0)
  act(() => handle.props.onPointerMove(event(200)))
  assert.equal(deltas.length, 1)
  act(() => handle.props.onPointerDown(event(10)))
  act(() => handle.props.onLostPointerCapture())
  act(() => handle.props.onPointerMove(event(200)))
  act(() => handle.props.onClick(event(200)))
  assert.equal(deltas.length, 1)
  assert.equal(sorts, 0)
})

test('page restores saved controls, separates changed conditions, and submits the chosen period', async (t) => {
  let currentReport = 'previous dashboard'
  let routeId
  const generated = deferred()
  const requests = []
  const setCurrentReport = (value) => { currentReport = value }
  const instance = sourceLoader({
    'react-router-dom': { useParams: () => ({ id: routeId }), useNavigate: () => () => {}, Link: ({ children, to, ...props }) => React.createElement('a', { href: to, ...props }, children) },
    'presentation/context/JiraContext': { useJira: () => ({ jiraBrowse: 'https://jira.example/browse' }) },
    'presentation/state/reportStore': { useReportStore: (selector) => selector({ setCurrentReport }) },
  })
  const Page = instance('presentation/pages/SlaViolationPage').default
  const { ApplicationServicesProvider } = instance('presentation/context/ApplicationServicesContext')
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } })
  const gateway = { getLatest: async () => report, generate: async (request) => { requests.push(request); return generated.promise } }
  const renderPage = () => React.createElement(ApplicationServicesProvider, { services: { slaViolations: gateway } }, React.createElement(QueryClientProvider, { client }, React.createElement(Page)))
  let view
  act(() => { view = TestRenderer.create(renderPage()) })
  t.after(() => { act(() => view.unmount()); client.clear() })
  await until(() => view.root.findByProps({ type: 'date' }).props.value === report.selected_date)
  assert.equal(currentReport, null)
  const monthly = view.root.findAllByType('button').find((button) => textOf(button) === '월간')
  assert.equal(monthly.props['aria-pressed'], true)
  act(() => view.root.findAllByType('button').find((button) => textOf(button) === '연간').props.onClick())
  assert.match(textOf(view.toJSON()), /아래에는 기존 보고서가 표시됩니다/)
  act(() => view.root.findByType('form').props.onSubmit({ preventDefault() {} }))
  await until(() => requests.length === 1)
  assert.deepEqual(requests[0], { period: 'year', date: '2026-05-06' })
  assert.equal(view.root.findByType('fieldset').props.disabled, true)
  assert.equal(view.root.findByProps({ type: 'date' }).props.disabled, true)
  generated.resolve({ ...report, id: 11, period: 'year', start_date: '2026-01-01', end_date: '2026-12-31' })
  await until(() => textOf(view.toJSON()).includes('히스토리에 저장했습니다'))
  assert.equal(view.root.findAllByType('button').find((button) => textOf(button) === '연간').props['aria-pressed'], true)
  assert.doesNotMatch(textOf(view.toJSON()), /아래에는 기존 보고서가 표시됩니다/)
  act(() => view.root.findAllByType('button').find((button) => textOf(button) === '월간').props.onClick())
  assert.match(textOf(view.toJSON()), /아래에는 기존 보고서가 표시됩니다/)
  routeId = '11'
  act(() => view.update(renderPage()))
  assert.equal(view.root.findAllByType('button').find((button) => textOf(button) === '연간').props['aria-pressed'], true)
  assert.doesNotMatch(textOf(view.toJSON()), /아래에는 기존 보고서가 표시됩니다/)
})

test('history pages saved snapshots independently and links directly to each immutable report', async (t) => {
  const calls = []
  const secondPage = deferred()
  const instance = sourceLoader({ 'react-router-dom': { Link: ({ children, to, ...props }) => React.createElement('a', { href: to, ...props }, children) } })
  const History = instance('presentation/components/sla-violations/SlaViolationHistory').default
  const { ApplicationServicesProvider } = instance('presentation/context/ApplicationServicesContext')
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  const gateway = { getHistory: async (limit, offset, signal) => { calls.push({ limit, offset, signal }); return offset === 0 ? Array.from({ length: 20 }, (_, index) => ({ ...report, id: 100 - index })) : secondPage.promise } }
  let view
  act(() => { view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { slaViolations: gateway } }, React.createElement(QueryClientProvider, { client }, React.createElement(History)))) })
  t.after(() => { act(() => view.unmount()); client.clear() })
  await until(() => view.root.findAllByType('a').length === 21)
  assert.equal(view.root.findAllByType('a')[1].props.href, '/sla-violations/history/100')
  act(() => view.root.findAllByType('button').find((button) => textOf(button).includes('다음')).props.onClick())
  await until(() => calls.length === 2)
  assert.deepEqual(calls.map(({ limit, offset }) => ({ limit, offset })), [{ limit: 20, offset: 0 }, { limit: 20, offset: 20 }])
  assert.equal(view.root.findAllByType('a').length, 1)
  assert.equal(view.root.findAllByType('button').find((button) => textOf(button).includes('이전')).props.disabled, true)
  secondPage.resolve([{ ...report, id: 79 }])
  await until(() => view.root.findAllByType('a').length === 2)
  assert.equal(view.root.findAllByType('a')[1].props.href, '/sla-violations/history/79')
  assert.equal(view.root.findAllByType('button').find((button) => textOf(button).includes('다음')).props.disabled, true)
})
