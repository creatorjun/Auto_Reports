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
const { defaultSecurityNewsFilters, filterCveResponseRows, filterSecurityNews, safeSecurityNewsUrl, cveReferenceUrl, securityNewsDisplayText } = load('application/services/securityNews')
const { RequestError } = load('application/errors/RequestError')
const now = Date.parse('2026-10-20T05:00:00Z')
const source = { id: 'nvd', name: 'NVD', homepage: 'https://nvd.nist.gov/', kind: 'cve', status: 'ok', count: 1, last_success_at: '2026-10-20T00:00:00Z', error: null }
function item(overrides = {}) {
  return { id: 'one', source_id: 'nvd', kind: 'cve', title: '취약점 보안 업데이트', summary: 'Linux 보안 패치', url: 'https://nvd.nist.gov/vuln/detail/CVE-2026-12345', published_at: '2026-10-19T00:00:00Z', updated_at: null, cve_ids: ['CVE-2026-12345'], severity: 'high', cvss_score: 8.1, cvss_version: '3.1', known_exploited: false, vendor: 'Vendor', product: 'Linux', due_date: null, ...overrides }
}
function snapshot(overrides = {}) {
  return { items: [item()], sources: [source], initialized: true, refreshing: false, refreshed_at: '2026-10-20T00:00:00Z', next_refresh_at: null, retry_after_seconds: 0, refresh_interval_seconds: 900, ...overrides }
}
function translation(overrides = {}) {
  return { enabled: true, translating: false, translated_count: 1, pending_count: 0, message: null, ...overrides }
}
function query(overrides = {}) {
  return { data: snapshot(), now, isError: false, isFetching: false, refreshing: false, canRefresh: true, retryAfterSeconds: 0, refreshError: null, refresh() {}, refetch() {}, ...overrides }
}
function renderPage(t, state, pageName = 'SecurityNewsPage') {
  const instance = sourceLoader({ 'presentation/hooks/useSecurityNews': { useSecurityNews: () => state }, 'application/errors/RequestError': { RequestError } })
  const Page = instance(`presentation/pages/${pageName}`).default
  let view
  act(() => { view = TestRenderer.create(React.createElement(Page)) })
  t.after(() => act(() => view.unmount()))
  return view
}
function plainText(view) { return JSON.stringify(view.toJSON()) }
function summaryButtons(view) { return view.root.findByProps({ role: 'group', 'aria-label': '보안 정보 요약 필터' }).findAllByType('button') }
function summaryButton(view, label) { return summaryButtons(view).find((button) => button.findAllByType('span').some((span) => span.children.includes(label))) }
function selectedSummaries(view) { return summaryButtons(view).filter((button) => button.props['aria-pressed']).map((button) => button.findAllByType('span').find((span) => typeof span.children[0] === 'string').children.join('')) }
function cveTableRows(view) { return view.root.findAllByType('tbody').flatMap((body) => body.findAllByType('tr')) }
function visibleTitles(view) { return cveTableRows(view).map((row) => row.findByProps({ scope: 'row' }).findByType('a').children.join('')) }
function selectWithOption(view, value) { return view.root.findAllByType('select').find((select) => select.findAllByType('option').some((option) => option.props.value === value)) }
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

test('translated and original fields are both searched without changing the filter contract', () => {
  const rows = [item({ title: 'Remote access vulnerability', summary: 'Authentication bypass in network appliance', title_ko: '원격 접근 취약점', summary_ko: '네트워크 장비의 인증 우회' }), item({ id: 'other', title: 'Other report', summary: '', title_ko: null, summary_ko: null })]
  for (const search of ['원격 취약점', '인증 우회', 'remote AUTHENTICATION', '원격 bypass']) {
    assert.deepEqual(filterSecurityNews(rows, { ...defaultSecurityNewsFilters(), search }, now).map((row) => row.id), ['one'])
  }
  assert.deepEqual(filterSecurityNews(rows, { ...defaultSecurityNewsFilters(), search: '인증 우회', severity: 'critical' }, now), [])
})

test('Korean display uses only concise summaries and falls back to original titles without exposing old full translations', () => {
  const row = item({ title: 'Original title', summary: 'Original description', title_ko: null, summary_ko: '한국어 한 줄 요약' })
  const original = structuredClone(row)
  assert.deepEqual(securityNewsDisplayText(row, 'ko'), { text: '한국어 한 줄 요약', summarized: true, originalFallback: false })
  assert.deepEqual(securityNewsDisplayText(row, 'original'), { text: 'Original title', summarized: false, originalFallback: false })
  for (const changes of [{ summary_ko: null }, { title_ko: '이전 전체 번역 제목' }, { summary_ko: '가'.repeat(181) }, { summary_ko: '첫 줄\n둘째 줄' }]) {
    assert.deepEqual(securityNewsDisplayText({ ...row, ...changes }, 'ko'), { text: 'Original title', summarized: false, originalFallback: true })
  }
  assert.deepEqual(securityNewsDisplayText(item({ source_id: 'kisa', title: '보안 업데이트 권고', summary: '', title_ko: null, summary_ko: null }), 'ko'), { text: '보안 업데이트 권고', summarized: false, originalFallback: false })
  assert.deepEqual(row, original)
})

