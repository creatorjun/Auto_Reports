// frontend/tests/securityNews.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
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

const load = sourceLoader()
const { defaultSecurityNewsFilters, filterSecurityNews, safeSecurityNewsUrl, cveReferenceUrl } = load('application/services/securityNews')
const { RequestError } = load('application/errors/RequestError')
const now = Date.parse('2026-10-20T05:00:00Z')
const source = { id: 'nvd', name: 'NVD', homepage: 'https://nvd.nist.gov/', kind: 'cve', status: 'ok', count: 1, last_success_at: '2026-10-20T00:00:00Z', error: null }
function item(overrides = {}) {
  return { id: 'one', source_id: 'nvd', kind: 'cve', title: '취약점 보안 업데이트', summary: 'Linux 보안 패치', url: 'https://nvd.nist.gov/vuln/detail/CVE-2026-12345', published_at: '2026-10-19T00:00:00Z', updated_at: null, cve_ids: ['CVE-2026-12345'], severity: 'high', cvss_score: 8.1, cvss_version: '3.1', known_exploited: false, vendor: 'Vendor', product: 'Linux', due_date: null, ...overrides }
}
function snapshot(overrides = {}) {
  return { items: [item()], sources: [source], initialized: true, refreshing: false, refreshed_at: '2026-10-20T00:00:00Z', next_refresh_at: null, refresh_interval_seconds: 900, ...overrides }
}
function query(overrides = {}) {
  return { data: snapshot(), now, isError: false, isFetching: false, refreshing: false, canRefresh: true, retryAfterSeconds: 0, refreshError: null, refresh() {}, refetch() {}, ...overrides }
}
function renderPage(t, state) {
  const instance = sourceLoader({ 'presentation/hooks/useSecurityNews': { useSecurityNews: () => state }, 'application/errors/RequestError': { RequestError } })
  const Page = instance('presentation/pages/SecurityNewsPage').default
  let view
  act(() => { view = TestRenderer.create(React.createElement(Page)) })
  t.after(() => act(() => view.unmount()))
  return view
}
function plainText(view) { return JSON.stringify(view.toJSON()) }
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
async function until(predicate) {
  const deadline = Date.now() + 2000
  while (!predicate()) {
    assert.ok(Date.now() < deadline, 'Timed out waiting for state')
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 15)) })
  }
}
function setupHook(t, gateway) {
  const previousWindow = globalThis.window
  globalThis.window = { setInterval, clearInterval }
  const instance = sourceLoader()
  const { ApplicationServicesProvider } = instance('presentation/context/ApplicationServicesContext')
  const { useSecurityNews } = instance('presentation/hooks/useSecurityNews')
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } } })
  let observed, view
  function Probe() { observed = useSecurityNews(); return null }
  act(() => { view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { securityNews: gateway } }, React.createElement(QueryClientProvider, { client }, React.createElement(Probe)))) })
  t.after(() => { act(() => view.unmount()); client.clear(); globalThis.window = previousWindow })
  return { client, unmount: () => act(() => view.unmount()), get observed() { return observed } }
}

test('filters search normalized CVE, vendor and product with all terms and preserve source rows', () => {
  const original = [item(), item({ id: 'two', title: '다른 소식', summary: '', product: 'Windows', cve_ids: [] })]
  const copy = structuredClone(original)
  for (const search of ['ｃｖｅ－２０２６－１２３４５', '  linux VENDOR  ', '보안 패치']) {
    assert.deepEqual(filterSecurityNews(original, { ...defaultSecurityNewsFilters(), search }, now).map((row) => row.id), ['one'])
  }
  assert.deepEqual(filterSecurityNews(original, { ...defaultSecurityNewsFilters(), search: 'linux windows' }, now), [])
  assert.deepEqual(original, copy)
})

test('source, type, severity and exploitation filters combine rather than broaden the results', () => {
  const rows = [item(), item({ id: 'kev', source_id: 'cisa-kev', severity: 'unknown', cvss_score: null, known_exploited: true }), item({ id: 'news', kind: 'news' })]
  const filters = { ...defaultSecurityNewsFilters(), source: 'cisa-kev', severity: 'unknown', exploitedOnly: true, kind: 'cve' }
  assert.deepEqual(filterSecurityNews(rows, filters, now).map((row) => row.id), ['kev'])
  assert.deepEqual(filterSecurityNews(rows, { ...filters, severity: 'high' }, now), [])
})

test('date filters use publication or KEV addition date and exclude undated items only in finite windows', () => {
  const rows = [item(), item({ id: 'old', published_at: '2026-09-01', updated_at: '2026-10-20' }), item({ id: 'undated', published_at: null }), item({ id: 'fallback', published_at: null, updated_at: '2026-10-18' })]
  assert.deepEqual(filterSecurityNews(rows, { ...defaultSecurityNewsFilters(), days: 7 }, now).map((row) => row.id), ['one', 'fallback'])
  assert.equal(filterSecurityNews(rows, defaultSecurityNewsFilters(), now).length, 4)
})

