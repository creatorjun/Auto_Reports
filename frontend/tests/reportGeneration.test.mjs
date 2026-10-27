// frontend/tests/reportGeneration.test.mjs
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

function deferred() {
  let resolve
  let reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

async function settle() { await act(async () => { await new Promise((resolve) => setTimeout(resolve, 10)) }) }
async function until(predicate) {
  const deadline = Date.now() + 2500
  while (!predicate()) { assert.ok(Date.now() < deadline, 'Timed out waiting for generation state'); await settle() }
}

function textOf(node) {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textOf).join(' ')
  return node?.children ? textOf(node.children) : ''
}

const previous = { id: 1, scope: 'standard', week_start: '2026-05-04', week_end: '2026-05-10', widgets: {} }
const created = { ...previous, id: 2, week_start: '2026-01-01', week_end: '2026-12-31' }

function setup(t, gateway = {}) {
  let pathname = '/'
  const navigation = []
  const requests = []
  let stream
  let closeCount = 0
  const load = sourceLoader({ 'react-router-dom': { useLocation: () => ({ pathname }), useNavigate: () => (url) => navigation.push(url) } })
  const { ApplicationServicesProvider } = load('presentation/context/ApplicationServicesContext')
  const { ReportGenerationProvider, useReportGeneration } = load('presentation/context/ReportGenerationContext')
  const { useUiStore } = load('presentation/state/uiStore')
  const Form = load('presentation/components/common/DashboardGenerateForm').default
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } })
  client.setQueryData(['reports', 'latest'], previous)
  client.setQueryData(['reports', 'list', 0, 20], [previous])
  let context
  function Probe({ showForm }) {
    context = useReportGeneration()
    return showForm ? React.createElement(Form, { report: previous }) : null
  }
  const reports = {
    trigger: async (request) => { requests.push(request); return { job_id: 'job-1' } },
    getById: async () => created,
    watchJob: (jobId, callbacks, timeoutMs) => { stream = { jobId, callbacks, timeoutMs }; return { close: () => { closeCount += 1 } } },
    ...gateway,
  }
  function element(showForm = true) { return React.createElement(ApplicationServicesProvider, { services: { reports } }, React.createElement(QueryClientProvider, { client }, React.createElement(ReportGenerationProvider, null, React.createElement(Probe, { showForm })))) }
  let view
  act(() => { view = TestRenderer.create(element()) })
  t.after(() => { act(() => view.unmount()); client.clear() })
  return {
    client, navigation, requests, view, load,
    get context() { return context }, get stream() { return stream }, get closeCount() { return closeCount },
    get ui() { return useUiStore.getState() },
    move: (url, showForm) => { pathname = url; act(() => view.update(element(showForm))) },
    unmount: () => act(() => view.unmount()),
  }
}

test('dashboard and SLA share complete Monday-through-Sunday weekly periods', () => {
  const load = sourceLoader()
  const period = load('application/services/reportPeriod')
  const sla = load('application/services/slaViolationReport')
  assert.equal(sla.slaDateRange, period.reportDateRange)
  assert.equal(sla.slaToday, period.reportToday)
  for (const [date, start, end] of [
    ['2026-10-09', '2026-10-05', '2026-10-11'],
    ['2026-10-05', '2026-10-05', '2026-10-11'],
    ['2026-10-11', '2026-10-05', '2026-10-11'],
    ['2026-01-01', '2025-12-29', '2026-01-04'],
    ['2026-03-01', '2026-02-23', '2026-03-01'],
  ]) assert.deepEqual(period.reportDateRange('week', date), { start, end })
  for (const day of [12, 13, 14, 15, 16, 17, 18]) {
    assert.deepEqual(period.reportDateRange('week', `2026-10-${day}`), { start: '2026-10-12', end: '2026-10-18' })
  }
  assert.equal(period.reportToday(new Date('2026-10-13T15:00:00Z')), '2026-10-14')
})

