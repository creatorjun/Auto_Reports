// frontend/tests/partnerOrganizations.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { createRequire } from 'node:module'
import path from 'node:path'
import test from 'node:test'
import ts from 'typescript'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)
const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')
const modules = new Map()

function loadSource(relative) {
  const base = path.join(sourceRoot, relative)
  const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate))
  assert.ok(filename, `Missing source module: ${relative}`)
  if (modules.has(filename)) return modules.get(filename).exports
  const module = { exports: {} }
  modules.set(filename, module)
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    fileName: filename,
  }).outputText
  new Function('require', 'module', 'exports', compiled)((dependency) => (
    dependency.startsWith('./')
      ? loadSource(path.join(path.dirname(relative), dependency))
      : require(dependency)
  ), module, module.exports)
  return module.exports
}

const { filterPartnerIssues, sortPartnerOrganizationsByIssueCount } = loadSource('domain/Partner')
const { sortDashboardStatuses } = loadSource('domain/DashboardStatusPolicy')

test('orders known current statuses consistently and then sorts unknown statuses', () => {
  assert.deepEqual(
    sortDashboardStatuses(['새 상태 2', '닫힘', '할 일', '새 상태 1', '할 일']),
    ['할 일', '닫힘', '새 상태 1', '새 상태 2'],
  )
})

test('sorts partner organizations by total issue count without mutating the API result', () => {
  const organizations = [
    { id: '3', name: '세 번째', issue_count: 9 },
    { id: '1', name: '첫 번째', issue_count: 31 },
    { id: '2', name: '두 번째', issue_count: 14 },
  ]
  const original = structuredClone(organizations)

  assert.deepEqual(
    sortPartnerOrganizationsByIssueCount(organizations).map(({ id }) => id),
    ['1', '2', '3'],
  )
  assert.deepEqual(organizations, original)
})

test('uses the Korean partner name and id as deterministic tie breakers', () => {
  const organizations = [
    { id: '2', name: '가나다', issue_count: 10 },
    { id: '3', name: '라마바', issue_count: 10 },
    { id: '1', name: '가나다', issue_count: 10 },
  ]

  assert.deepEqual(
    sortPartnerOrganizationsByIssueCount(organizations).map(({ id }) => id),
    ['1', '2', '3'],
  )
})

test('applies the dashboard request-type, current-status and semester policy to partner issues', () => {
  const issue = (key, type, status, created) => ({ key, type, status, created })
  const issues = [
    issue('H1-INCIDENT', '인시던트', '할 일', '2026-03-10 09:00'),
    issue('H2-INCIDENT', '인시던트', '닫힘', '2026-08-10 09:00'),
    issue('H1-IMPROVEMENT', '개선', '닫힘', '2026-04-10 09:00'),
    issue('H1-HIDDEN', '승인된 서비스 요청', '할 일', '2026-05-10 09:00'),
    issue('H1-EXCLUDED', '라이선스 요청', '할 일', '2026-05-10 09:00'),
    issue('OLD-INCIDENT', '인시던트', '할 일', '2025-03-10 09:00'),
  ]

  assert.deepEqual(
    filterPartnerIssues(issues, new Set(['인시던트']), ['인시던트', '개선'], new Set(['할 일']), 'h1', 2026)
      .map(({ key }) => key),
    ['H1-INCIDENT', 'H1-HIDDEN'],
  )
  assert.deepEqual(
    filterPartnerIssues(issues, null, ['인시던트', '개선'], null, null, 2026)
      .map(({ key }) => key),
    ['H1-INCIDENT', 'H2-INCIDENT', 'H1-IMPROVEMENT', 'H1-HIDDEN', 'OLD-INCIDENT'],
  )
})