test('brief validation counts Unicode code points and rejects every backend line separator', () => {
  const row = item({ title: 'Original title', title_ko: null, summary_ko: `${'가'.repeat(179)}🔒` })
  assert.deepEqual(securityNewsDisplayText(row, 'ko'), { text: row.summary_ko, summarized: true, originalFallback: false })
  const invalid = [`${'가'.repeat(180)}🔒`, ...Array.from('\r\n\v\f\x85\u2028\u2029', (separator) => `첫 줄${separator}둘째 줄`)]
  for (const summary_ko of invalid) {
    assert.deepEqual(securityNewsDisplayText({ ...row, summary_ko }, 'ko'), { text: 'Original title', summarized: false, originalFallback: true })
  }
})

test('source, type, severity and exploitation filters combine rather than broaden the results', () => {
  const rows = [item(), item({ id: 'kev', source_id: 'cisa-kev', severity: 'unknown', cvss_score: null, known_exploited: true }), item({ id: 'news', kind: 'news' })]
  const filters = { ...defaultSecurityNewsFilters(), source: 'cisa-kev', severity: 'unknown', exploitedOnly: true, kind: 'cve' }
  assert.deepEqual(filterSecurityNews(rows, filters, now).map((row) => row.id), ['kev'])
  assert.deepEqual(filterSecurityNews(rows, { ...filters, severity: 'high' }, now), [])
})

test('summary filters include both high severities and both update kinds without changing individual filters', () => {
  const rows = [
    item({ id: 'critical', severity: 'critical' }),
    item({ id: 'high', known_exploited: true }),
    item({ id: 'medium', severity: 'medium' }),
    item({ id: 'advisory', kind: 'advisory', source_id: 'kisa', known_exploited: true }),
    item({ id: 'news', kind: 'news', severity: 'unknown', source_id: 'google' }),
  ]
  const ids = (changes) => filterSecurityNews(rows, { ...defaultSecurityNewsFilters(), ...changes }, now).map((row) => row.id)
  assert.deepEqual(ids({ severity: 'high-risk' }), ['advisory', 'critical', 'high'])
  assert.deepEqual(ids({ kind: 'updates' }), ['advisory', 'news'])
  assert.deepEqual(ids({ kind: 'updates', severity: 'high-risk', source: 'kisa', exploitedOnly: true, days: 7, search: 'linux' }), ['advisory'])
  assert.deepEqual(ids({ kind: 'updates', severity: 'high-risk', source: 'google' }), [])
  assert.deepEqual(ids({ kind: 'advisory' }), ['advisory'])
  assert.deepEqual(ids({ kind: 'news' }), ['news'])
  assert.deepEqual(ids({ severity: 'high' }), ['advisory', 'high'])
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
  const List = load('presentation/components/security/SecurityNewsList').default
  const html = renderToStaticMarkup(React.createElement(List, { items: [item({ title: '<script>alert(1)</script>', summary: '<img src=x onerror=alert(1)>', url: 'javascript:alert(1)', cve_ids: [], severity: 'unknown', cvss_score: null, cvss_version: null })], sources: new Map([['nvd', 'NVD']]) }))
  assert.ok(html.includes('&lt;script&gt;'))
  assert.ok(!html.includes('&lt;img'))
  assert.ok(html.includes('미평가'))
  assert.ok(html.includes('원문 링크 없음'))
  assert.doesNotMatch(html, /href=|<script>|<img |CVSS 0/)
  const valid = renderToStaticMarkup(React.createElement(List, { items: [item()], sources: new Map([['nvd', 'NVD']]) }))
  assert.match(valid, /target="_blank" rel="noopener noreferrer"/)
})

test('summary rows escape generated text and do not render full original or translated bodies', () => {
  const List = load('presentation/components/security/SecurityNewsList').default
  const render = (changes) => renderToStaticMarkup(React.createElement(List, { items: [item({ title: 'Original title', summary: 'Full original body', ...changes })], sources: new Map() }))
  const translated = render({ summary_ko: '<script>취약점을 해결하려면 최신 버전으로 업데이트해야 합니다.</script>', title_ko: null })
  assert.match(translated, /&lt;script&gt;취약점을 해결하려면/)
  assert.doesNotMatch(translated, /<script>|AI 번역|Full original body|Original title/)
  const pending = render({ title_ko: '이전 전체 번역 제목', summary_ko: '이전 전체 번역 본문' })
  assert.match(pending, /Original title/)
  assert.doesNotMatch(pending, /이전 전체 번역|Full original body|AI 번역/)
  const native = render({ source_id: 'kisa', title: '보안 업데이트 권고', summary: '' })
  assert.match(native, /보안 업데이트 권고/)
  assert.doesNotMatch(native, /원문 표시|AI 번역/)
})

