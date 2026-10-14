// frontend/tests/redeployments.test.mjs
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
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')
const cache = new Map()
function load(relative) {
  if (relative === 'presentation/context/JiraContext') return { useJira: () => ({ jiraBrowse: 'https://jira.example/browse' }) }
  const base = path.join(root, relative)
  const filename = [base, `${base}.ts`, `${base}.tsx`].find((item) => fs.existsSync(item) && fs.statSync(item).isFile())
  assert.ok(filename)
  if (cache.has(filename)) return cache.get(filename).exports
  const module = { exports: {} }
  cache.set(filename, module)
  if (filename.endsWith('.json')) {
    const value = JSON.parse(fs.readFileSync(filename, 'utf8'))
    module.exports = { ...value, default: value }
    return module.exports
  }
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX }, fileName: filename }).outputText
  new Function('require', 'module', 'exports', compiled)((dependency) => {
    if (dependency.startsWith('@/')) return load(dependency.slice(2))
    if (dependency.startsWith('.')) return load(path.relative(root, path.resolve(path.dirname(filename), dependency)).replaceAll('\\', '/'))
    return require(dependency)
  }, module, module.exports)
  return module.exports
}

const { redeploymentSummary, redeploymentMonths, filterRedeployments, redeploymentIsStale } = load('application/services/redeploymentReport')
const { default: Tickets } = load('presentation/components/redeployments/RedeploymentTickets')
const ticket = (key, overrides = {}) => ({ key, summary: '[고객사] 재배포', issue_type: '개선', status: '결과 대기 중', closed: false, created_at: '2025-12-01T09:00:00+09:00', resolved_at: null, completion_month: null, cause: '개발오류', reason: '파일 누락', repatch_count: 2, customer: '고객사', partners: [], assignee: '담당자', reporter: '보고자', ...overrides })

test('totals preserve missing versus zero and scope active separately', () => {
  const summary = redeploymentSummary([ticket('TACEA-1'), ticket('TACEA-2', { closed: true, repatch_count: null, reason: null }), ticket('TACEA-3', { repatch_count: 0, cause: null })])
  assert.deepEqual([summary.total, summary.closed, summary.active, summary.repatches, summary.missingCount, summary.missingReason], [3, 1, 2, 2, 1, 1])
  assert.deepEqual(summary.causes, [{ name: '개발오류', count: 2 }, { name: '원인 미입력', count: 1 }])
})

test('monthly completion uses recorded month, includes zeros, excludes active and discloses unmatched months', () => {
  const report = { period_start: '2026-01-01', generated_at: '2026-02-28T15:00:00Z', tickets: [
    ticket('TACEA-1', { closed: true, resolved_at: '2026-02-09T10:00:00+09:00', completion_month: '2026-01' }),
    ticket('TACEA-2', { closed: true }), ticket('TACEA-3', { completion_month: '2026-02' }),
    ticket('TACEA-4', { closed: true, completion_month: '2025-12' }),
  ] }
  assert.deepEqual(redeploymentMonths(report), { months: [{ month: '2026-01', count: 1 }, { month: '2026-02', count: 0 }, { month: '2026-03', count: 0 }], unassigned: 2 })
})

test('cause and text search compose without modifying source and numeric keys sort correctly', () => {
  const items = [ticket('TACEA-2'), ticket('TACEA-10'), ticket('TACEA-1', { closed: true }), ticket('TACEA-3', { cause: '환경변경' })]
  const copy = structuredClone(items)
  assert.deepEqual(filterRedeployments(items, 'active', '개발오류', '파일').map((item) => item.key), ['TACEA-10', 'TACEA-2'])
  assert.equal(filterRedeployments(items, 'closed', '', 'unknown').length, 0)
  assert.deepEqual(items, copy)
})

test('staleness changes exactly at 08:00 KST regardless of browser timezone', () => {
  assert.equal(redeploymentIsStale('2026-10-13T08:00:00+09:00', new Date('2026-10-14T07:59:59+09:00')), false)
  assert.equal(redeploymentIsStale('2026-10-13T08:00:00+09:00', new Date('2026-10-13T23:00:00Z')), true)
  assert.equal(redeploymentIsStale('2026-10-14T08:00:00+09:00', new Date('2026-10-13T23:00:00Z')), false)
})

test('ticket expands original reason and safely links to Jira with unassigned partner fallback', () => {
  let rendered
  act(() => { rendered = TestRenderer.create(React.createElement(Tickets, { tickets: [ticket('TACEA-1')] })) })
  const link = rendered.root.findByType('a')
  assert.equal(link.props.href, 'https://jira.example/browse/TACEA-1')
  assert.equal(link.props.target, '_blank')
  const expand = rendered.root.findByProps({ 'aria-expanded': false })
  act(() => expand.props.onClick())
  assert.ok(JSON.stringify(rendered.toJSON()).includes('재배포 상세 사유'))
  assert.ok(JSON.stringify(rendered.toJSON()).includes('본사'))
  act(() => rendered.unmount())
})
