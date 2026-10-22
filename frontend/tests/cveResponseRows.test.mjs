// frontend/tests/cveResponseRows.test.mjs
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
function load(relative) {
  const filename = path.join(sourceRoot, `${relative}.ts`)
  if (modules.has(filename)) return modules.get(filename).exports
  const module = { exports: {} }
  modules.set(filename, module)
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }, fileName: filename }).outputText
  new Function('require', 'module', 'exports', compiled)((dependency) => dependency.startsWith('@/') ? load(dependency.slice(2)) : require(dependency), module, module.exports)
  return module.exports
}

const { defaultSecurityNewsFilters, filterCveResponseRows, filterSecurityNews, isUnknownCveProduct } = load('application/services/securityNews')
const now = Date.parse('2026-10-22T05:00:00Z')
function item(overrides = {}) {
  return { id: 'one', source_id: 'nvd', kind: 'cve', title: 'Original vulnerability title', summary: 'Short original summary', url: 'https://nvd.nist.gov/vuln/detail/CVE-2026-12345', published_at: '2026-10-21T00:00:00Z', updated_at: null, cve_ids: ['CVE-2026-12345'], severity: 'high', cvss_score: 8.1, cvss_version: '3.1', known_exploited: false, vendor: null, product: null, due_date: null, ...overrides }
}
function remediation(product, affected_versions = '', fixed_version = null, vendor = null) {
  return { vendor, product, affected_versions, fixed_version, reference_url: null }
}
function rows(items, overrides = {}) {
  return filterCveResponseRows(items, { ...defaultSecurityNewsFilters(), ...overrides }, now)
}

test('CVE rows expose each product and version pair before pagination without mutating snapshots', () => {
  const input = [item({ remediations: Array.from({ length: 23 }, (_, index) => remediation('Tomcat', `9.0.${index}`, `9.0.${index + 1}`)) }), item({ id: 'news', kind: 'advisory' })]
  const original = structuredClone(input)
  const result = rows(input, { sort: 'affected-version' })
  assert.equal(result.length, 23)
  assert.equal(result.slice(0, 20).length, 20)
  assert.deepEqual(result.slice(20).map((row) => row.remediation.affected_versions), ['9.0.20', '9.0.21', '9.0.22'])
  assert.equal(new Set(result.map((row) => row.id)).size, 23)
  assert.equal(result[0].item, input[0])
  assert.equal(result[0].remediation, input[0].remediations[0])
  assert.deepEqual(input, original)
})

test('original full descriptions and row metadata support normalized all-term search', () => {
  const input = [item({ original_description: `${'Long source text '.repeat(120)} Authentication bypass affects TLS endpoint`, title_ko: '한국어 제목', remediations: [remediation('Tomcat', '9.0.116', '9.0.117', 'Apache'), remediation('Other library', '2.0', '2.1')] })]
  for (const search of ['ｔｏｍｃａｔ AUTHENTICATION', '한국어 9.0.117', 'CVE-2026-12345 APACHE tls', 'original bypass tomcat']) {
    assert.deepEqual(rows(input, { search }).map((row) => row.remediation.product), ['Tomcat'])
  }
  assert.equal(rows(input, { search: 'authentication endpoint' }).length, 2)
  assert.equal(rows(input, { search: 'tomcat 2.1' }).length, 0)
  assert.equal(rows(input, { search: 'tomcat missing-term' }).length, 0)
  assert.equal(filterSecurityNews(input, { ...defaultSecurityNewsFilters(), search: 'authentication endpoint' }, now).length, 1)
})

test('a long source description is normalized once even when one CVE has thousands of version rows', (t) => {
  const normalize = String.prototype.normalize
  let longDescriptionNormalizations = 0
  t.mock.method(String.prototype, 'normalize', function (form) {
    if (this.length > 100000) longDescriptionNormalizations += 1
    return normalize.call(this, form)
  })
  const input = [item({ original_description: `${'Original source text '.repeat(5000)} authentication bypass`, remediations: Array.from({ length: 2000 }, (_, index) => remediation(index % 2 ? 'Tomcat' : 'OpenSSL', '9.0.9', '9.0.10')) })]
  const result = rows(input, { search: 'authentication tomcat 9.0.10' })
  assert.equal(result.length, 1000)
  assert.ok(result.every((row) => row.remediation.product === 'Tomcat'))
  assert.equal(longDescriptionNormalizations, 1)
})

test('unknown product hiding applies per row and preserves known software in mixed CVEs', () => {
  const input = [item({ remediations: [remediation('Tomcat'), remediation('제품 확인 필요'), remediation('  제품 확인 필요  '), remediation('  ')] }), item({ id: 'fallback-known', product: ' OpenSSL ', vendor: 'OpenSSL' }), item({ id: 'fallback-unknown' }), item({ id: 'fallback-empty', product: '  ' })]
  assert.equal(defaultSecurityNewsFilters().hideUnknownProducts, false)
  assert.equal(rows(input).length, 7)
  assert.deepEqual(rows(input, { hideUnknownProducts: true }).map((row) => row.remediation.product).sort(), ['OpenSSL', 'Tomcat'])
  const fallback = rows(input).find((row) => row.item.id === 'fallback-unknown')
  assert.deepEqual(fallback.remediation, remediation('제품 확인 필요'))
  for (const product of [null, undefined, '', ' ', '제품 확인 필요', ' 제품 확인 필요 ']) assert.equal(isUnknownCveProduct(product), true)
  assert.equal(isUnknownCveProduct('제품 확인 필요 없음'), false)
})

