// frontend/tests/cveInventory.test.mjs
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
import { finding, packagePage, snapshot } from './helpers/cveInventoryFixtures.mjs'

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
      if (dependency.startsWith('@/')) return load(dependency.slice(2))
      if (dependency.startsWith('.')) return load(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)).replaceAll('\\', '/'))
      return require(dependency)
    }, module, module.exports)
    return module.exports
  }
  return load
}

function query(overrides = {}) {
  return { data: snapshot(), isPending: false, isError: false, isFetching: false, refreshing: false, canRefresh: true, retryAfterSeconds: 0, refreshError: null, refresh() {}, refetch() {}, ...overrides }
}

function renderPage(t, state = query(), packageState = { data: packagePage(), isPending: false, isError: false, isFetching: false, refetch() {} }) {
  const priorWindow = globalThis.window
  globalThis.window = { setTimeout, clearTimeout }
  const requests = []
  const packageRequests = []
  const load = sourceLoader({ 'presentation/hooks/useCveInventory': {
    useCveInventory: (request) => { requests.push(request); return typeof state === 'function' ? state(request) : state },
    useCveInventoryPackages: (request, enabled) => { packageRequests.push({ request, enabled }); return packageState },
  } })
  const Page = load('presentation/pages/CveResponsePage').default
  let view
  act(() => { view = TestRenderer.create(React.createElement(Page)) })
  t.after(() => { act(() => view.unmount()); globalThis.window = priorWindow })
  return { view, requests, packageRequests }
}

function visibleText(view) { return JSON.stringify(view.toJSON()) }
function selectWith(view, value) { return view.root.findAllByType('select').find((select) => select.findAllByType('option').some((option) => option.props.value === value)) }
function deferred() { let resolve; const promise = new Promise((yes) => { resolve = yes }); return { promise, resolve } }
async function until(predicate) {
  const deadline = Date.now() + 3000
  while (!predicate()) { assert.ok(Date.now() < deadline, 'Timed out'); await act(async () => { await new Promise((resolve) => setTimeout(resolve, 15)) }) }
}

test('default requests include all package versions and dates, with distinct inventory impact', (t) => {
  const { view, requests } = renderPage(t)
  assert.deepEqual(requests[0], { severity: 'all', search: '', ecosystem: 'all', impact: 'all', page: 1, page_size: 50, sort: 'severity' })
  const text = visibleText(view)
  for (const expected of ['Orcle Linux 8.10 / eyeCloudXoar 4.03_R2 기준', 'CVE-2020-12345', '영향받지 않음', '미평가', '전체 등록 기간', '패키지·CVE 조합 기준', '패키지별 CVE']) assert.ok(text.includes(expected), expected)
  assert.equal(view.root.findAllByType('tbody')[0].findAllByProps({ scope: 'row' }).length, 3)
  assert.equal(view.root.findAllByType('article').length, 3)
  assert.equal(view.root.findAllByProps({ 'aria-label': '표시 언어 선택' }).length, 0)
})

test('severity, ecosystem, inventory impact and pagination are sent to the server', (t) => {
  const { view, requests } = renderPage(t, (request) => query({ data: snapshot({ page: request.page, total: 130 }) }))
  act(() => view.root.findByProps({ 'aria-label': 'CVE 목록 다음 페이지' }).props.onClick())
  assert.equal(requests.at(-1).page, 2)
  const buttons = view.root.findByProps({ 'aria-label': 'CVE 위험도 필터' }).findAllByType('button')
  act(() => buttons.at(-1).props.onClick())
  assert.equal(requests.at(-1).severity, 'unknown')
  assert.equal(requests.at(-1).page, 1)
  act(() => selectWith(view, 'PyPI').props.onChange({ target: { value: 'PyPI' } }))
  assert.equal(requests.at(-1).ecosystem, 'PyPI')
  act(() => selectWith(view, 'not_affected').props.onChange({ target: { value: 'not_affected' } }))
  assert.equal(requests.at(-1).impact, 'not_affected')
  act(() => view.root.findAllByType('button').find((button) => button.children.includes('필터 초기화')).props.onClick())
  assert.equal(requests.at(-1).impact, 'all')
  assert.equal(requests.at(-1).severity, 'all')
})

test('search is debounced and resets the page without introducing a date limit', async (t) => {
  const { view, requests } = renderPage(t, (request) => query({ data: snapshot({ page: request.page, total: 130 }) }))
  act(() => view.root.findByProps({ 'aria-label': 'CVE 목록 다음 페이지' }).props.onClick())
  act(() => view.root.findByProps({ type: 'search' }).props.onChange({ target: { value: '  kernel CVE  ' } }))
  assert.equal(requests.at(-1).search, '')
  await until(() => requests.at(-1).search === 'kernel CVE')
  assert.equal(requests.at(-1).page, 1)
  assert.equal('days' in requests.at(-1), false)
})

test('a smaller refreshed result set returns an out-of-range page to the last valid page', (t) => {
  let total = 130
  const { view, requests } = renderPage(t, (request) => query({ data: snapshot({ page: request.page, total }) }))
  total = 1
  act(() => view.root.findByProps({ 'aria-label': 'CVE 목록 다음 페이지' }).props.onClick())
  assert.equal(requests.at(-1).page, 1)
})