test('news list renders eight columns, one line per issue and compact CVE references', (t) => {
  const rows = [item({ kind: 'advisory', title: 'Original advisory', summary_ko: '제품 취약점 해결을 위한 보안 업데이트가 공개됐습니다.', title_ko: null, known_exploited: true, cve_ids: ['CVE-2026-12345', 'CVE-2026-12346', 'invalid'] }), item({ id: 'native', kind: 'advisory', source_id: 'kisa', title: '한국어 보안 권고', summary: '길고 상세한 원문 내용' })]
  const view = renderPage(t, query({ data: snapshot({ items: rows }) }))
  assert.equal(view.root.findAllByType('article').length, 0)
  assert.equal(cveTableRows(view).length, 2)
  assert.deepEqual(view.root.findByType('thead').findAllByType('th').map((cell) => cell.children.join('')), ['유형', '한 줄 요약', '위험도', '관련 CVE', '실제 악용', '출처', '게시일', '원문'])
  assert.match(view.root.findByType('table').props.className, /whitespace-nowrap/)
  const region = view.root.findByProps({ role: 'region' })
  assert.equal(region.props.tabIndex, 0)
  assert.match(region.props.className, /overflow-x-auto/)
  for (const row of cveTableRows(view)) {
    assert.equal(row.findAllByType('td').length, 7)
    const text = row.findByProps({ scope: 'row' }).findByType('span')
    assert.match(text.props.className, /truncate/)
    assert.equal(text.props.title, text.findByType('a').children.join(''))
  }
  assert.ok(cveTableRows(view).some((row) => row.findAllByType('span').some((span) => span.children.join('') === '+1')))
  assert.doesNotMatch(plainText(view), /길고 상세한 원문 내용|invalid/)
})

test('summary widgets replace duplicate tabs with accessible buttons that select the matching rows', (t) => {
  const rows = [
    item({ id: 'critical', severity: 'critical' }),
    item({ id: 'high', known_exploited: true }),
    item({ id: 'medium', severity: 'medium' }),
    item({ id: 'advisory', kind: 'advisory', known_exploited: true }),
    item({ id: 'news', kind: 'news', severity: 'unknown' }),
  ].map((row) => ({ ...row, title: `항목 ${row.id}` }))
  const view = renderPage(t, query({ data: snapshot({ items: rows }) }))
  assert.equal(view.root.findAllByProps({ role: 'tablist' }).length, 0)
  assert.equal(view.root.findAllByProps({ role: 'tab' }).length, 0)
  assert.equal(view.root.findByType('h1').children.join(''), '보안 뉴스')
  assert.doesNotMatch(plainText(view), /공개 보안 정보를 한곳에서|마지막 수집 시도|위젯을 선택하면|같은 CVE가 여러 출처|게시일 기준 ·|원문 링크는 새 창|출처별 공개 자료의 일부/)
  const results = view.root.findByProps({ id: 'security-news-results' })
  assert.equal(results.props['aria-label'], '보안 정보 검색 결과')
  assert.equal(results.props['aria-labelledby'], undefined)
  assert.notEqual(results.props.role, 'tabpanel')
  assert.equal(summaryButtons(view).length, 4)
  for (const button of summaryButtons(view)) {
    assert.equal(button.props.type, 'button')
    assert.equal(button.props['aria-controls'], 'security-news-results')
    assert.equal(typeof button.props['aria-pressed'], 'boolean')
  }
  assert.deepEqual(selectedSummaries(view), ['수집된 항목'])
  for (const [label, ids] of [
    ['실제 악용 확인', ['advisory']],
    ['치명적 · 높은 위험도', ['advisory']],
    ['보안 권고', ['advisory']],
    ['수집된 항목', ['advisory', 'news']],
  ]) {
    act(() => summaryButton(view, label).props.onClick())
    assert.deepEqual(visibleTitles(view), ids.map((id) => `항목 ${id}`))
    assert.deepEqual(selectedSummaries(view), [label])
  }
})

test('summary selection clears stale filters, preserves sort and returns to the first page', (t) => {
  const rows = [
    ...Array.from({ length: 23 }, (_, index) => item({ id: `matching-${String(index).padStart(2, '0')}`, title: `대상 ${index}`, source_id: 'kisa', kind: 'advisory', known_exploited: true })),
    item({ id: 'old-critical', kind: 'advisory', title: '이전 치명적 취약점', severity: 'critical', published_at: '2026-09-01', known_exploited: false }),
    item({ id: 'medium', kind: 'advisory', title: '보통 취약점', severity: 'medium' }),
  ]
  const view = renderPage(t, query({ data: snapshot({ items: rows, sources: [source, { ...source, id: 'kisa', name: 'KISA', kind: 'advisory' }] }) }))
  act(() => {
    summaryButton(view, '보안 권고').props.onClick()
    view.root.findByProps({ type: 'search' }).props.onChange({ target: { value: '대상' } })
    selectWithOption(view, 'kisa').props.onChange({ target: { value: 'kisa' } })
    selectWithOption(view, 'high').props.onChange({ target: { value: 'high' } })
    selectWithOption(view, '7').props.onChange({ target: { value: '7' } })
    view.root.findByProps({ type: 'checkbox' }).props.onChange({ target: { checked: true } })
    selectWithOption(view, 'newest').props.onChange({ target: { value: 'severity' } })
  })
  act(() => view.root.findByProps({ 'aria-label': '다음 페이지' }).props.onClick())
  assert.deepEqual(visibleTitles(view), ['대상 20', '대상 21', '대상 22'])
  act(() => summaryButton(view, '치명적 · 높은 위험도').props.onClick())
  assert.equal(view.root.findByProps({ type: 'search' }).props.value, '')
  assert.equal(selectWithOption(view, 'kisa').props.value, '')
  assert.equal(selectWithOption(view, '7').props.value, 'all')
  assert.equal(view.root.findByProps({ type: 'checkbox' }).props.checked, false)
  assert.equal(selectWithOption(view, 'high').props.value, 'high-risk')
  assert.equal(selectWithOption(view, 'newest').props.value, 'severity')
  assert.equal(view.root.findByProps({ 'aria-label': '이전 페이지' }).props.disabled, true)
  assert.equal(visibleTitles(view).length, 20)
  assert.equal(visibleTitles(view)[0], '이전 치명적 취약점')
  assert.deepEqual(selectedSummaries(view), ['치명적 · 높은 위험도'])
  act(() => summaryButton(view, '수집된 항목').props.onClick())
  assert.equal(selectWithOption(view, 'high').props.value, 'all')
  assert.equal(selectWithOption(view, 'newest').props.value, 'severity')
  assert.equal(visibleTitles(view)[0], '이전 치명적 취약점')
  act(() => view.root.findByProps({ 'aria-label': '다음 페이지' }).props.onClick())
  assert.deepEqual(visibleTitles(view), ['대상 19', '대상 20', '대상 21', '대상 22', '보통 취약점'])
})