test('dashboard and SLA month and year cover the complete calendar period and reject invalid dates', () => {
  const { reportDateRange } = sourceLoader()('application/services/reportPeriod')
  assert.deepEqual(reportDateRange('month', '2026-10-09'), { start: '2026-10-01', end: '2026-10-31' })
  assert.deepEqual(reportDateRange('year', '2026-10-09'), { start: '2026-01-01', end: '2026-12-31' })
  assert.deepEqual(reportDateRange('month', '2024-02-29'), { start: '2024-02-01', end: '2024-02-29' })
  for (const period of ['day', 'week', 'month', 'year']) {
    for (const date of ['', '2026-2-01', '2026-02-29', '2026-13-01', '0000-01-01']) {
      assert.equal(reportDateRange(period, date), null)
    }
  }
})

test('daily report periods keep the selected day at month year and leap-day boundaries', () => {
  const { reportDateRange, REPORT_PERIOD_LABELS } = sourceLoader()('application/services/reportPeriod')
  assert.equal(REPORT_PERIOD_LABELS.day, '일간')
  for (const date of ['2026-10-27', '2026-01-01', '2026-12-31', '2024-02-29']) {
    assert.deepEqual(reportDateRange('day', date), { start: date, end: date })
  }
})

test('dashboard form compares a saved partial week against the full week without changing the saved report', (t) => {
  const generation = { generate() {}, pending: false, error: null, lastRequest: { period: 'week', date: '2026-10-09' } }
  const Form = sourceLoader({ 'presentation/context/ReportGenerationContext': { useReportGeneration: () => generation } })('presentation/components/common/DashboardGenerateForm').default
  const report = { ...previous, week_start: '2026-10-05', week_end: '2026-10-09' }
  const original = structuredClone(report)
  let view
  act(() => { view = TestRenderer.create(React.createElement(Form, { report })) })
  t.after(() => act(() => view.unmount()))
  assert.match(textOf(view.toJSON()), /선택한 기간과 현재 보고서의 기간이 다릅니다/)
  act(() => view.update(React.createElement(Form, { report: { ...report, week_end: '2026-10-11' } })))
  assert.doesNotMatch(textOf(view.toJSON()), /선택한 기간과 현재 보고서의 기간이 다릅니다/)
  act(() => view.root.findByType('input').props.onChange({ target: { value: '2026-10-14' } }))
  assert.match(textOf(view.toJSON()), /선택한 기간과 현재 보고서의 기간이 다릅니다/)
  act(() => view.root.findByType('input').props.onChange({ target: { value: '2026-10-11' } }))
  assert.doesNotMatch(textOf(view.toJSON()), /선택한 기간과 현재 보고서의 기간이 다릅니다/)
  assert.deepEqual(report, original)
})

test('API forwards explicit period and selected date without legacy date range inference', async () => {
  const calls = []
  const client = { post: async (...args) => { calls.push(args); return { data: { job_id: 'job-1' } } } }
  const api = sourceLoader({ 'infrastructure/api/client': { default: client } })('infrastructure/api/reportApi').reportApi
  for (const period of ['day', 'year']) await api.trigger({ period, date: '2026-05-06' })
  assert.deepEqual(calls, ['day', 'year'].map((period) => ['/trigger/', { period, date: '2026-05-06' }]))
})

