// frontend/tests/slaStatus.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
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
    if (filename.endsWith('.json')) return JSON.parse(fs.readFileSync(filename, 'utf8'))
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX }, fileName: filename,
    }).outputText
    new Function('require', 'module', 'exports', compiled)((dependency) => {
      if (dependency.startsWith('@/')) return load(dependency.slice(2))
      if (dependency.startsWith('.')) return load(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)).replaceAll('\\', '/'))
      return require(dependency)
    }, module, module.exports)
    return module.exports
  }
  return load
}

const jiraOverride = { 'presentation/context/JiraContext': { useJira: () => ({ jiraBrowse: 'https://jira.example.test/browse' }) } }
const load = sourceLoader(jiraOverride)
const { defaultSlaStatusFilters, slaStatusCounts, slaStatusFilterOptions, filterSlaStatusTickets } = load('application/services/slaStatus')
function sla(overrides = {}) { return { sla_id: 'response', sla_name: '최초응답', goal_millis: 36_000_000, remaining_millis: 1_800_000, remaining_percent: 5, paused: false, ...overrides } }
function ticket(overrides = {}) { return { key: 'TAC-1', summary: '방화벽 점검', status: '분석중', assignee: '담당자', slas: [sla()], ...overrides } }
function rows() {
  return [
    ticket({ key: 'TAC-10', summary: '혼합 SLA', slas: [sla({ remaining_percent: 10 }), sla({ sla_id: 'resolution', sla_name: '해결시간', remaining_percent: 2, remaining_millis: 720_000, paused: true })] }),
    ticket({ key: 'TAC-2', summary: '진행 티켓', slas: [sla({ remaining_percent: 9.999 })] }),
    ticket({ key: 'TAC-3', status: '보류중', assignee: '미지정', slas: [sla({ sla_id: 'resolution', sla_name: '해결시간', remaining_percent: 29.999, paused: true })] }),
  ]
}
function snapshot(tickets = rows()) { return { generated_at: '2026-10-21T03:00:00Z', threshold_percent: 30, ticket_count: tickets.length, sla_count: tickets.reduce((sum, ticket) => sum + ticket.slas.length, 0), tickets } }
function query(overrides = {}) { return { data: snapshot(), error: null, refreshError: null, refreshing: false, refresh() {}, ...overrides } }
const currentReport = { setCurrentReport() {} }
function renderPage(t, state) {
  const instance = sourceLoader({ ...jiraOverride, 'presentation/hooks/useSlaStatus': { useSlaStatus: () => state }, 'presentation/state/reportStore': { useReportStore: (selector) => selector(currentReport) } })
  const Page = instance('presentation/pages/SlaStatusPage').default
  let view
  act(() => { view = TestRenderer.create(React.createElement(Page)) })
  t.after(() => act(() => view.unmount()))
  return { view, update(next) { Object.assign(state, next); act(() => view.update(React.createElement(Page))) } }
}
function visibleKeys(view) { return view.root.findAll((node) => node.type === 'tr' && node.props['data-ticket-key']).map((node) => node.props['data-ticket-key']) }
function text(view) { return JSON.stringify(view.toJSON()) }
function selectByOption(view, value) { return view.root.findAllByType('select').find((node) => node.findAllByType('option').some((option) => option.props.value === value)) }
function clickSummary(view, label) { const button = view.root.findByProps({ 'aria-label': 'SLA 현황 요약 필터' }).findAllByType('button').find((node) => node.findAllByType('span').some((span) => span.children.includes(label))); act(() => button.props.onClick()); return button }
function deferred() { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no }); return { promise, resolve, reject } }
async function until(predicate) { const deadline = Date.now() + 3000; while (!predicate()) { assert.ok(Date.now() < deadline, 'Timed out waiting for state'); await act(async () => { await new Promise((resolve) => setTimeout(resolve, 15)) }) } }
function setupHook(t, gateway) {
  const instance = sourceLoader()
  const { ApplicationServicesProvider } = instance('presentation/context/ApplicationServicesContext')
  const { useSlaStatus } = instance('presentation/hooks/useSlaStatus')
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } } })
  let observed, view
  function Probe() { observed = useSlaStatus(); return null }
  act(() => { view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { slaStatus: gateway } }, React.createElement(QueryClientProvider, { client }, React.createElement(Probe)))) })
  t.after(() => { act(() => view.unmount()); client.clear() })
  return { client, unmount: () => act(() => view.unmount()), get observed() { return observed } }
}

