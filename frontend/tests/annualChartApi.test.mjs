// frontend/tests/annualChartApi.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import axios from 'axios'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

function loadSource(relative, dependencies = {}) {
  const filename = path.join(root, relative)
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
    fileName: filename,
  }).outputText
  const module = { exports: {} }
  new Function('require', 'module', 'exports', compiled)((dependency) => {
    if (Object.hasOwn(dependencies, dependency)) return dependencies[dependency]
    if (dependency === 'react' || dependency === 'react/jsx-runtime') return require(dependency)
    assert.fail(`Unexpected dependency: ${dependency}`)
  }, module, module.exports)
  return module.exports
}

const { RequestError } = loadSource('src/application/errors/RequestError.ts')
const request = { chart: 'sla_initial', month: 1, sla_status: 'all' }
const defaultProps = { reportId: 7, request, title: '1월 최초응답 SLA', total: 3, onClose() {} }

function result(key = 'TAC-1', changes = {}) {
  return {
    issues: [{ key, summary: '조회한 이슈', type: '개선' }],
    snapshot_count: 3, current_count: 1, source_total: 1, source_total_exact: true,
    collection_limit: 500, truncated: false, queried_at: '2026-09-10T12:00:00+09:00',
    snapshot_at: '2026-09-09', source: 'current_jira', ...changes,
  }
}

function createApi(get) {
  return loadSource('src/infrastructure/api/reportApi.ts', {
    './client': { default: { get }, getAccessToken: () => null },
  }).reportApi
}

function createModal(getChartIssues) {
  return loadSource('src/presentation/components/annual/AnnualRemoteIssueDetailsModal.tsx', {
    '@tanstack/react-query': { useQuery },
    '@/application/errors/RequestError': { RequestError },
    '@/presentation/context/ApplicationServicesContext': { useApplicationServices: () => ({ reports: { getChartIssues } }) },
    '@/presentation/components/common/IssueModalShell': {
      default: ({ children, ...props }) => React.createElement('IssueModalShell', props, children),
    },
    './AnnualIssueDetailsModal': {
      default: ({ headerSlot, ...props }) => React.createElement('AnnualIssueDetailsModal', props, headerSlot),
    },
  }).default
}

function setup(t, getChartIssues, props = defaultProps, beforeRender) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  beforeRender?.(client)
  const Modal = createModal(getChartIssues)
  const element = (nextProps) => React.createElement(QueryClientProvider, { client }, React.createElement(Modal, nextProps))
  let view
  act(() => { view = TestRenderer.create(element(props)) })
  t.after(() => { act(() => view.unmount()); client.clear() })
  return { client, view, update: (nextProps) => act(() => view.update(element(nextProps))) }
}

function deferred() {
  let resolve
  let reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

async function until(predicate) {
  const deadline = Date.now() + 1000
  while (!predicate()) {
    assert.ok(Date.now() < deadline, 'Timed out waiting for the query state')
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 5)) })
  }
}

function textOf(node) {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  return node.children.map(textOf).join('')
}

test('chart API preserves empty active type and status filters, cancellation signal and long source-query timeout', async () => {
  const calls = []
  const response = result()
  const api = createApi(async (...args) => { calls.push(args); return { data: response } })
  const selection = { ...request, filter_types: true, selected_types: [], filter_statuses: true, selected_statuses: [] }
  const controller = new AbortController()
  assert.equal(await api.getChartIssues(7, selection, controller.signal), response)
  const [url, options] = calls[0]
  assert.equal(url, '/reports/7/chart-issues')
  assert.equal(options.params, selection)
  assert.equal(options.params.filter_types, true)
  assert.deepEqual(options.params.selected_types, [])
  assert.equal(options.params.filter_statuses, true)
  assert.deepEqual(options.params.selected_statuses, [])
  assert.deepEqual(options.paramsSerializer, { indexes: null })
  assert.equal(options.signal, controller.signal)
  assert.equal(options.timeout, 120_000)
  const params = new URL(axios.getUri({ url, ...options }), 'https://test.invalid').searchParams
  assert.equal(params.get('filter_types'), 'true')
  assert.deepEqual(params.getAll('selected_types'), [])
  assert.equal(params.get('filter_statuses'), 'true')
  assert.deepEqual(params.getAll('selected_statuses'), [])
  controller.abort()
  assert.equal(options.signal.aborted, true)
})

test('chart API serializes type and status filters as repeated unindexed parameters and propagates upstream errors', async () => {
  const calls = []
  const api = createApi(async (...args) => { calls.push(args); return { data: result() } })
  const selectedTypes = ['개선', '인시던트', '서비스 요청']
  const selectedStatuses = ['Closed', '처리 중']
  await api.getChartIssues(8, { chart: 'resolution_type', filter_types: true, selected_types: selectedTypes, filter_statuses: true, selected_statuses: selectedStatuses, semester: 'h1' })
  const [url, options] = calls[0]
  const params = new URL(axios.getUri({ url, ...options }), 'https://test.invalid').searchParams
  assert.deepEqual(params.getAll('selected_types'), selectedTypes)
  assert.equal(params.has('selected_types[]'), false)
  assert.equal(params.has('selected_types[0]'), false)
  assert.deepEqual(params.getAll('selected_statuses'), selectedStatuses)
  assert.equal(params.has('selected_statuses[]'), false)
  assert.equal(params.has('selected_statuses[0]'), false)
  assert.equal(params.get('semester'), 'h1')
  const error = new RequestError(502, 'Jira 이슈 상세를 불러오지 못했습니다.')
  const failing = createApi(async () => { throw error })
  await assert.rejects(failing.getChartIssues(7, request), (received) => received === error)
})

