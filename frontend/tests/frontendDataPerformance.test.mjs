// frontend/tests/frontendDataPerformance.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')
const modules = new Map()

function loadSource(relative) {
  const filename = path.resolve(sourceRoot, `${relative.replace(/\.ts$/, '')}.ts`)
  if (modules.has(filename)) return modules.get(filename).exports
  const module = { exports: {} }
  modules.set(filename, module)
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }, fileName: filename,
  }).outputText
  new Function('require', 'module', 'exports', compiled)((dependency) => {
    if (dependency.startsWith('@/')) return loadSource(dependency.slice(2))
    if (dependency.startsWith('.')) return loadSource(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)))
    return require(dependency)
  }, module, module.exports)
  return module.exports
}

const { defaultSecurityNewsFilters, filterSecurityNews } = loadSource('application/services/securityNews')
const { defaultSlaStatusFilters, filterSlaStatusTickets } = loadSource('application/services/slaStatus')
const { sortSlaViolationTickets } = loadSource('domain/SlaViolationSort')
const { sortPartnerOrganizationsByIssueCount } = loadSource('domain/Partner')
const { filterRedeployments } = loadSource('application/services/redeploymentReport')

function news(id, published_at, overrides = {}) {
  return { id, published_at, updated_at: null, kind: 'news', source_id: 'source', severity: 'high', cvss_score: 8,
    title: 'Security update', summary: 'New protection', cve_ids: [], vendor: null, product: null, known_exploited: false, ...overrides }
}

test('news date filtering parses each candidate once and preserves fallback dates, ties and original objects', (t) => {
  const rows = Object.freeze([
    Object.freeze(news('b', '2026-10-20T00:00:00Z')),
    Object.freeze(news('z', 'invalid', { updated_at: '2026-10-21T00:00:00Z' })),
    Object.freeze(news('a', '2026-10-20T00:00:00Z')),
    Object.freeze(news('missing', null)),
    Object.freeze(news('old', '2026-10-13T00:00:00Z')),
  ])
  const originalParse = Date.parse
  const now = originalParse('2026-10-21T00:00:00Z')
  let calls = 0
  t.mock.method(Date, 'parse', (value) => { calls++; return originalParse(value) })
  const filtered = filterSecurityNews(rows, defaultSecurityNewsFilters(), now)
  assert.deepEqual(filtered.map(({ id }) => id), ['z', 'a', 'b', 'old', 'missing'])
  assert.equal(calls, 5)
  assert.strictEqual(filtered[0], rows[1])
  assert.deepEqual(filterSecurityNews(rows, { ...defaultSecurityNewsFilters(), days: 7 }, now).map(({ id }) => id), ['z', 'a', 'b'])
})

test('news prepared sort values are per call and see changed timestamps and translations immediately', () => {
  const first = news('first', '2026-10-20T00:00:00Z')
  const second = news('second', '2026-10-19T00:00:00Z')
  const rows = [first, second]
  assert.strictEqual(filterSecurityNews(rows, defaultSecurityNewsFilters(), 0)[0], first)
  second.published_at = '2026-10-21T00:00:00Z'
  second.title_ko = '새로운 번역'
  assert.strictEqual(filterSecurityNews(rows, defaultSecurityNewsFilters(), 0)[0], second)
  assert.deepEqual(filterSecurityNews(rows, { ...defaultSecurityNewsFilters(), search: '새로운' }, 0), [second])
})

test('SLA sorts the minimum of displayed metrics and skips search text work for empty queries', (t) => {
  const metric = (id, percent, millis, paused = false) => Object.freeze({ sla_id: id, sla_name: id, remaining_percent: percent, remaining_millis: millis, paused })
  const rows = Object.freeze([
    Object.freeze({ key: 'TAC-10', summary: '혼합', status: '진행', assignee: '담당자', slas: Object.freeze([metric('a', 1, 100), metric('b', 4, 3, true)]) }),
    Object.freeze({ key: 'TAC-2', summary: '일반', status: '진행', assignee: '담당자', slas: Object.freeze([metric('a', 1, 50)]) }),
  ])
  const normalize = String.prototype.normalize
  let calls = 0
  t.mock.method(String.prototype, 'normalize', function (form) { calls++; return normalize.call(this, form) })
  const filters = defaultSlaStatusFilters()
  assert.deepEqual(filterSlaStatusTickets(rows, filters).map(({ key }) => key), ['TAC-2', 'TAC-10'])
  assert.equal(calls, 1)
  assert.deepEqual(filterSlaStatusTickets(rows, { ...filters, sort: 'remaining_millis' }).map(({ key }) => key), ['TAC-10', 'TAC-2'])
  assert.deepEqual(filterSlaStatusTickets(rows, { ...filters, sort: 'remaining_millis', stage: 'a' }).map(({ key }) => key), ['TAC-2', 'TAC-10'])
  assert.deepEqual(filterSlaStatusTickets(rows, { ...filters, scope: 'paused', search: '담당자 b' }).map(({ key }) => key), ['TAC-10'])
  assert.equal(filterSlaStatusTickets(rows, { ...filters, scope: 'running', search: 'b' }).length, 0)
})

test('SLA date sorting parses each ticket once while keeping invalid dates and equal keys stable', (t) => {
  const rows = Object.freeze([
    Object.freeze({ key: 'first', created_at: 'invalid' }),
    Object.freeze({ key: 'second', created_at: '2026-10-21T00:00:00Z' }),
    Object.freeze({ key: 'third', created_at: '2026-10-21T00:00:00Z' }),
  ])
  const originalParse = Date.parse
  let calls = 0
  t.mock.method(Date, 'parse', (value) => { calls++; return originalParse(value) })
  assert.deepEqual(sortSlaViolationTickets(rows, { key: 'created_at', direction: 'desc' }), rows)
  assert.equal(calls, rows.length)
  assert.strictEqual(sortSlaViolationTickets(rows, null), rows)
})

test('reused collators preserve numeric, Korean, case and stable equal-key ordering', () => {
  const organizations = Object.freeze([
    Object.freeze({ id: '9', name: '기관10', issue_count: 3 }),
    Object.freeze({ id: 'b', name: '기관2', issue_count: 3 }),
    Object.freeze({ id: 'a', name: '기관2', issue_count: 3 }),
    Object.freeze({ id: '0', name: '기관100', issue_count: 4 }),
  ])
  const expected = [...organizations].sort((a, b) => b.issue_count - a.issue_count || a.name.localeCompare(b.name, 'ko-KR', { numeric: true, sensitivity: 'base' }) || a.id.localeCompare(b.id))
  assert.deepEqual(sortPartnerOrganizationsByIssueCount(organizations), expected)
  const tickets = Object.freeze(['TAC-2', 'TAC-10', 'TAC-10', 'tac-10', 'TAC-01', 'TAC-100'].map((key, index) => Object.freeze({ key, closed: index === 5 })))
  const sorted = [...tickets].sort((a, b) => Number(a.closed) - Number(b.closed) || b.key.localeCompare(a.key, 'en', { numeric: true }))
  assert.deepEqual(filterRedeployments(tickets, 'all', '', ''), sorted)
  assert.strictEqual(sorted[0], tickets[1])
  assert.strictEqual(sorted[1], tickets[2])
})