test('summary conditions combine with search, source, severity, period and exploitation and reset empty results', (t) => {
  const base = { kind: 'advisory', source_id: 'kisa', title: '대상 권고', known_exploited: true }
  const rows = [
    item({ ...base, id: 'advisory' }),
    item({ ...base, id: 'news', kind: 'news', title: '대상 뉴스' }),
    item({ ...base, id: 'wrong-kind', kind: 'cve', title: '대상 취약점' }),
    item({ ...base, id: 'wrong-source', source_id: 'nvd', title: '대상 다른 출처' }),
    item({ ...base, id: 'wrong-severity', severity: 'medium', title: '대상 보통 위험도' }),
    item({ ...base, id: 'not-exploited', known_exploited: false, title: '대상 악용 미확인' }),
    item({ ...base, id: 'old', published_at: '2026-09-01', title: '대상 이전 권고' }),
    item({ ...base, id: 'wrong-search', title: '다른 검색 항목' }),
  ]
  const view = renderPage(t, query({ data: snapshot({ items: rows, sources: [source, { ...source, id: 'kisa', name: 'KISA', kind: 'advisory' }] }) }))
  act(() => {
    summaryButton(view, '보안 권고').props.onClick()
    view.root.findByProps({ type: 'search' }).props.onChange({ target: { value: '대상' } })
    selectWithOption(view, 'kisa').props.onChange({ target: { value: 'kisa' } })
    selectWithOption(view, 'high-risk').props.onChange({ target: { value: 'high-risk' } })
    selectWithOption(view, '7').props.onChange({ target: { value: '7' } })
    view.root.findByProps({ type: 'checkbox' }).props.onChange({ target: { checked: true } })
  })
  assert.deepEqual(visibleTitles(view), ['대상 권고'])
  assert.deepEqual(selectedSummaries(view), ['보안 권고'])
  act(() => selectWithOption(view, 'high-risk').props.onChange({ target: { value: 'medium' } }))
  assert.deepEqual(visibleTitles(view), ['대상 보통 위험도'])
  assert.deepEqual(selectedSummaries(view), ['보안 권고'])
  act(() => view.root.findByProps({ type: 'search' }).props.onChange({ target: { value: '없는 검색어' } }))
  assert.equal(view.root.findAllByType('article').length, 0)
  assert.match(plainText(view), /조건에 맞는 보안 정보가 없습니다/)
  act(() => view.root.findAllByType('button').find((button) => button.children.includes('필터 초기화')).props.onClick())
  assert.equal(cveTableRows(view).length, rows.filter((row) => row.kind !== 'cve').length)
  assert.deepEqual(selectedSummaries(view), ['수집된 항목'])
})

test('summary toggle changes only row presentation and preserves search results without requesting AI work', (t) => {
  let refreshes = 0
  let reads = 0
  const state = query({
    data: snapshot({ items: [item({ kind: 'news', title: 'Original security update', summary: 'Original summary', title_ko: null, summary_ko: '한국어 보안 업데이트 요약' })], translation: translation() }),
    refresh: () => { refreshes += 1 },
    refetch: () => { reads += 1 },
  })
  const view = renderPage(t, state)
  const languageGroup = view.root.findByProps({ role: 'group', 'aria-label': '표시 언어 선택' })
  const korean = languageGroup.findAllByType('button').find((button) => button.children.includes('한 줄 요약'))
  const original = languageGroup.findAllByType('button').find((button) => button.children.includes('원문 제목'))
  assert.equal(korean.props['aria-pressed'], true)
  assert.deepEqual(visibleTitles(view), ['한국어 보안 업데이트 요약'])
  act(() => view.root.findByProps({ type: 'search' }).props.onChange({ target: { value: '한국어' } }))
  act(() => original.props.onClick())
  assert.equal(original.props['aria-pressed'], true)
  assert.equal(cveTableRows(view).length, 1)
  assert.deepEqual(visibleTitles(view), ['Original security update'])
  assert.ok(view.root.findByType('thead').findAllByType('th').some((cell) => cell.children.includes('원문 제목')))
  act(() => korean.props.onClick())
  assert.deepEqual(visibleTitles(view), ['한국어 보안 업데이트 요약'])
  assert.equal(refreshes, 0)
  assert.equal(reads, 0)
})