test('remote details show loading and a 502 alert without an empty issue list, then retry the same selection', async (t) => {
  const first = deferred()
  const second = deferred()
  const calls = []
  const { view } = setup(t, (...args) => {
    calls.push(args)
    return calls.length === 1 ? first.promise : second.promise
  })
  assert.equal(view.root.findAllByType('AnnualIssueDetailsModal').length, 0)
  assert.match(textOf(view.root.findByProps({ role: 'status' })), /조회하고 있습니다/)
  await act(async () => first.reject(new RequestError(502, 'Jira 이슈 상세를 불러오지 못했습니다.')))
  await until(() => view.root.findAllByProps({ role: 'alert' }).length === 1)
  assert.equal(view.root.findAllByType('AnnualIssueDetailsModal').length, 0)
  assert.equal(textOf(view.root.findByProps({ role: 'alert' })), 'Jira 이슈 상세를 불러오지 못했습니다.')
  assert.equal(calls.length, 1)
  act(() => view.root.findByType('button').props.onClick())
  assert.equal(calls.length, 2)
  assert.deepEqual(calls.map(([id, selection]) => [id, selection]), [[7, request], [7, request]])
  assert.ok(calls.every(([, , signal]) => signal instanceof AbortSignal))
  await act(async () => second.resolve(result('TAC-RETRY')))
  await until(() => view.root.findAllByType('AnnualIssueDetailsModal').length === 1)
  const details = view.root.findByType('AnnualIssueDetailsModal')
  assert.deepEqual(details.props.issues.map((issue) => issue.key), ['TAC-RETRY'])
  assert.equal(details.props.total, 3)
  assert.equal(view.root.findAllByProps({ role: 'alert' }).length, 0)
})

test('report, chart, month, SLA status, type and status filters and empty-selection state use separate query caches', (t) => {
  const variants = [
    { reportId: 7, request },
    { reportId: 8, request },
    { reportId: 7, request: { ...request, chart: 'sla_resolution' } },
    { reportId: 7, request: { ...request, month: 2 } },
    { reportId: 7, request: { ...request, sla_status: 'violated' } },
    { reportId: 7, request: { ...request, filter_types: true, selected_types: [] } },
    { reportId: 7, request: { ...request, filter_types: true, selected_types: ['개선'] } },
    { reportId: 7, request: { ...request, filter_statuses: true, selected_statuses: [] } },
    { reportId: 7, request: { ...request, filter_statuses: true, selected_statuses: ['Closed'] } },
    { reportId: 7, request: { chart: 'resolution_type', issue_type: '개선', semester: 'h1' } },
  ]
  const calls = []
  const { client, view, update } = setup(t, async (...args) => { calls.push(args); return result('UNEXPECTED') }, defaultProps, (cache) => {
    variants.forEach(({ reportId, request: selection }, index) => cache.setQueryData(['annual-chart-issues', reportId, selection], result(`CACHE-${index}`)))
  })
  variants.forEach((variant, index) => {
    update({ ...defaultProps, ...variant, request: structuredClone(variant.request) })
    assert.equal(view.root.findByType('AnnualIssueDetailsModal').props.issues[0].key, `CACHE-${index}`)
  })
  assert.equal(calls.length, 0)
  assert.equal(client.getQueryCache().getAll().length, variants.length)
})

test('changing a selection cannot show the previous list while the new source request is pending', async (t) => {
  const pending = deferred()
  const calls = []
  const { view, update } = setup(t, (...args) => { calls.push(args); return pending.promise }, defaultProps, (cache) => {
    cache.setQueryData(['annual-chart-issues', 7, request], result('OLD-MONTH'))
  })
  assert.equal(view.root.findByType('AnnualIssueDetailsModal').props.issues[0].key, 'OLD-MONTH')
  const selection = { ...request, month: 2 }
  update({ ...defaultProps, request: selection })
  assert.equal(view.root.findAllByType('AnnualIssueDetailsModal').length, 0)
  assert.match(textOf(view.root.findByProps({ role: 'status' })), /조회하고 있습니다/)
  assert.equal(calls[0][1], selection)
  await act(async () => pending.resolve(result('NEW-MONTH')))
  await until(() => view.root.findAllByType('AnnualIssueDetailsModal').length === 1)
  assert.equal(view.root.findByType('AnnualIssueDetailsModal').props.issues[0].key, 'NEW-MONTH')
})

test('closing the pending modal aborts the signal consumed by the source request', (t) => {
  let requestSignal
  let aborted = 0
  const Modal = createModal((_, __, signal) => {
    requestSignal = signal
    return new Promise((_, reject) => signal.addEventListener('abort', () => {
      aborted++
      reject(new Error('request cancelled'))
    }, { once: true }))
  })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  function Host() {
    const [open, setOpen] = React.useState(true)
    return open ? React.createElement(Modal, { ...defaultProps, onClose: () => setOpen(false) }) : null
  }
  let view
  act(() => { view = TestRenderer.create(React.createElement(QueryClientProvider, { client }, React.createElement(Host))) })
  t.after(() => { act(() => view.unmount()); client.clear() })
  assert.equal(requestSignal.aborted, false)
  act(() => view.root.findByType('IssueModalShell').props.onClose())
  assert.equal(view.root.findAllByType('IssueModalShell').length, 0)
  assert.equal(requestSignal.aborted, true)
  assert.equal(aborted, 1)
})