test('sorting keeps unknown severity last and pagination order deterministic without mutation', () => {
  const rows = [item({ id: 'unknown', severity: 'unknown', cvss_score: null, published_at: '2026-10-20' }), item({ id: 'critical', severity: 'critical', cvss_score: 9.8, published_at: '2026-10-01' }), item({ id: 'high' })]
  assert.deepEqual(filterSecurityNews(rows, { ...defaultSecurityNewsFilters(), sort: 'severity' }, now).map((row) => row.id), ['critical', 'high', 'unknown'])
  assert.deepEqual(filterSecurityNews(rows, defaultSecurityNewsFilters(), now).map((row) => row.id), ['unknown', 'high', 'critical'])
})

test('external destinations only allow absolute HTTP(S) without credentials and strict CVE identifiers', () => {
  for (const value of ['javascript:alert(1)', 'data:text/html,x', '//host/path', '/relative', 'file:///etc/passwd', 'https://user:pass@example.com']) assert.equal(safeSecurityNewsUrl(value), null)
  assert.equal(safeSecurityNewsUrl('https://example.com/article'), 'https://example.com/article')
  assert.equal(cveReferenceUrl('CVE-2026-12345'), 'https://nvd.nist.gov/vuln/detail/CVE-2026-12345')
  assert.equal(cveReferenceUrl('CVE-2026-1234/<script>'), null)
})

test('external source text is escaped, dangerous links are omitted, and unknown CVSS is never rendered as zero', () => {
  const Card = load('presentation/components/security/SecurityNewsCard').default
  const html = renderToStaticMarkup(React.createElement(Card, { item: item({ title: '<script>alert(1)</script>', summary: '<img src=x onerror=alert(1)>', url: 'javascript:alert(1)', cve_ids: [], severity: 'unknown', cvss_score: null, cvss_version: null }), sourceName: 'NVD' }))
  assert.ok(html.includes('&lt;script&gt;'))
  assert.ok(html.includes('&lt;img'))
  assert.ok(html.includes('미평가'))
  assert.ok(html.includes('원문 링크 없음'))
  assert.doesNotMatch(html, /href=|<script>|<img |CVSS 0/)
  const valid = renderToStaticMarkup(React.createElement(Card, { item: item(), sourceName: 'NVD' }))
  assert.match(valid, /target="_blank" rel="noopener noreferrer"/)
})

test('KEV cards distinguish addition dates and federal due dates from vulnerability publication', () => {
  const Card = load('presentation/components/security/SecurityNewsCard').default
  const html = renderToStaticMarkup(React.createElement(Card, { item: item({ source_id: 'cisa-kev', known_exploited: true, due_date: '2026-10-30' }), sourceName: 'CISA KEV' }))
  assert.match(html, /KEV 등록/)
  assert.match(html, /미 연방기관 조치 기한/)
  assert.match(html, /실제 악용 확인/)
})

test('Korean page tabs, search, reset and pagination work on all filtered items', (t) => {
  const state = query({ data: snapshot({ items: Array.from({ length: 23 }, (_, index) => item({ id: String(index), kind: index === 22 ? 'news' : 'cve', title: `항목 ${index}` })) }) })
  const view = renderPage(t, state)
  assert.equal(view.root.findAllByType('article').length, 20)
  act(() => view.root.findByProps({ 'aria-label': '다음 페이지' }).props.onClick())
  assert.equal(view.root.findAllByType('article').length, 3)
  act(() => view.root.findByProps({ role: 'tab', id: 'security-tab-news' }).props.onClick())
  assert.equal(view.root.findAllByType('article').length, 1)
  assert.match(plainText(view), /항목 22/)
  act(() => view.root.findByProps({ type: 'search' }).props.onChange({ target: { value: '없는 검색어' } }))
  assert.match(plainText(view), /조건에 맞는 보안 정보가 없습니다/)
  act(() => view.root.findAllByType('button').find((button) => button.children.some((child) => child === '필터 초기화')).props.onClick())
  assert.equal(view.root.findAllByType('article').length, 20)
})

test('source failures disclose missing success instead of showing a false valid zero count', () => {
  const Sources = load('presentation/components/security/SecurityNewsSources').default
  const html = renderToStaticMarkup(React.createElement(Sources, { sources: [{ ...source, status: 'error', last_success_at: null, count: 0, error: '일시적인 연결 오류', warning: '최근 일부 자료만 제공' }], refreshing: false }))
  assert.match(html, /수집 실패/)
  assert.match(html, /수집에 성공한 기록이 없습니다/)
  assert.doesNotMatch(html, /보관 중 0개/)
  assert.match(html, /최근 일부 자료만 제공/)
})

test('page keeps saved cards visible when refresh or polling fails and disables duplicate refresh', (t) => {
  let refreshes = 0
  const state = query({ refreshError: new Error('offline'), isError: true, refreshing: true, canRefresh: false, refresh: () => { refreshes += 1 } })
  const view = renderPage(t, state)
  assert.equal(view.root.findAllByType('article').length, 1)
  assert.match(plainText(view), /기존 자료를 유지합니다/)
  const button = view.root.findAllByType('button').find((node) => node.props['aria-busy'] === true)
  assert.equal(button.props.disabled, true)
  assert.equal(refreshes, 0)
})