test('translation controls keep concise active status and escaped error details without repeated guides', () => {
  const Controls = load('presentation/components/security/SecurityNewsTranslationControls').default
  const render = (state) => renderToStaticMarkup(React.createElement(Controls, { language: 'ko', onLanguageChange() {}, translation: state }))
  const active = render(translation({ translating: true, translated_count: 3, pending_count: 22 }))
  assert.match(active, /AI 요약 중 · 22건/)
  assert.doesNotMatch(active, /번역 완료|준비되는 대로|원문으로 표시/)
  const paused = render(translation({ enabled: false, translated_count: 7, pending_count: 18, message: '<제공 서비스 일시 중단>' }))
  assert.match(paused, /AI 요약 일시 대기 · 18건/)
  assert.match(paused, /title="&lt;제공 서비스 일시 중단&gt;"/)
  for (const normal of [render(translation()), render(undefined)]) {
    assert.match(normal, /표시 언어/)
    assert.doesNotMatch(normal, /번역 완료|원문으로 표시|role="status"/)
  }
})

test('source failures disclose missing success instead of showing a false valid zero count', () => {
  const Sources = load('presentation/components/security/SecurityNewsSources').default
  const html = renderToStaticMarkup(React.createElement(Sources, { sources: [{ ...source, status: 'error', last_success_at: null, count: 0, error: '일시적인 연결 오류', warning: '최근 일부 자료만 제공' }], refreshing: false }))
  assert.match(html, /수집 실패/)
  assert.match(html, /수집 기록 없음/)
  assert.doesNotMatch(html, /0개 ·/)
  assert.match(html, /일시적인 연결 오류/)
  assert.match(html, /최근 일부 자료만 제공/)
})

test('page keeps saved rows visible when refresh or polling fails and disables duplicate refresh', (t) => {
  let refreshes = 0
  const state = query({ data: snapshot({ items: [item({ kind: 'advisory' })] }), refreshError: new Error('offline'), isError: true, refreshing: true, canRefresh: false, refresh: () => { refreshes += 1 } })
  const view = renderPage(t, state)
  assert.equal(cveTableRows(view).length, 1)
  assert.match(plainText(view), /업데이트 실패 · 기존 자료 표시/)
  const button = view.root.findAllByType('button').find((node) => node.props['aria-busy'] === true)
  assert.equal(button.props.disabled, true)
  assert.equal(refreshes, 0)
})

test('429 refresh rejection and initial failure have readable Korean recovery copy', (t) => {
  const view = renderPage(t, query({ data: undefined, isError: true, refreshError: new RequestError(429, 'rate limit') }))
  assert.match(plainText(view), /업데이트 요청 대기/)
  assert.match(plainText(view), /다시 조회/)
  assert.doesNotMatch(plainText(view), /보안 뉴스 로딩 중/)
})

test('first scheduled collection can remain empty without an endless loader and manual refresh stays available', (t) => {
  let refreshes = 0
  const empty = snapshot({ items: [], initialized: false, sources: [{ ...source, status: 'pending', count: 0, last_success_at: null }] })
  const view = renderPage(t, query({ data: empty, refresh: () => { refreshes += 1 } }))
  assert.match(plainText(view), /아직 수집된 보안 정보가 없습니다/)
  assert.doesNotMatch(plainText(view), /보안 뉴스 로딩 중/)
  assert.equal(view.root.findByProps({ id: 'security-news-results' }).props['aria-busy'], false)
  const refresh = view.root.findByType('header').findByType('button')
  assert.equal(refresh.props.disabled, false)
  assert.equal(refreshes, 0)
  act(() => refresh.props.onClick())
  assert.equal(refreshes, 1)

  for (const state of [query({ data: undefined, isFetching: true, canRefresh: false }), query({ data: { ...empty, refreshing: true }, refreshing: true, canRefresh: false })]) {
    const loading = renderPage(t, state)
    assert.match(plainText(loading), /보안 뉴스 로딩 중/)
    assert.equal(loading.root.findByProps({ id: 'security-news-results' }).props['aria-busy'], true)
  }
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
  const state = setupHook(t, { getSnapshot: async () => snapshot({ next_refresh_at: new Date(Date.now() + 60000).toISOString(), retry_after_seconds: 60 }), refresh: async () => { refreshes += 1; return snapshot() } })
  await until(() => state.observed.data)
  assert.equal(state.observed.canRefresh, false)
  act(() => state.observed.refresh())
  assert.equal(refreshes, 0)
})

test('opening and repeated snapshot reads never collect news and the next daily schedule does not block manual refresh', async (t) => {
  let reads = 0
  let refreshes = 0
  const empty = snapshot({ items: [], initialized: false, next_refresh_at: new Date(Date.now() + 86400000).toISOString(), refresh_interval_seconds: 86400, retry_after_seconds: 0 })
  const state = setupHook(t, {
    getSnapshot: async () => { reads += 1; return empty },
    refresh: async () => { refreshes += 1; return snapshot({ refreshing: true }) },
  })
  await until(() => state.observed.canRefresh)
  assert.equal(reads, 1)
  assert.equal(refreshes, 0)
  for (let count = 0; count < 3; count += 1) {
    await act(async () => { await state.observed.refetch() })
  }
  assert.equal(reads, 4)
  assert.equal(refreshes, 0)
  await until(() => state.observed.canRefresh)
  act(() => state.observed.refresh())
  await until(() => refreshes === 1 && state.observed.refreshing)
})