test('coverage distinguishes unmapped and failed packages from successful empty results', (t) => {
  const { view, packageRequests } = renderPage(t, query({ data: snapshot({ items: [], total: 0 }) }))
  assert.match(visibleText(view), /조회 대기·실패·매핑 필요 항목은 취약점 없음으로 판단하지 않습니다/)
  assert.equal(packageRequests.at(-1).enabled, false)
  act(() => view.root.findByProps({ 'aria-controls': 'cve-inventory-coverage' }).props.onClick())
  assert.equal(packageRequests.at(-1).enabled, true)
  assert.match(visibleText(view), /공식 패키지 식별자 확인 필요|조회 결과 미확정/)
  act(() => selectWith(view, 'unmapped').props.onChange({ target: { value: 'unmapped' } }))
  assert.equal(packageRequests.at(-1).request.status, 'unmapped')
  assert.doesNotMatch(visibleText(view), /안전합니다|취약점이 없습니다/)
})

test('range details preserve branch associations and only expose safe reference links', (t) => {
  const row = finding({ title: '<script>source</script>', references: ['javascript:alert(1)', 'https://user:password@example.com', 'https://example.com/fix', 'https://example.com/fix'] })
  const { view } = renderPage(t, query({ data: snapshot({ items: [row], total: 1 }) }))
  act(() => view.root.findAllByProps({ 'aria-label': `${row.package_name} ${row.cve_id} 상세 정보` })[0].props.onClick())
  assert.match(visibleText(view), /버전 범위별 수정 정보|최초 수집|3.0.0/)
  assert.ok(view.root.findAllByType('a').every((link) => !link.props.href.startsWith('javascript:') && !link.props.href.includes('password')))
  const Results = sourceLoader()('presentation/components/cve/CveInventoryResults').default
  const html = renderToStaticMarkup(React.createElement(Results, { rows: [finding({ package_name: '<script>package</script>' })] }))
  assert.match(html, /&lt;script&gt;package&lt;\/script&gt;/)
  assert.doesNotMatch(html, /<script>/)
})

test('API adapter forwards filters and cancellation independently from security news', async () => {
  const calls = []
  const load = sourceLoader({ 'infrastructure/api/client': { default: { get: async (...args) => { calls.push(['get', ...args]); return { data: {} } }, post: async (...args) => { calls.push(['post', ...args]); return { data: {} } } } } })
  const { cveInventoryApi } = load('infrastructure/api/cveInventoryApi')
  const request = sourceLoader()('application/services/cveInventory').defaultCveInventoryRequest()
  const signal = new AbortController().signal
  await cveInventoryApi.getSnapshot(request, signal)
  await cveInventoryApi.getPackages({ status: 'error', search: '', page: 1, page_size: 20 }, signal)
  await cveInventoryApi.refresh()
  assert.equal(calls[0][1], '/cve-inventory')
  assert.deepEqual(calls[0][2], { params: request, signal })
  assert.equal(calls[1][1], '/cve-inventory/packages')
  assert.deepEqual(calls[2], ['post', '/cve-inventory/refresh'])
})

function setupHook(t, gateway) {
  const priorWindow = globalThis.window
  globalThis.window = { setInterval, clearInterval }
  const load = sourceLoader()
  const { useCveInventory } = load('presentation/hooks/useCveInventory')
  const { useAuthStore } = load('presentation/state/authStore')
  const { ApplicationServicesProvider } = load('presentation/context/ApplicationServicesContext')
  const request = load('application/services/cveInventory').defaultCveInventoryRequest()
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } } })
  let observed, view
  function Probe() { observed = useCveInventory(request); return null }
  act(() => { view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { cveInventory: gateway } }, React.createElement(QueryClientProvider, { client }, React.createElement(Probe)))) })
  t.after(() => { act(() => view.unmount()); client.clear(); globalThis.window = priorWindow })
  return { client, auth: useAuthStore, get observed() { return observed } }
}

test('refresh hook suppresses duplicate requests', async (t) => {
  let calls = 0
  const pending = deferred()
  const hook = setupHook(t, { getSnapshot: async () => snapshot(), refresh: () => { calls++; return pending.promise } })
  await until(() => hook.observed.data)
  act(() => { hook.observed.refresh(); hook.observed.refresh() })
  await until(() => calls === 1)
  await act(async () => pending.resolve(snapshot({ refreshing: true, retry_after_seconds: 7200 })))
  assert.equal(calls, 1)
})

test('refresh hook honours the server cooldown', async (t) => {
  const cooldown = setupHook(t, { getSnapshot: async () => snapshot({ retry_after_seconds: 100 }), refresh: async () => { throw new Error('Must not refresh') } })
  await until(() => cooldown.observed.data)
  assert.equal(cooldown.observed.canRefresh, false)
  act(() => cooldown.observed.refresh())
  assert.equal(cooldown.observed.retryAfterSeconds, 100)
})

test('late refresh responses from an old login never update the new session cache', async (t) => {
  const pending = deferred()
  const hook = setupHook(t, { getSnapshot: async () => snapshot(), refresh: () => pending.promise })
  await until(() => hook.observed.data)
  act(() => hook.observed.refresh())
  await until(() => hook.observed.refreshing)
  act(() => hook.auth.getState().clearAuth())
  await until(() => hook.observed.data && !hook.observed.isFetching)
  await act(async () => pending.resolve(snapshot({ refreshing: true, retry_after_seconds: 7200 })))
  assert.equal(hook.observed.data.refreshing, false)
  assert.equal(hook.observed.data.retry_after_seconds, 0)
})