test('429 refresh rejection and initial failure have readable Korean recovery copy', (t) => {
  const view = renderPage(t, query({ data: undefined, isError: true, refreshError: new RequestError(429, 'rate limit') }))
  assert.match(plainText(view), /방금 업데이트를 요청했습니다/)
  assert.match(plainText(view), /다시 조회/)
  assert.doesNotMatch(plainText(view), /공개 보안 정보를 수집하고 있습니다/)
})

test('gateway uses authenticated application client and passes cancellation only to GET', async () => {
  const calls = []
  const instance = sourceLoader({ 'infrastructure/api/client': { default: { get: async (...args) => { calls.push(['get', ...args]); return { data: snapshot() } }, post: async (...args) => { calls.push(['post', ...args]); return { data: snapshot() } } } } })
  const { securityNewsApi } = instance('infrastructure/api/securityNewsApi')
  const signal = new AbortController().signal
  await securityNewsApi.getSnapshot(signal)
  await securityNewsApi.refresh()
  assert.deepEqual(calls, [['get', '/security-news', { signal }], ['post', '/security-news/refresh']])
})

test('hook performs single refresh under immediate repeated calls and retains cache after rejection', async (t) => {
  const pending = deferred()
  let refreshes = 0
  const state = setupHook(t, { getSnapshot: async () => snapshot(), refresh: () => { refreshes += 1; return pending.promise } })
  await until(() => state.observed.canRefresh)
  act(() => { state.observed.refresh(); state.observed.refresh() })
  await until(() => refreshes === 1)
  await act(async () => pending.reject(new Error('unavailable')))
  await until(() => state.observed.refreshError)
  assert.equal(state.observed.data.items[0].id, 'one')
  assert.equal(refreshes, 1)
})

test('hook enforces server retry eligibility', async (t) => {
  let refreshes = 0
  const state = setupHook(t, { getSnapshot: async () => snapshot({ next_refresh_at: new Date(Date.now() + 60000).toISOString() }), refresh: async () => { refreshes += 1; return snapshot() } })
  await until(() => state.observed.data)
  assert.equal(state.observed.canRefresh, false)
  act(() => state.observed.refresh())
  assert.equal(refreshes, 0)
})

test('hook cancels unfinished reads on unmount', async (t) => {
  const waiting = deferred()
  let signal
  const cancellation = setupHook(t, { getSnapshot: (value) => { signal = value; return waiting.promise }, refresh: async () => snapshot() })
  await until(() => signal)
  cancellation.unmount()
  assert.equal(signal.aborted, true)
})

test('successful refresh updates shared snapshot and polling follows collection state', async (t) => {
  const updated = snapshot({ refreshing: true, items: [item({ id: 'updated' })] })
  const state = setupHook(t, { getSnapshot: async () => snapshot(), refresh: async () => updated })
  await until(() => state.observed.canRefresh)
  const cached = state.client.getQueryCache().find({ queryKey: ['security-news'] })
  assert.equal(cached.options.refetchInterval(cached), 60000)
  act(() => state.observed.refresh())
  await until(() => state.observed.data.items[0].id === 'updated')
  assert.equal(cached.options.refetchInterval(cached), 2000)
  assert.equal(state.observed.canRefresh, false)
})

test('desktop and mobile expose accessible security news and route stays under protected layout', (t) => {
  const instance = sourceLoader({
    'presentation/state/authStore': { useAuthStore: () => ({ loginRequired: false }) },
    'presentation/hooks/useAuth': { useMe: () => ({ data: null }), useLogout: () => ({ mutate() {} }) },
    'presentation/components/layout/ThemeToggle': { default: () => null },
  })
  for (const component of ['Sidebar', 'MobileTabBar']) {
    const Component = instance(`presentation/components/layout/${component}`).default
    let view
    act(() => { view = TestRenderer.create(React.createElement(MemoryRouter, { initialEntries: ['/security-news'] }, React.createElement(Component, { collapsed: true, setCollapsed() {} }))) })
    t.after(() => act(() => view.unmount()))
    const link = view.root.findAllByType('a').find((entry) => entry.props.href === '/security-news')
    assert.equal(link.props['aria-label'], '보안 뉴스')
    assert.equal(link.props['aria-current'], 'page')
  }
  const router = fs.readFileSync(path.join(sourceRoot, 'app/router.tsx'), 'utf8')
  const route = router.indexOf("path: 'security-news'")
  assert.ok(route > router.indexOf('<ProtectedRoute>'))
  assert.ok(route > router.indexOf('children: ['))
  assert.match(router, /SecurityNewsPage\s*=\s*lazy/)
  assert.match(fs.readFileSync(path.join(sourceRoot, 'main.tsx'), 'utf8'), /securityNews: securityNewsApi/)
})