for (const clockOffset of [-180000, 180000]) {
  test(`relative retry eligibility stays correct when client clock is ${clockOffset < 0 ? 'behind' : 'ahead of'} server`, { timeout: 3000 }, async (t) => {
    const serverNow = Date.now()
    t.mock.method(Date, 'now', () => serverNow + clockOffset)
    const state = setupHook(t, {
      getSnapshot: async () => snapshot({ next_refresh_at: new Date(serverNow + 60000).toISOString(), retry_after_seconds: 60 }),
      refresh: async () => snapshot(),
    })
    await until(() => state.observed.data)
    assert.equal(state.observed.retryAfterSeconds, 60)
    assert.equal(state.observed.canRefresh, false)
    act(() => state.client.setQueryData(['security-news'], snapshot({ next_refresh_at: new Date(serverNow + 60000).toISOString(), retry_after_seconds: 0 })))
    await until(() => state.observed.canRefresh)
    assert.equal(state.observed.retryAfterSeconds, 0)
  })
}

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

test('translation polling is faster while work remains but does not disable source refresh', async (t) => {
  const translating = snapshot({ translation: translation({ translating: true, pending_count: 10 }) })
  const state = setupHook(t, { getSnapshot: async () => translating, refresh: async () => translating })
  await until(() => state.observed.canRefresh)
  const cached = state.client.getQueryCache().find({ queryKey: ['security-news'] })
  assert.equal(cached.options.refetchInterval(cached), 5000)
  assert.equal(state.observed.refreshing, false)
  assert.equal(state.observed.canRefresh, true)
  act(() => state.client.setQueryData(['security-news'], { ...translating, refreshing: true }))
  await until(() => state.observed.refreshing)
  assert.equal(cached.options.refetchInterval(cached), 2000)
  act(() => state.client.setQueryData(['security-news'], snapshot({ translation: translation() })))
  await until(() => state.observed.canRefresh)
  assert.equal(cached.options.refetchInterval(cached), 60000)
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
    const links = view.root.findAllByType('a')
    const cveIndex = links.findIndex((entry) => entry.props.href === '/cve-response')
    assert.ok(cveIndex >= 0)
    assert.equal(links[cveIndex].props['aria-label'], 'CVE 취약점 대응')
    assert.equal(links[cveIndex + 1].props.href, '/security-news')
  }
  const router = fs.readFileSync(path.join(sourceRoot, 'app/router.tsx'), 'utf8')
  const route = router.indexOf("path: 'security-news'")
  assert.ok(route > router.indexOf('<ProtectedRoute>'))
  assert.ok(route > router.indexOf('children: ['))
  assert.match(router, /SecurityNewsPage\s*=\s*lazy/)
  assert.ok(router.indexOf("path: 'cve-response'") > router.indexOf('children: ['))
  assert.match(router, /CveResponsePage\s*=\s*lazy/)
  assert.match(fs.readFileSync(path.join(sourceRoot, 'main.tsx'), 'utf8'), /securityNews: securityNewsApi/)
})

test('CVE page includes NVD and CISA KEV with version pairs and excludes news translations', (t) => {
  const rows = [
    item({ id: 'nvd', summary: 'Long original vulnerability description', title_ko: '기존 번역 제목', summary_ko: '기존 번역 설명', remediations: [{ vendor: 'Example', product: 'Library', affected_versions: '1.0 이상, 1.4 미만', fixed_version: '1.4', reference_url: 'https://example.com/fix' }] }),
    item({ id: 'kev', source_id: 'cisa-kev', known_exploited: true, product: 'Gateway', cve_ids: ['CVE-2026-23456'], remediations: [] }),
    item({ id: 'advisory', kind: 'advisory', title: '보안 권고 제목', source_id: 'kisa' }),
    item({ id: 'news', kind: 'news', title: '보안 뉴스 제목', source_id: 'google' }),
  ]
  const sources = [source, { ...source, id: 'cisa-kev', name: 'CISA KEV' }, { ...source, id: 'kisa', name: 'KISA', kind: 'advisory' }]
  const view = renderPage(t, query({ data: snapshot({ items: rows, sources, translation: translation({ translating: true, pending_count: 10 }) }) }), 'CveResponsePage')
  assert.equal(view.root.findByType('h1').children.join(''), 'CVE 취약점 대응')
  assert.equal(cveTableRows(view).length, 2)
  assert.equal(summaryButtons(view).length, 3)
  assert.equal(view.root.findAllByProps({ 'aria-label': '표시 언어 선택' }).length, 0)
  for (const expected of ['Library', 'Gateway', '1.4', '해결 버전 미확인', '실제 악용 확인', 'CISA KEV', 'NVD']) assert.ok(plainText(view).includes(expected))
  assert.doesNotMatch(plainText(view), /Long original vulnerability description|기존 번역|보안 권고 제목|보안 뉴스 제목|번역 중/)
  assert.equal(selectWithOption(view, 'nvd').findAllByType('option').some((option) => option.props.value === 'kisa'), false)
  act(() => selectWithOption(view, 'cisa-kev').props.onChange({ target: { value: 'cisa-kev' } }))
  assert.equal(cveTableRows(view).length, 1)
  assert.match(plainText(view), /Gateway/)
  act(() => summaryButton(view, '수집된 항목').props.onClick())
  assert.equal(cveTableRows(view).length, 2)
  act(() => view.root.findByProps({ type: 'search' }).props.onChange({ target: { value: 'Library 1.4' } }))
  assert.equal(cveTableRows(view).length, 1)
  assert.doesNotMatch(plainText(view), /Gateway/)
})