test('daily selection submits its date and shows the saved one-day report only after completion', async (t) => {
  const daily = { ...created, week_start: '2024-02-29', week_end: '2024-02-29' }
  const state = setup(t, { getById: async () => daily })
  const options = () => state.view.root.findAllByType('button').filter((node) => node.props['aria-pressed'] !== undefined)
  assert.deepEqual(options().map(textOf), ['일간', '주간', '월간', '연간'])
  assert.equal(options().find((node) => textOf(node) === '주간').props['aria-pressed'], true)
  act(() => options().find((node) => textOf(node) === '일간').props.onClick())
  act(() => state.view.root.findByType('input').props.onChange({ target: { value: '2024-02-29' } }))
  assert.equal(options().find((node) => textOf(node) === '일간').props['aria-pressed'], true)
  assert.equal(state.client.getQueryData(['reports', 'latest']), previous)
  assert.equal(state.requests.length, 0)
  act(() => state.view.root.findByType('form').props.onSubmit({ preventDefault() {} }))
  await until(() => state.stream)
  assert.deepEqual(state.requests, [{ period: 'day', date: '2024-02-29' }])
  assert.equal(state.context.pending, true)
  assert.equal(state.view.root.findByType('fieldset').props.disabled, true)
  assert.equal(state.client.getQueryData(['reports', 'latest']), previous)
  act(() => state.stream.callbacks.onComplete(daily.id))
  await until(() => !state.context.pending)
  assert.deepEqual(state.client.getQueryData(['reports', 'latest']), daily)
  assert.deepEqual(state.client.getQueryData(['reports', daily.id]), daily)
  assert.deepEqual(state.navigation, ['/reports/2'])
  state.move('/issues', false)
  state.move('/', true)
  assert.equal(options().find((node) => textOf(node) === '일간').props['aria-pressed'], true)
  assert.equal(state.view.root.findByType('input').props.value, '2024-02-29')
})

test('daily form compares saved dates and rejects invalid or future days without submitting', (t) => {
  const requests = []
  const generation = { generate: (request) => requests.push(request), pending: false, error: null, lastRequest: { period: 'day', date: '2024-02-29' } }
  const Form = sourceLoader({ 'presentation/context/ReportGenerationContext': { useReportGeneration: () => generation } })('presentation/components/common/DashboardGenerateForm').default
  const report = { ...previous, week_start: '2024-02-29', week_end: '2024-02-29' }
  let view
  act(() => { view = TestRenderer.create(React.createElement(Form, { report })) })
  t.after(() => act(() => view.unmount()))
  assert.doesNotMatch(textOf(view.toJSON()), /선택한 기간과 현재 보고서의 기간이 다릅니다/)
  for (const date of ['2026-02-29', '9999-01-01', '']) {
    act(() => view.root.findByType('input').props.onChange({ target: { value: date } }))
    assert.equal(view.root.findAllByType('button').find((node) => node.props.type === 'submit').props.disabled, true)
    act(() => view.root.findByType('form').props.onSubmit({ preventDefault() {} }))
  }
  assert.deepEqual(requests, [])
  act(() => view.root.findByType('input').props.onChange({ target: { value: '2024-03-01' } }))
  assert.match(textOf(view.toJSON()), /선택한 기간과 현재 보고서의 기간이 다릅니다/)
  act(() => view.root.findByType('form').props.onSubmit({ preventDefault() {} }))
  assert.deepEqual(requests, [{ period: 'day', date: '2024-03-01' }])
})

test('period form works without an existing report and prevents invalid future dates', (t) => {
  const requests = []
  const generation = { generate: (request) => requests.push(request), pending: false, error: null, lastRequest: null }
  const load = sourceLoader({ 'presentation/context/ReportGenerationContext': { useReportGeneration: () => generation } })
  const Form = load('presentation/components/common/DashboardGenerateForm').default
  let view
  act(() => { view = TestRenderer.create(React.createElement(Form)) })
  t.after(() => act(() => view.unmount()))
  const date = () => view.root.findByType('input')
  const submit = () => view.root.findAllByType('button').find((item) => item.props.type === 'submit')
  act(() => view.root.findAllByType('button').find((item) => textOf(item) === '월간').props.onClick())
  act(() => date().props.onChange({ target: { value: '2024-02-29' } }))
  assert.equal(date().props.value, '2024-02-29')
  assert.equal(submit().props.disabled, false)
  act(() => view.root.findByType('form').props.onSubmit({ preventDefault() {} }))
  assert.deepEqual(requests, [{ period: 'month', date: '2024-02-29' }])
  act(() => date().props.onChange({ target: { value: '9999-01-01' } }))
  assert.equal(submit().props.disabled, true)
  assert.match(textOf(view.toJSON()), /유효한 날짜/)
  act(() => view.root.findByType('form').props.onSubmit({ preventDefault() {} }))
  assert.equal(requests.length, 1)
})