test('software sorting groups product and vendor with natural affected versions and unknown products last', () => {
  const input = [item({ remediations: [remediation('Tomcat', '9.0.10', null, 'Apache'), remediation('제품 확인 필요'), remediation('Zoo', '1.0'), remediation('Tomcat', '9.0.9', null, 'Apache'), remediation('Alpha', '1.0')] })]
  const labels = (sort) => rows(input, { sort }).map((row) => `${row.remediation.product}:${row.remediation.affected_versions}`)
  assert.deepEqual(labels('software'), ['Alpha:1.0', 'Tomcat:9.0.9', 'Tomcat:9.0.10', 'Zoo:1.0', '제품 확인 필요:'])
  assert.deepEqual(labels('software-desc'), ['Zoo:1.0', 'Tomcat:9.0.9', 'Tomcat:9.0.10', 'Alpha:1.0', '제품 확인 필요:'])
  const vendors = [item({ remediations: [remediation('Library', '1.0', null, 'B'), remediation('Library', '2.0', null, 'A')] })]
  assert.deepEqual(rows(vendors, { sort: 'software' }).map((row) => row.remediation.vendor), ['A', 'B'])
})

test('affected versions sort numerically across products and keep unknowns last in both directions', () => {
  const input = [item({ remediations: [remediation('Alpha', '9.0.10'), remediation('Beta', '9.0.9'), remediation('Gamma', '10.0'), remediation('Delta', ''), remediation('Epsilon', '버전 확인 필요'), remediation('Zeta', '< 8.0')] })]
  assert.deepEqual(rows(input, { sort: 'affected-version' }).map((row) => row.remediation.product), ['Zeta', 'Beta', 'Alpha', 'Gamma', 'Delta', 'Epsilon'])
  assert.deepEqual(rows(input, { sort: 'affected-version-desc' }).map((row) => row.remediation.product), ['Gamma', 'Alpha', 'Beta', 'Zeta', 'Delta', 'Epsilon'])
})

test('fixed versions use natural version order and preserve missing fixes at the end', () => {
  const input = [item({ remediations: [remediation('A', '9', '9.0.10'), remediation('B', '9', '9.0.9'), remediation('C', '10', '10.0'), remediation('D', '99', null), remediation('E', '0', '해결 버전 미확인')] })]
  assert.deepEqual(rows(input, { sort: 'fixed-version' }).map((row) => row.remediation.product), ['B', 'A', 'C', 'D', 'E'])
  assert.deepEqual(rows(input, { sort: 'fixed-version-desc' }).map((row) => row.remediation.product), ['C', 'A', 'B', 'D', 'E'])
})

test('row filters combine source severity exploitation and date without introducing ordinary news', () => {
  const input = [item({ id: 'kev', source_id: 'cisa-kev', known_exploited: true, remediations: [remediation('Tomcat', '9'), remediation('OpenSSL', '1')] }), item({ id: 'nvd', known_exploited: true }), item({ id: 'old', source_id: 'cisa-kev', known_exploited: true, published_at: '2026-09-01' }), item({ id: 'news', source_id: 'cisa-kev', kind: 'news', known_exploited: true })]
  const filters = { source: 'cisa-kev', severity: 'high-risk', exploitedOnly: true, days: 7 }
  assert.deepEqual(rows(input, filters).map((row) => row.id), ['kev:0', 'kev:1'])
  assert.equal(rows(input, { ...filters, severity: 'critical' }).length, 0)
  assert.equal(rows(input, { ...filters, kind: 'updates' }).length, 0)
  assert.equal(rows(input, { ...filters, hideUnknownProducts: true, search: 'tomcat' }).length, 1)
})

test('newest severity and equal version ties have deterministic order independent of source order', () => {
  const input = [item({ id: 'b', remediations: [remediation('Library', '1'), remediation('Library', '1')] }), item({ id: 'a', remediations: [remediation('Library', '1')] }), item({ id: 'old-critical', severity: 'critical', cvss_score: 9.8, published_at: '2026-10-01', remediations: [remediation('Library', '1')] })]
  for (const sort of ['newest', 'affected-version', 'software']) {
    assert.deepEqual(rows(input, { sort }).map((row) => row.id), ['a:0', 'b:0', 'b:1', 'old-critical:0'])
    assert.deepEqual(rows([...input].reverse(), { sort }).map((row) => row.id), ['a:0', 'b:0', 'b:1', 'old-critical:0'])
  }
  assert.equal(rows(input, { sort: 'severity' })[0].item.id, 'old-critical')
})