test('CVE pagination and filters never pull ordinary news into the response list', (t) => {
  const rows = Array.from({ length: 23 }, (_, index) => item({ id: `cve-${index.toString().padStart(2, '0')}`, cve_ids: [`CVE-2026-${10000 + index}`], known_exploited: index % 2 === 0 }))
  const view = renderPage(t, query({ data: snapshot({ items: [...rows, item({ id: 'news', kind: 'news' })] }) }), 'CveResponsePage')
  assert.equal(cveTableRows(view).length, 20)
  act(() => view.root.findByProps({ 'aria-label': '다음 페이지' }).props.onClick())
  assert.equal(cveTableRows(view).length, 3)
  act(() => summaryButton(view, '실제 악용 확인').props.onClick())
  assert.equal(cveTableRows(view).length, 12)
  assert.equal(view.root.findAllByProps({ 'aria-label': '다음 페이지' }).length, 0)
})

test('removed Google Security entries and source never return from an older cached snapshot', (t) => {
  const google = { ...source, id: 'google-security', name: 'Google Security', kind: 'news' }
  const data = snapshot({ items: [item({ id: 'google', source_id: google.id, kind: 'news', title: 'Removed Google headline' }), item({ id: 'cisco', source_id: 'cisco', kind: 'advisory', title: 'Cisco 보안 권고' })], sources: [google, { ...source, id: 'cisco', name: 'Cisco', kind: 'advisory' }] })
  const view = renderPage(t, query({ data }))
  assert.deepEqual(visibleTitles(view), ['Cisco 보안 권고'])
  assert.doesNotMatch(plainText(view), /Google Security|Removed Google headline|google-security/)
  assert.equal(view.root.findByProps({ id: 'security-news-results' }).findByProps({ role: 'status' }).findByType('strong').children.join(''), '1')
  act(() => summaryButton(view, '수집된 항목').props.onClick())
  assert.deepEqual(visibleTitles(view), ['Cisco 보안 권고'])
})

test('CVE remediation pairs escape source content and distinguish missing fixes from affected bounds', () => {
  const List = load('presentation/components/security/CveRemediationList').default
  const html = renderToStaticMarkup(React.createElement(List, { rows: filterCveResponseRows([item({ url: 'javascript:bad()', cve_ids: [], remediations: [{ vendor: null, product: '<script>library</script>', affected_versions: '< 9.0', fixed_version: null, reference_url: 'javascript:bad()' }, { vendor: null, product: 'Second library', affected_versions: '2.0', fixed_version: '2.1', reference_url: 'https://example.com/fix' }] })], defaultSecurityNewsFilters(), now), sources: new Map() }))
  assert.match(html, /&lt;script&gt;library&lt;\/script&gt;/)
  assert.match(html, /해결 버전 미확인/)
  assert.match(html, /Second library/)
  assert.match(html, /href="https:\/\/example.com\/fix"/)
  assert.doesNotMatch(html, /<script>|javascript:|AI 번역|Linux 보안 패치/)
})

test('CVE table distinguishes verified vendor fixes, scoped NVD bounds and description evidence', () => {
  const List = load('presentation/components/security/CveRemediationList').default
  const remediations = [
    { vendor: null, product: 'Vendor library', affected_versions: '< 9.0.117', fixed_version: '9.0.117', fixed_version_basis: 'vendor', fixed_version_branch: '9.0', reference_url: 'https://vendor.example/security' },
    { vendor: null, product: 'Range library', affected_versions: '< 1.6.20', fixed_version: '1.6.20', fixed_version_basis: 'nvd_range', fixed_version_branch: '1.6', reference_url: 'https://nvd.nist.gov/vuln/detail/CVE-2026-12345' },
    { vendor: null, product: 'Description library', affected_versions: '2.0', fixed_version: '2.1', fixed_version_basis: 'description', fixed_version_branch: null, reference_url: 'https://source.example/advisory' },
  ]
  const html = renderToStaticMarkup(React.createElement(List, { rows: filterCveResponseRows([item({ remediations })], defaultSecurityNewsFilters(), now), sources: new Map() }))
  assert.equal((html.match(/scope="col"/g) ?? []).length, 10)
  assert.equal((html.match(/scope="row"/g) ?? []).length, 3)
  assert.match(html, /판단 근거/)
  assert.match(html, /1\.6\.20 이상 \(1\.6 계열\)/)
  assert.match(html, /제조사 확인/)
  assert.match(html, /NVD 영향 범위/)
  assert.match(html, /출처 수정 명시/)
  assert.match(html, /같은 제품과 주·부 버전 계열의 다른 NVD 영향 범위/)
  assert.match(html, /공급사 백포트/)
  for (const url of ['https://vendor.example/security', 'https://nvd.nist.gov/vuln/detail/CVE-2026-12345', 'https://source.example/advisory']) assert.ok(html.includes(`href="${url}"`))
  assert.doesNotMatch(html, /9\.0\.117 이상|2\.1 이상/)
})

