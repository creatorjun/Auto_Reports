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
const { filterSlaViolationTickets, slaViolationFilterOptions } = load('domain/SlaViolationFilters')
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
  assert.deepEqual(metricKeys(), [['TACEA-1234', 'TACEA-2'], ['TACEA-1234', 'TACEA-3']])
  assert.match(textOf(view.toJSON()), /요청 유형이 저장되지 않은 티켓\s+1\s*건/)
  assert.equal(view.root.findAllByProps({ 'aria-label': '이슈 제목 검색' }).length, 0)
  click('필터 펼치기')
  click('확인 불가')
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
  assert.deepEqual(metricKeys(), [['TACEA-1234', 'TACEA-2'], ['TACEA-1234', 'TACEA-3']])
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
  const columns = view.root.findAllByType('div').find((node) => node.props['aria-hidden'] === 'true')
  assert.deepEqual(columns.findAllByType('span').map((node) => textOf(node)), ['번호', '제목', '유형', '생성일', '경과일', '상세'])
  assert.equal(view.root.findByType('button').props['aria-expanded'], false)
  assert.equal(link.findAllByType('button').length, 0)
  assert.doesNotMatch(textOf(view.toJSON()), /김영준 과장/)
  act(() => view.root.findByType('button').props.onClick())
  assert.equal(view.root.findByType('button').props['aria-expanded'], true)
  const content = textOf(view.toJSON())
  for (const value of ['본사', '김영준 과장', '조장희 수석', '한준희 선임', '결과 대기 중', '3.25', '120.5', '2026. 05. 06.']) assert.ok(content.includes(value), value)
  assert.doesNotMatch(content, /2026\. 05\. 08\./)
  act(() => view.root.findByType('button').props.onClick())
  assert.doesNotMatch(textOf(view.toJSON()), /김영준 과장/)
  act(() => view.update(React.createElement(List, { tickets: [{ ...ticket, issue_type: null }], metric: 'resolution' })))
  assert.match(textOf(view.root.findByType('a')), /확인 불가/)
  assert.equal(view.root.findByType('button').props['aria-expanded'], false)
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
  await until(() => view.root.findByType('input').props.value === report.selected_date)
  assert.equal(currentReport, null)
  const monthly = view.root.findAllByType('button').find((button) => textOf(button) === '월간')
  assert.equal(monthly.props['aria-pressed'], true)
  act(() => view.root.findAllByType('button').find((button) => textOf(button) === '연간').props.onClick())
  assert.match(textOf(view.toJSON()), /아래에는 기존 보고서가 표시됩니다/)
  act(() => view.root.findByType('form').props.onSubmit({ preventDefault() {} }))
  await until(() => requests.length === 1)
  assert.deepEqual(requests[0], { period: 'year', date: '2026-05-06' })
  assert.equal(view.root.findByType('fieldset').props.disabled, true)
  assert.equal(view.root.findByType('input').props.disabled, true)
  generated.resolve({ ...report, id: 11, period: 'year', start_date: '2026-01-01', end_date: '2026-12-31' })
  await until(() => textOf(view.toJSON()).includes('히스토리에 저장했습니다'))
  assert.match(textOf(view.toJSON()), /2026-01-01/)
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