test('generation stays pending through job completion and loads the exact saved report', async (t) => {
  const detail = deferred()
  const state = setup(t, { getById: async (id) => { assert.equal(id, 2); return detail.promise } })
  const request = { period: 'year', date: '2026-05-06' }
  act(() => { state.context.generate(request); state.context.generate(request) })
  await until(() => state.stream)
  assert.deepEqual(state.requests, [request])
  assert.equal(state.context.pending, true)
  assert.equal(state.stream.timeoutMs, 600_000)
  assert.equal(state.view.root.findByType('fieldset').props.disabled, true)
  assert.equal(state.view.root.findByType('input').props.disabled, true)
  assert.equal(state.client.getQueryData(['reports', 'latest']), previous)
  act(() => state.stream.callbacks.onComplete(2))
  await settle()
  assert.equal(state.context.pending, true)
  detail.resolve(created)
  await until(() => !state.context.pending)
  assert.deepEqual(state.client.getQueryData(['reports', 'latest']), created)
  assert.deepEqual(state.client.getQueryData(['reports', 2]), created)
  assert.equal(state.client.getQueryState(['reports', 'list', 0, 20]).isInvalidated, true)
  assert.deepEqual(state.navigation, ['/reports/2'])
  assert.equal(state.ui.triggerMessage, null)
})

test('request failure unlocks generation and preserves the displayed report', async (t) => {
  const state = setup(t, { trigger: async () => { throw new Error('unavailable') } })
  act(() => state.context.generate({ period: 'week', date: '2026-05-06' }))
  await until(() => state.context.error)
  assert.equal(state.context.pending, false)
  assert.equal(state.stream, undefined)
  assert.equal(state.client.getQueryData(['reports', 'latest']), previous)
  assert.match(textOf(state.view.toJSON()), /보고서 생성 실패/)
})

test('stream failures and timeouts release controls without changing saved data', async (t) => {
  const state = setup(t)
  act(() => state.context.generate({ period: 'week', date: '2026-05-06' }))
  await until(() => state.stream)
  act(() => state.stream.callbacks.onError('Jira unavailable'))
  assert.equal(state.context.pending, false)
  assert.equal(state.client.getQueryData(['reports', 'latest']), previous)
  act(() => state.context.generate({ period: 'month', date: '2026-05-06' }))
  await until(() => state.requests.length === 2)
  act(() => state.stream.callbacks.onTimeout())
  assert.equal(state.context.pending, false)
  assert.match(state.context.error, /히스토리에서 완료 여부/)
  assert.equal(state.client.getQueryData(['reports', 'latest']), previous)
})

test('leaving the dashboard keeps job monitoring alive without redirecting another menu', async (t) => {
  const state = setup(t)
  act(() => state.context.generate({ period: 'year', date: '2026-05-06' }))
  await until(() => state.stream)
  state.move('/sla-violations', false)
  assert.equal(state.closeCount, 0)
  act(() => state.stream.callbacks.onComplete(2))
  await until(() => !state.context.pending)
  assert.deepEqual(state.navigation, [])
  assert.deepEqual(state.client.getQueryData(['reports', 'latest']), created)
  state.move('/', true)
  assert.equal(state.view.root.findByType('input').props.value, '2026-05-06')
  assert.equal(state.view.root.findAllByType('button').find((item) => textOf(item) === '연간').props['aria-pressed'], true)
})

test('leaving the layout closes an existing stream and avoids starting one after logout', async (t) => {
  const active = setup(t)
  act(() => active.context.generate({ period: 'week', date: '2026-05-06' }))
  await until(() => active.stream)
  active.unmount()
  assert.equal(active.closeCount, 1)
  const accepted = deferred()
  const pending = setup(t, { trigger: () => accepted.promise })
  act(() => pending.context.generate({ period: 'week', date: '2026-05-06' }))
  await settle()
  pending.unmount()
  accepted.resolve({ job_id: 'late-job' })
  await settle()
  assert.equal(pending.stream, undefined)
})