test('CVE evidence links use safe references or source fallback while legacy fixes remain unverified', () => {
  const List = load('presentation/components/security/CveRemediationList').default
  const remediations = [
    { vendor: null, product: 'Legacy library', affected_versions: '1.0', fixed_version: '1.1', reference_url: 'javascript:alert(1)' },
    { vendor: null, product: 'Unknown library', affected_versions: '< 2.0', fixed_version: null, fixed_version_basis: null, reference_url: null },
  ]
  const safeHtml = renderToStaticMarkup(React.createElement(List, { rows: filterCveResponseRows([item({ remediations })], defaultSecurityNewsFilters(), now), sources: new Map() }))
  assert.match(safeHtml, /근거 확인 필요 근거 확인/)
  assert.match(safeHtml, /href="https:\/\/nvd.nist.gov\/vuln\/detail\/CVE-2026-12345"/)
  assert.match(safeHtml, />미확인<\/span>/)
  assert.doesNotMatch(safeHtml, /javascript:|제조사 확인|NVD 영향 범위/)
  const unsafeHtml = renderToStaticMarkup(React.createElement(List, { rows: filterCveResponseRows([item({ url: 'data:text/html,bad', cve_ids: [], remediations })], defaultSecurityNewsFilters(), now), sources: new Map() }))
  assert.doesNotMatch(unsafeHtml, /href=|javascript:|data:text/)
  assert.match(unsafeHtml, />근거 확인 필요<\/span>/)
})

test('CVE range fixes without a valid branch never claim all higher versions are fixed', () => {
  const List = load('presentation/components/security/CveRemediationList').default
  const remediations = [undefined, null, '1', '1.7', '<script>1.6</script>'].map((branch, index) => ({ vendor: null, product: `Library ${index}`, affected_versions: '< 1.6.20', fixed_version: '1.6.20', fixed_version_basis: 'nvd_range', fixed_version_branch: branch, reference_url: null }))
  const html = renderToStaticMarkup(React.createElement(List, { rows: filterCveResponseRows([item({ remediations })], defaultSecurityNewsFilters(), now), sources: new Map() }))
  assert.match(html, /1\.6\.20 \(계열 확인 필요\)/)
  assert.doesNotMatch(html, /1\.6\.20 이상|<script>/)
})


test('CVE table searches full original description without displaying the prose', (t) => {
  const fullText = 'Details '.repeat(250) + 'EncryptInterceptor bypass marker'
  const view = renderPage(t, query({ data: snapshot({ items: [item({ id: 'target', original_description: fullText }), item({ id: 'other', cve_ids: ['CVE-2026-55555'] })] }) }), 'CveResponsePage')
  assert.equal(view.root.findAllByType('article').length, 0)
  assert.equal(view.root.findByType('thead').findAllByType('th').length, 10)
  assert.doesNotMatch(plainText(view), /EncryptInterceptor bypass marker/)
  act(() => view.root.findByProps({ type: 'search' }).props.onChange({ target: { value: 'EncryptInterceptor bypass marker' } }))
  assert.equal(cveTableRows(view).length, 1)
  assert.equal(cveTableRows(view)[0].findByProps({ scope: 'row' }).findByType('a').children.join(''), 'CVE-2026-12345')
})

test('CVE table paginates version rows and hides only unknown product rows', (t) => {
  const remediations = Array.from({ length: 23 }, (_, index) => ({ vendor: null, product: index < 3 ? '제품 확인 필요' : 'Tomcat', affected_versions: `9.0.${index}`, fixed_version: '9.0.117', reference_url: null }))
  const view = renderPage(t, query({ data: snapshot({ items: [item({ remediations })] }) }), 'CveResponsePage')
  assert.equal(cveTableRows(view).length, 20)
  act(() => view.root.findByProps({ 'aria-label': '다음 페이지' }).props.onClick())
  assert.equal(cveTableRows(view).length, 3)
  const toggle = view.root.findAllByType('label').find((label) => label.children.includes('제품 확인 필요 숨기기')).findByType('input')
  act(() => toggle.props.onChange({ target: { checked: true } }))
  assert.equal(cveTableRows(view).length, 20)
  assert.equal(view.root.findAllByProps({ 'aria-label': '다음 페이지' }).length, 0)
  assert.ok(cveTableRows(view).every((row) => !row.findAllByType('span').some((span) => span.props.title === '제품 확인 필요')))
  act(() => view.root.findAllByType('button').find((button) => button.children.includes('필터 초기화')).props.onClick())
  assert.equal(cveTableRows(view).length, 20)
  assert.equal(view.root.findAllByProps({ 'aria-label': '다음 페이지' }).length, 1)
})

test('CVE column sorting synchronizes with sort control and uses numeric versions', (t) => {
  const remediations = ['9.0.10', '9.0.9', '9.0.117'].map((version) => ({ vendor: 'Apache', product: 'Tomcat', affected_versions: version, fixed_version: null, reference_url: null }))
  const view = renderPage(t, query({ data: snapshot({ items: [item({ remediations })] }) }), 'CveResponsePage')
  const versions = () => cveTableRows(view).map((row) => row.findAllByType('td')[2].findByType('span').children.join(''))
  act(() => view.root.findByProps({ 'aria-label': '영향 버전 오름차순 정렬' }).props.onClick())
  assert.deepEqual(versions(), ['9.0.9', '9.0.10', '9.0.117'])
  assert.equal(selectWithOption(view, 'affected-version').props.value, 'affected-version')
  assert.equal(view.root.findByType('thead').findAllByType('th')[3].props['aria-sort'], 'ascending')
  act(() => view.root.findByProps({ 'aria-label': '영향 버전 내림차순 정렬' }).props.onClick())
  assert.deepEqual(versions(), ['9.0.117', '9.0.10', '9.0.9'])
  assert.equal(selectWithOption(view, 'affected-version-desc').props.value, 'affected-version-desc')
})