test('counts use unique tickets per scope and mixed running/paused tickets can belong to both', () => {
  assert.deepEqual(slaStatusCounts(rows()), { all: 3, urgent: 2, running: 2, paused: 2 })
  assert.deepEqual(slaStatusCounts([]), { all: 0, urgent: 0, running: 0, paused: 0 })
  assert.deepEqual(slaStatusFilterOptions(rows()), { statuses: ['보류중', '분석중'], stages: [{ id: 'response', name: '최초응답' }, { id: 'resolution', name: '해결시간' }] })
})

test('scope and SLA stage intersect on the same metric, then search and status filter whole tickets without mutation', () => {
  const original = rows()
  const before = structuredClone(original)
  const filters = { ...defaultSlaStatusFilters(), scope: 'urgent', stage: 'response' }
  assert.deepEqual(filterSlaStatusTickets(original, filters).map((row) => row.key), ['TAC-2'])
  const selected = filterSlaStatusTickets(original, { ...defaultSlaStatusFilters(), scope: 'paused', stage: 'resolution', status: '분석중', search: 'ｔａｃ－１０ 혼합 담당자' })
  assert.equal(selected.length, 1)
  assert.deepEqual(selected[0].slas.map((sla) => sla.sla_id), ['resolution'])
  assert.deepEqual(filterSlaStatusTickets(original, { ...filters, status: '보류중' }), [])
  assert.deepEqual(original, before)
})

test('default sorting uses the lowest displayed remaining percentage with stable numeric ticket ties', () => {
  const original = rows()
  assert.deepEqual(filterSlaStatusTickets(original, defaultSlaStatusFilters()).map((row) => row.key), ['TAC-10', 'TAC-2', 'TAC-3'])
  assert.deepEqual(filterSlaStatusTickets(original, { ...defaultSlaStatusFilters(), sort: 'key' }).map((row) => row.key), ['TAC-2', 'TAC-3', 'TAC-10'])
  assert.deepEqual(filterSlaStatusTickets([ticket({ key: 'TAC-10' }), ticket({ key: 'TAC-2' })], defaultSlaStatusFilters()).map((row) => row.key), ['TAC-2', 'TAC-10'])
  assert.deepEqual(filterSlaStatusTickets(original, { ...defaultSlaStatusFilters(), sort: 'remaining_millis' }).map((row) => row.key), ['TAC-10', 'TAC-2', 'TAC-3'])
})

test('summary buttons filter actual rows and combine with stage, status and search controls', (t) => {
  const { view } = renderPage(t, query())
  assert.deepEqual(visibleKeys(view), ['TAC-10', 'TAC-2', 'TAC-3'])
  const buttons = view.root.findByProps({ 'aria-label': 'SLA 현황 요약 필터' }).findAllByType('button')
  assert.equal(buttons.length, 4)
  for (const button of buttons) { assert.equal(button.props.type, 'button'); assert.equal(button.props['aria-controls'], 'sla-status-results') }
  clickSummary(view, '잔여 10% 미만')
  assert.deepEqual(visibleKeys(view), ['TAC-10', 'TAC-2'])
  act(() => selectByOption(view, 'response').props.onChange({ target: { value: 'response' } }))
  assert.deepEqual(visibleKeys(view), ['TAC-2'])
  act(() => selectByOption(view, '보류중').props.onChange({ target: { value: '보류중' } }))
  assert.deepEqual(visibleKeys(view), [])
  assert.match(text(view), /선택한 조건에 맞는 티켓이 없습니다/)
  const reset = view.root.findAllByType('button').find((node) => node.children.includes('필터 초기화'))
  act(() => reset.props.onClick())
  act(() => view.root.findByProps({ type: 'search' }).props.onChange({ target: { value: '미지정' } }))
  assert.deepEqual(visibleKeys(view), ['TAC-3'])
  act(() => reset.props.onClick())
  clickSummary(view, '일시정지 SLA 포함')
  assert.deepEqual(visibleKeys(view), ['TAC-10', 'TAC-3'])
  clickSummary(view, '일시정지 SLA 포함')
  assert.deepEqual(visibleKeys(view), ['TAC-10', 'TAC-2', 'TAC-3'])
  assert.equal(view.root.findAllByProps({ type: 'date' }).length, 0)
})

