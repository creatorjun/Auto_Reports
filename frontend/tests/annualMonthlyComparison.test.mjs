// frontend/tests/annualMonthlyComparison.test.mjs
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
const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')
const modules = new Map()
const charts = Object.fromEntries([
  'Bar', 'BarChart', 'CartesianGrid', 'Legend', 'ResponsiveContainer', 'Tooltip', 'XAxis', 'YAxis',
].map((name) => [name, ({ children, ...props }) => React.createElement(name, props, children)]))

function loadSource(relative) {
  const base = path.join(sourceRoot, relative)
  const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
  assert.ok(filename, `Missing source module: ${relative}`)
  if (modules.has(filename)) return modules.get(filename).exports
  const module = { exports: {} }
  modules.set(filename, module)
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
    fileName: filename,
  }).outputText
  new Function('require', 'module', 'exports', compiled)((dependency) => {
    if (dependency === 'recharts') return charts
    return dependency.startsWith('@/') ? loadSource(dependency.slice(2)) : require(dependency)
  }, module, module.exports)
  return module.exports
}

const { buildAnnualMonthlyComparison } = loadSource('presentation/utils/annualMonthlyComparison')
const { default: AnnualMonthlyComparison } = loadSource('presentation/components/annual/AnnualMonthlyComparison')
const { DashboardExportProvider } = loadSource('presentation/context/DashboardExportContext')
const entry = (month, count, year = 2026) => ({ month: `${year}-${month}`, year, month_num: month, count })

test('aligns independently ordered months and preserves missing values separately from zero', () => {
  const created = [entry(3, 7), entry(1, 0), entry(2, 2), entry(1, 99, 2025)]
  const resolved = [entry(4, 4), entry(3, 0), entry(1, 5)]
  const original = structuredClone([created, resolved])
  assert.deepEqual(buildAnnualMonthlyComparison(created, resolved, 2026, '2026-12-31'), [
    { month: '1월', monthNumber: 1, created: 0, resolved: 5 },
    { month: '2월', monthNumber: 2, created: 2, resolved: null },
    { month: '3월', monthNumber: 3, created: 7, resolved: 0 },
    { month: '4월', monthNumber: 4, created: null, resolved: 4 },
  ])
  assert.deepEqual([created, resolved], original)
})

test('excludes future monthly placeholders while retaining the current partial month', () => {
  const monthly = Array.from({ length: 12 }, (_, index) => entry(index + 1, index < 9 ? 5 : 0))
  const rows = buildAnnualMonthlyComparison(monthly, monthly, 2026, '2026-09-09')
  assert.deepEqual(rows.map((row) => row.monthNumber), [1, 2, 3, 4, 5, 6, 7, 8, 9])
  assert.equal(buildAnnualMonthlyComparison(monthly, monthly, 2026, '2025-12-31').length, 0)
  assert.equal(buildAnnualMonthlyComparison(monthly, monthly, 2026, '2027-01-01').length, 12)
})

test('retains a filtered semester without inventing months or counts', () => {
  assert.deepEqual(buildAnnualMonthlyComparison([entry(7, 0)], [entry(8, 3)], 2026, '2026-09-09'), [
    { month: '7월', monthNumber: 7, created: 0, resolved: null },
    { month: '8월', monthNumber: 8, created: null, resolved: 3 },
  ])
  assert.deepEqual(buildAnnualMonthlyComparison([], [], 2026, '2026-12-31'), [])
})

test('invalid month or count cannot become a misleading zero or chart value', () => {
  const created = [entry(0, 5), entry(13, 5), entry(1.5, 5), entry(1, Number.NaN), entry(2, -1), entry(3, Infinity)]
  assert.deepEqual(buildAnnualMonthlyComparison(created, [], 2026, '2026-12-31'), [
    { month: '1월', monthNumber: 1, created: null, resolved: null },
    { month: '2월', monthNumber: 2, created: null, resolved: null },
    { month: '3월', monthNumber: 3, created: null, resolved: null },
  ])
})

test('all-zero data still renders a chart and an expandable exact-count table', () => {
  let view
  act(() => {
    view = TestRenderer.create(React.createElement(AnnualMonthlyComparison, {
      created: [entry(1, 0)], resolved: [entry(1, 0)], year: 2026, periodEnd: '2026-09-09', subtitle: '전체 기간',
    }))
  })
  assert.equal(view.root.findAllByType('BarChart').length, 1)
  assert.equal(view.root.findByType('details').props.open, false)
  assert.deepEqual(view.root.findAllByType('td').map((cell) => cell.children.join('')), ['0', '0'])
  assert.ok(view.root.findAllByType('p').some((paragraph) => paragraph.children.join('') === '해당 기간의 등록·해결 건수가 모두 0건입니다.'))
  act(() => view.root.findByType('details').props.onToggle({ currentTarget: { open: true } }))
  assert.equal(view.root.findByType('details').props.open, true)
  act(() => view.unmount())
})

test('PDF mode expands all rows and disables both bar animations without losing missing data', () => {
  let view
  const created = Array.from({ length: 12 }, (_, index) => entry(index + 1, index))
  act(() => {
    view = TestRenderer.create(React.createElement(DashboardExportProvider, null,
      React.createElement(AnnualMonthlyComparison, {
        created, resolved: [entry(1, 0)], year: 2026, periodEnd: '2026-09-09', subtitle: '전체 기간',
      }),
    ))
  })
  assert.equal(view.root.findByType('details').props.open, true)
  assert.deepEqual(view.root.findAllByType('Bar').map((bar) => bar.props.isAnimationActive), [false, false])
  assert.equal(view.root.findByType('tbody').findAllByType('tr').length, 9)
  assert.deepEqual(view.root.findAll((node) => node.props['data-pdf-kind']).map((node) => node.props['data-pdf-kind']), ['chart', 'table'])
  assert.equal(view.root.findAllByType('td')[3].children.join(''), '—')
  assert.equal(view.root.findAllByType('td')[3].props['aria-label'], '해결 데이터 없음')
  assert.equal(view.root.findAllByType('YAxis').length, 1)
  act(() => view.unmount())
})
