// frontend/tests/annualChartInteractions.test.mjs
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
  'Area', 'AreaChart', 'Bar', 'BarChart', 'CartesianGrid', 'Cell', 'Legend',
  'ReferenceLine', 'ResponsiveContainer', 'Tooltip', 'XAxis', 'YAxis',
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

const { default: SlaMonthlyLineChart } = loadSource('presentation/components/charts/SlaMonthlyLineChart')
const { default: TypeBarChart } = loadSource('presentation/components/charts/TypeBarChart')
const { DashboardExportProvider } = loadSource('presentation/context/DashboardExportContext')
const monthly = [
  { month: '2026-01', year: 2026, month_num: 1, total: 5, met: 4, rate: 80 },
  { month: '2026-02', year: 2026, month_num: 2, total: 0, met: 0, rate: 0 },
]
const slaProps = { title: '최초응답 SLA', subtitle: '전체 기간', monthly, color: '#123456' }
const byType = {
  '장애 문의': { avg_days: 1.25, avg_hours: 30, count: 5 },
  '제품 설치': { avg_days: 0, avg_hours: 0, count: 0 },
}

function render(element) {
  let view
  act(() => { view = TestRenderer.create(element) })
  return view
}

test('SLA chart payload and both dot states select the source month without duplicate bubbling', () => {
  const calls = []
  const view = render(React.createElement(SlaMonthlyLineChart, { ...slaProps, onMonthClick: (...args) => calls.push(args) }))
  const chart = view.root.findByType('AreaChart')
  const area = view.root.findByType('Area')
  const point = chart.props.data[0]
  let stopped = 0
  act(() => {
    chart.props.onClick({ activePayload: [{ payload: point }] })
    chart.props.onClick({ activePayload: [] })
    chart.props.onClick(undefined)
    area.props.dot({ cx: 20, cy: 30, payload: point }).props.onClick({ stopPropagation: () => stopped++ })
    area.props.activeDot({ cx: 20, cy: 30, payload: point }).props.onClick({ stopPropagation: () => stopped++ })
  })
  assert.equal(stopped, 2)
  assert.deepEqual(calls, [[monthly[0], 'all'], [monthly[0], 'all'], [monthly[0], 'all']])
  assert.equal(area.props.dot({ payload: chart.props.data[1] }).type, 'g')
  act(() => view.unmount())
})

test('SLA collapsed details expose target, met and violated filters including all zero-count actions', () => {
  const calls = []
  const view = render(React.createElement(SlaMonthlyLineChart, { ...slaProps, onMonthClick: (...args) => calls.push(args) }))
  assert.equal(view.root.findByType('details').props.open, false)
  act(() => view.root.findByType('details').props.onToggle({ currentTarget: { open: true } }))
  assert.equal(view.root.findByType('details').props.open, true)
  const buttons = view.root.findAllByType('button')
  assert.deepEqual(buttons.map((button) => button.children.join('')), ['5', '4', '1', '0', '0', '0'])
  assert.ok(buttons.every((button) => button.props.type === 'button' && button.props['aria-label'].includes('상세 보기')))
  act(() => buttons.forEach((button) => button.props.onClick()))
  assert.deepEqual(calls, monthly.flatMap((entry) => ['all', 'met', 'violated'].map((status) => [entry, status])))
  act(() => view.unmount())
})

test('SLA all-zero input keeps the exact-count actions when no rate can be charted', () => {
  const calls = []
  const view = render(React.createElement(SlaMonthlyLineChart, { ...slaProps, monthly: [monthly[1]], onMonthClick: (...args) => calls.push(args) }))
  assert.equal(view.root.findAllByType('AreaChart').length, 0)
  assert.equal(view.root.findAllByType('details').length, 1)
  const buttons = view.root.findAllByType('button')
  assert.equal(buttons.length, 3)
  act(() => buttons[2].props.onClick())
  assert.deepEqual(calls, [[monthly[1], 'violated']])
  act(() => view.unmount())
})

test('type bars resolve Recharts payloads and the details table preserves counts and both duration units', () => {
  const calls = []
  const view = render(React.createElement(TypeBarChart, { byType, onTypeClick: (type) => calls.push(type) }))
  const bar = view.root.findByType('Bar')
  act(() => {
    bar.props.onClick({ payload: { name: '장애 문의' } })
    bar.props.onClick({ name: '제품 설치' })
    bar.props.onClick({ payload: { name: '없는 유형' } })
    bar.props.onClick({})
  })
  assert.deepEqual(calls, ['장애 문의', '제품 설치'])
  assert.equal(view.root.findByType('details').props.open, false)
  act(() => view.root.findByType('details').props.onToggle({ currentTarget: { open: true } }))
  assert.equal(view.root.findByType('details').props.open, true)
  const rows = view.root.findByType('tbody').findAllByType('tr')
  assert.deepEqual(rows[0].findAllByType('td').slice(0, 3).map((cell) => cell.children.join('')), ['5건', '1.25', '30'])
  assert.deepEqual(rows[1].findAllByType('td').slice(0, 3).map((cell) => cell.children.join('')), ['0건', '0', '0'])
  const buttons = view.root.findAllByType('button')
  assert.ok(buttons[1].props['aria-label'].includes('0건'))
  act(() => buttons.forEach((button) => button.props.onClick()))
  assert.deepEqual(calls, ['장애 문의', '제품 설치', '장애 문의', '제품 설치'])
  act(() => view.unmount())
})

test('ordinary dashboard callers retain charts without new controls or click handlers', () => {
  const view = render(React.createElement(React.Fragment, null,
    React.createElement(SlaMonthlyLineChart, slaProps), React.createElement(TypeBarChart, { byType }),
  ))
  assert.equal(view.root.findAllByType('details').length, 0)
  assert.equal(view.root.findAllByType('button').length, 0)
  const chart = view.root.findByType('AreaChart')
  assert.equal(chart.props.onClick, undefined)
  assert.equal(view.root.findByType('Area').props.dot({ payload: chart.props.data[0] }).props.onClick, undefined)
  assert.equal(view.root.findByType('Bar').props.onClick, undefined)
  act(() => view.unmount())
})

test('PDF exports omit every added control and callback while keeping chart animation disabled', () => {
  const unexpected = () => assert.fail('Export must not invoke an interaction callback')
  const view = render(React.createElement(DashboardExportProvider, null,
    React.createElement(SlaMonthlyLineChart, { ...slaProps, onMonthClick: unexpected }),
    React.createElement(TypeBarChart, { byType, onTypeClick: unexpected }),
  ))
  assert.equal(view.root.findAllByType('details').length, 0)
  assert.equal(view.root.findAllByType('button').length, 0)
  const chart = view.root.findByType('AreaChart')
  const area = view.root.findByType('Area')
  const bar = view.root.findByType('Bar')
  assert.equal(chart.props.onClick, undefined)
  assert.equal(area.props.dot({ payload: chart.props.data[0] }).props.onClick, undefined)
  assert.equal(typeof area.props.activeDot, 'object')
  assert.equal(bar.props.onClick, undefined)
  assert.equal(area.props.isAnimationActive, false)
  assert.equal(bar.props.isAnimationActive, false)
  act(() => view.unmount())
})