test('one row keeps multiple SLA summaries, accurate boundary labels and accessible Jira links', () => {
  const List = load('presentation/components/sla-status/SlaStatusList').default
  const html = renderToStaticMarkup(React.createElement(List, { tickets: [ticket({ key: 'TAC-1/extra', summary: '<script>escaped</script>', slas: [sla({ remaining_percent: 29.999 }), sla({ sla_id: 'resolution', sla_name: '해결시간', remaining_percent: 0.01, paused: true })] })], isFiltered: false }))
  assert.equal((html.match(/data-ticket-key=/g) ?? []).length, 1)
  assert.match(html, /29.9%/)
  assert.match(html, /0.1% 미만/)
  assert.doesNotMatch(html, />30%|<script>/)
  assert.match(html, /&lt;script&gt;escaped&lt;\/script&gt;/)
  assert.match(html, /href="https:\/\/jira.example.test\/browse\/TAC-1%2Fextra" target="_blank" rel="noopener noreferrer"/)
  assert.match(html, /가로로 스크롤/)
  assert.match(html, /overflow-x-auto/)
})

test('refresh preserves vanished filter choices visibly instead of showing a different effective selection', (t) => {
  const { view, update } = renderPage(t, query())
  act(() => selectByOption(view, 'response').props.onChange({ target: { value: 'response' } }))
  act(() => selectByOption(view, '분석중').props.onChange({ target: { value: '분석중' } }))
  update({ data: snapshot([ticket({ status: '진행중', slas: [sla({ sla_id: 'resolution', sla_name: '해결시간' })] })]) })
  const status = selectByOption(view, '분석중')
  const stage = selectByOption(view, 'response')
  assert.equal(status.props.value, '분석중')
  assert.equal(stage.props.value, 'response')
  assert.equal(status.findAllByType('option').find((option) => option.props.value === '분석중').children.join(''), '분석중 (현재 결과 없음)')
  assert.equal(stage.findAllByType('option').find((option) => option.props.value === 'response').children.join(''), '최초응답 (현재 결과 없음)')
  assert.deepEqual(visibleKeys(view), [])
})

test('expanding a ticket shows SLA-based durations and separates calendar age without inventing missing values', (t) => {
  const row = ticket({ elapsed_days: 40, created_at: '2026-09-11T00:00:00Z', customer: '고객사', status_durations: [{ status: '분석중', hours: 9 }, { status: '진행중', hours: 3 }], status_durations_basis: 'resolution_sla', status_duration_calendar: '업무시간 달력', warnings: ['일부 이력 확인 필요'] })
  const { view } = renderPage(t, query({ data: snapshot([row]) }))
  assert.match(text(view), /최대 체류 단계/)
  assert.match(text(view), /9시간/)
  const button = view.root.findByProps({ 'aria-label': 'TAC-1 상세 펼치기' })
  act(() => button.props.onClick())
  assert.equal(button.props['aria-expanded'], true)
  assert.match(text(view), /상태별 체류시간/)
  assert.match(text(view), /해결시간 SLA 기준/)
  assert.match(text(view), /생성 후 달력 경과일/)
  assert.match(text(view), /40일/)
  assert.match(text(view), /9시간 30분/)
  assert.match(text(view), /업무시간 달력/)
  assert.match(text(view), /일부 이력 확인 필요/)
  const missing = renderPage(t, query({ data: snapshot([ticket()]) })).view
  act(() => missing.root.findByProps({ 'aria-label': 'TAC-1 상세 펼치기' }).props.onClick())
  assert.match(text(missing), /상태별 SLA 시간을 확인할 수 없습니다/)
  assert.doesNotMatch(text(missing), /이전 보고서|"0시간"/)
})

