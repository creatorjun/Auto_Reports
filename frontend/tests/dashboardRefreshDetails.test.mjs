// frontend/tests/dashboardRefreshDetails.test.mjs
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

function sourceLoader(overrides) {
  const modules = new Map()
  function load(relative) {
    if (Object.hasOwn(overrides, relative)) return overrides[relative]
    if (relative.endsWith('.css')) return {}
    if (relative.endsWith('.json')) return { default: JSON.parse(fs.readFileSync(path.join(sourceRoot, relative), 'utf8')) }
    if (relative.startsWith('presentation/components/')) {
      if (!modules.has(relative)) {
        const component = path.basename(relative)
        const Probe = (props) => React.createElement('component-probe', { ...props, component })
        modules.set(relative, { default: Probe, SUMMARY_ICONS: {}, ModalFallback: Probe, ChartFallback: Probe })
      }
      return modules.get(relative)
    }
    const base = path.join(sourceRoot, relative)
    const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
    assert.ok(filename, `Missing module ${relative}`)
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
      fileName: filename,
    }).outputText
    new Function('require', 'module', 'exports', compiled)((dependency) => {
      if (Object.hasOwn(overrides, dependency)) return overrides[dependency]
      if (dependency.startsWith('@/')) return load(dependency.slice(2))
      if (dependency.startsWith('.')) return load(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)).replaceAll('\\', '/'))
      return require(dependency)
    }, module, module.exports)
    return module.exports
  }
  return load
}

function fixtureReport(id, count) {
  const issues = Array.from({ length: count }, (_, index) => ({
    key: `REPORT-${id}-${index}`, summary: `Report ${id} issue ${index}`,
    type: '서비스 요청', status: '자료 요청 중', created: '2026-10-13T09:00:00', elapsed_days: 1,
  }))
  const widget = (data) => ({ name: '검증 지표', total: count, jql: '', data })
  return {
    id, scope: 'standard', report_year: null, week_start: '2026-10-12', week_end: '2026-10-18',
    report_date: '2026-10-18', created_at: '2026-10-18T09:00:00', sentiment: null, ai_analysis: null,
    widgets: {
      w7: widget({ issue_details: issues }),
      w12: widget({ violation_distribution: [{ stage: '해결 시간 SLA', count, rate: 100, issue_details: issues }] }),
      w13: widget({ by_status_details: { '자료 요청 중': issues } }),
    },
  }
}

const cases = [
  {
    name: 'open work-type requests', modal: 'IncompleteIssueModal',
    open: (find) => find('WorkTypeSummaryCard').props.onClick(),
  },
  {
    name: 'SLA violations', modal: 'SlaViolationModal',
    open: (find) => { const chart = find('SlaDonutChart'); chart.props.onSliceClick(chart.props.distribution[0]) },
  },
  {
    name: 'SLA delays', modal: 'SlaDelayModal',
    open: (find) => { const chart = find('ReasonPieChart'); chart.props.onSliceClick('자료 요청 중', chart.props.byStatusDetails['자료 요청 중']) },
  },
]

for (const item of cases) {
  test(`report regeneration clears stale ${item.name} details and reopens with current issues`, async (t) => {
    let report = fixtureReport(7, 1)
    const setCurrentReport = () => {}
    const load = sourceLoader({
      'react-router-dom': { useParams: () => ({}) },
      'presentation/hooks/useReport': {
        useLatestReport: () => ({ data: report, isLoading: false, error: null }),
        useReportById: () => ({}), useAnnualReport: () => ({}),
      },
      'presentation/hooks/useReportRefreshShortcut': { useReportRefreshShortcut: () => () => {} },
      'presentation/state/reportStore': { useReportStore: () => ({ setCurrentReport }) },
      'presentation/context/ReportGenerationContext': { useReportGeneration: () => ({ pending: false }) },
    })
    const DashboardPage = load('presentation/pages/DashboardPage').default
    let view
    t.after(() => { if (view) act(() => view.unmount()) })
    await act(async () => { view = TestRenderer.create(React.createElement(DashboardPage)) })
    const findAll = (component) => view.root.findAllByType('component-probe').filter((node) => node.props.component === component)
    const find = (component) => { const nodes = findAll(component); assert.ok(nodes.length, `Missing ${component}`); return nodes[0] }

    await act(async () => { item.open(find) })
    assert.equal(find(item.modal).props.total, 1)
    assert.deepEqual(find(item.modal).props.issues.map((issue) => issue.key), ['REPORT-7-0'])
    await act(async () => { view.update(React.createElement(DashboardPage)) })
    assert.equal(find(item.modal).props.total, 1)

    report = fixtureReport(8, 2)
    await act(async () => { view.update(React.createElement(DashboardPage)) })
    assert.equal(findAll(item.modal).length, 0)
    assert.equal(find('WorkTypeSummaryCard').props.count, 2)
    await act(async () => { item.open(find) })
    assert.equal(find(item.modal).props.total, 2)
    assert.deepEqual(find(item.modal).props.issues.map((issue) => issue.key), ['REPORT-8-0', 'REPORT-8-1'])
  })
}