test('annual menu generation keeps annual data separate from the standard dashboard cache', async (t) => {
  const annual = { ...created, scope: 'annual', report_year: 2025 }
  const state = setup(t, { getById: async () => annual })
  state.move('/reports/annual/2025', false)
  act(() => state.context.generate({ start_date: '2025-01-01', end_date: '2025-12-31' }))
  await until(() => state.stream)
  act(() => state.stream.callbacks.onComplete(2))
  await until(() => !state.context.pending)
  assert.equal(state.client.getQueryData(['reports', 'annual', 2025]), annual)
  assert.equal(state.client.getQueryData(['reports', 'latest']), previous)
  assert.equal(state.context.lastRequest, null)
  assert.deepEqual(state.navigation, [])
})

for (const scope of ['standard', 'annual']) {
  test(`leaving the layout during ${scope} cache cancellation discards report completion`, async (t) => {
    const cancellation = deferred()
    const report = { ...created, scope, report_year: scope === 'annual' ? 2025 : null }
    const state = setup(t, { getById: async () => report })
    let cancelStarted = false
    state.client.cancelQueries = () => { cancelStarted = true; return cancellation.promise }
    act(() => state.context.generate({ period: 'year', date: '2026-05-06' }))
    await until(() => state.stream)
    act(() => state.stream.callbacks.onComplete(2))
    await until(() => cancelStarted)
    state.unmount()
    state.client.clear()
    cancellation.resolve()
    await settle()
    assert.equal(state.client.getQueryCache().getAll().length, 0)
    assert.deepEqual(state.navigation, [])
  })
}

test('annual menu uses the legacy annual contract with calendar years and current-year cutoff', (t) => {
  const requests = []
  const generation = { generate: (request) => requests.push(request), pending: false, error: null }
  const { annualReportDateRange } = sourceLoader()('application/services/reportPeriod')
  const load = sourceLoader({
    'presentation/context/ReportGenerationContext': { useReportGeneration: () => generation },
    'application/services/reportPeriod': { annualReportDateRange: (year) => annualReportDateRange(year, '2026-10-14') },
  })
  const AnnualGenerate = load('presentation/components/annual/AnnualReportGenerate').default
  let view
  act(() => { view = TestRenderer.create(React.createElement(AnnualGenerate, { year: 2025 })) })
  t.after(() => act(() => view.unmount()))
  act(() => view.root.findByType('button').props.onClick())
  act(() => view.update(React.createElement(AnnualGenerate, { year: 2026 })))
  act(() => view.root.findByType('button').props.onClick())
  assert.deepEqual(requests, [
    { start_date: '2025-01-01', end_date: '2025-12-31' },
    { start_date: '2026-01-01', end_date: '2026-10-14' },
  ])
  act(() => view.update(React.createElement(AnnualGenerate, { year: 2027 })))
  assert.equal(view.root.findByType('button').props.disabled, true)
  act(() => view.root.findByType('button').props.onClick())
  assert.equal(requests.length, 2)
})

test('annual range policy preserves full historical years and the current KST cutoff', () => {
  const { annualReportDateRange, reportToday } = sourceLoader()('application/services/reportPeriod')
  const today = reportToday(new Date('2026-12-31T15:00:00Z'))
  assert.deepEqual(annualReportDateRange(2026, today), { start: '2026-01-01', end: '2026-12-31' })
  assert.deepEqual(annualReportDateRange(2027, today), { start: '2027-01-01', end: '2027-01-01' })
  assert.deepEqual(annualReportDateRange(2024, '2026-10-21'), { start: '2024-01-01', end: '2024-12-31' })
  for (const year of [0, -1, 2026.5, 2027, NaN, Infinity]) {
    assert.equal(annualReportDateRange(year, '2026-10-21'), null)
  }
})