test('empty snapshots differ from filtered results and refresh errors keep prior rows and collection timestamp', (t) => {
  const empty = renderPage(t, query({ data: snapshot([]) })).view
  assert.match(text(empty), /잔여 30% 미만인 SLA 티켓이 없습니다/)
  let refreshes = 0
  const { view, update } = renderPage(t, query({ refresh() { refreshes++ } }))
  const originalKeys = visibleKeys(view)
  act(() => view.root.findAllByType('button').find((node) => node.children.includes('새로고침')).props.onClick())
  assert.equal(refreshes, 1)
  update({ refreshError: new Error('network failure') })
  assert.deepEqual(visibleKeys(view), originalKeys)
  assert.match(text(view), /마지막으로 수집한 데이터를 유지/)
  assert.match(text(view), /2026\. 10\. 21\. 12:00/)
  assert.equal(view.root.findAllByProps({ role: 'alert' }).length, 1)
})

test('HTTP adapter uses the authenticated shared client, GET, cancellation and explicit force parameter', async () => {
  const calls = []
  const data = snapshot()
  const instance = sourceLoader({ 'infrastructure/api/client': { default: { async get(...args) { calls.push(args); return { data } } } } })
  const { slaStatusApi } = instance('infrastructure/api/slaStatusApi')
  const controller = new AbortController()
  assert.equal(await slaStatusApi.getSnapshot(false, controller.signal), data)
  assert.equal(await slaStatusApi.getSnapshot(true, controller.signal), data)
  assert.deepEqual(calls, [
    ['/sla-status', { params: undefined, signal: controller.signal, timeout: 120_000 }],
    ['/sla-status', { params: { refresh: true }, signal: controller.signal, timeout: 120_000 }],
  ])
})

test('query loads cached endpoint, deduplicates forced refresh, preserves data on failure and replaces it on success', async (t) => {
  const calls = []
  const failure = deferred()
  const success = deferred()
  const oldData = snapshot()
  const newData = { ...snapshot([ticket()]), generated_at: '2026-10-21T04:00:00Z' }
  const state = setupHook(t, { getSnapshot(refresh, signal) { calls.push({ refresh, signal }); return calls.length === 1 ? Promise.resolve(oldData) : calls.length === 2 ? failure.promise : success.promise } })
  await until(() => !!state.observed.data)
  assert.equal(calls[0].refresh, false)
  act(() => { state.observed.refresh(); state.observed.refresh() })
  await until(() => calls.length === 2)
  assert.equal(calls[1].refresh, true)
  assert.deepEqual(state.observed.data, oldData)
  await act(async () => failure.reject(new Error('unavailable')))
  await until(() => !!state.observed.refreshError && !state.observed.refreshing)
  assert.deepEqual(state.observed.data, oldData)
  act(() => state.observed.refresh())
  await until(() => calls.length === 3)
  await act(async () => success.resolve(newData))
  await until(() => state.observed.data.generated_at === newData.generated_at && !state.observed.refreshing)
  assert.equal(state.observed.refreshError, null)
})

test('unmount aborts both the ordinary request and the forced refresh request', async (t) => {
  let initialSignal
  const initial = setupHook(t, { getSnapshot(_refresh, signal) { initialSignal = signal; return new Promise(() => {}) } })
  await until(() => !!initialSignal)
  initial.unmount()
  assert.equal(initialSignal.aborted, true)
  let refreshSignal
  const pending = deferred()
  const state = setupHook(t, { getSnapshot(refresh, signal) { if (refresh) { refreshSignal = signal; return pending.promise } return Promise.resolve(snapshot()) } })
  await until(() => !!state.observed.data)
  act(() => state.observed.refresh())
  await until(() => !!refreshSignal)
  state.unmount()
  assert.equal(refreshSignal.aborted, true)
  state.client.removeQueries({ queryKey: ['sla-status'] })
  await act(async () => pending.resolve(snapshot()))
  assert.equal(state.client.getQueryData(['sla-status']), undefined)
})

test('leaving immediately after a refresh click does not start an unowned request', async (t) => {
  const calls = []
  const state = setupHook(t, { getSnapshot(refresh) { calls.push(refresh); return Promise.resolve(snapshot()) } })
  await until(() => !!state.observed.data)
  await act(async () => { state.observed.refresh(); state.unmount() })
  assert.deepEqual(calls, [false])
})
