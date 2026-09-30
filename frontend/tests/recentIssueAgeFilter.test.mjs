// frontend/tests/recentIssueAgeFilter.test.mjs
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
    if (dependency === '@/presentation/context/JiraContext') return { useJira: () => ({ jiraBase: 'https://jira.example.test' }) }
    if (dependency.startsWith('@/')) return loadSource(dependency.slice(2))
    if (dependency.startsWith('.')) return loadSource(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)))
    return require(dependency)
  }, module, module.exports)
  return module.exports
}

const { default: RecentIssuesWidget } = loadSource('presentation/components/charts/RecentIssuesWidget')
const { filterRecentIssuesByElapsedDays } = loadSource('domain/Issue')
const { DashboardExportProvider } = loadSource('presentation/context/DashboardExportContext')

function loadDashboardContent() {
  const filename = path.join(sourceRoot, 'presentation/pages/DashboardPage.tsx')
  const compiled = ts.transpileModule(`${fs.readFileSync(filename, 'utf8')}\nexport { DashboardContent }`, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
    fileName: filename,
  }).outputText
  const module = { exports: {} }
  const setCurrentReport = () => {}
  const stub = () => null
  new Function('require', 'module', 'exports', compiled)((dependency) => {
    if (dependency.endsWith('.css')) return {}
    if (dependency === 'react-router-dom') return { useParams: () => ({}) }
    if (dependency === '@/presentation/hooks/useReport') return {}
    if (dependency === '@/presentation/state/reportStore') return { useReportStore: () => ({ setCurrentReport }) }
    if (dependency === '@/presentation/components/charts/RecentIssuesWidget') return { default: RecentIssuesWidget }
    if (dependency === '@/presentation/components/export/DashboardPdfExportStage') return {
      default: ({ children, ...props }) => React.createElement('ExportStage', props,
        React.createElement(DashboardExportProvider, null, children)),
    }
    if (dependency.startsWith('@/presentation/components/')) return {
      default: stub, SUMMARY_ICONS: {}, ModalFallback: stub, ChartFallback: stub,
    }
    return dependency.startsWith('@/') ? loadSource(dependency.slice(2)) : require(dependency)
  }, module, module.exports)
  return module.exports.DashboardContent
}

function issue(days, overrides = {}) {
  return {
    key: `TACEA-${String(days).padStart(3, '0')}`, summary: `${days}일 경과 이슈`,
    created: '2026-09-10 09:00', type: '인시던트', status: '처리 중', stage_index: 1,
    elapsed_days: days, reporter: '보고자', tac_team: '담당자', ...overrides,
  }
}

function render(t, details, { elapsedDaysThreshold = null, elapsedDaysComparison = 'gte', exportMode = false } = {}) {
  const changes = []
  let nativeValue = elapsedDaysThreshold === null ? '' : String(elapsedDaysThreshold)
  const numberInput = {
    validity: { badInput: false },
    get value() { return nativeValue },
    set value(value) { nativeValue = value; this.validity.badInput = false },
  }
  let updateFilter
  function Harness({ details }) {
    const [threshold, setThreshold] = React.useState(elapsedDaysThreshold)
    const [comparison, setComparison] = React.useState(elapsedDaysComparison)
    updateFilter = (value, nextComparison) => act(() => { setThreshold(value); setComparison(nextComparison) })
    return React.createElement(RecentIssuesWidget, {
      details, elapsedDaysThreshold: threshold, elapsedDaysComparison: comparison,
      onElapsedDaysFilterChange(value, nextComparison) {
        changes.push([value, nextComparison]); setThreshold(value); setComparison(nextComparison)
      },
    })
  }
  const content = (rows) => {
    const widget = React.createElement(Harness, { details: rows })
    return exportMode ? React.createElement(DashboardExportProvider, null, widget) : widget
  }
  let view
  act(() => {
    view = TestRenderer.create(content(details), {
      createNodeMock: (element) => {
        if (element.type === 'table') return { offsetWidth: 1000 }
        if (element.type === 'input') return numberInput
        return null
      },
    })
  })
  t.after(() => act(() => view.unmount()))
  return { view, changes, numberInput, updateFilter: (...args) => updateFilter(...args), updateDetails: (rows) => act(() => view.update(content(rows))) }
}

function textOf(node) {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  return node.children.map(textOf).join('')
}

function keys(view) {
  const bodies = (view.root ?? view).findAllByType('tbody')
  return bodies.length ? bodies[0].findAllByType('tr').map((row) => textOf(row.findAllByType('td')[0])) : []
}

function input(view) {
  return view.root.findByProps({ 'aria-label': '최근 이슈 경과일' })
}

function comparisonInput(view) {
  return view.root.findByProps({ 'aria-label': '최근 이슈 경과일 조건' })
}

function selectComparison(view, value) {
  const target = { value }
  act(() => comparisonInput(view).props.onChange({ target, currentTarget: target }))
}

function type(view, value, badInput = false) {
  const target = { value, validity: { badInput } }
  act(() => {
    input(view).props.onInput({ target, currentTarget: target })
    input(view).props.onChange({ target, currentTarget: target })
  })
}

function nativeInput(view, value, badInput) {
  const target = { value, validity: { badInput } }
  act(() => input(view).props.onInput({ target, currentTarget: target }))
}

function submit(view) {
  let prevented = false
  act(() => view.root.findByType('form').props.onSubmit({ preventDefault() { prevented = true } }))
  assert.equal(prevented, true)
}

function button(view, label) {
  const result = view.root.findAllByType('button').find((node) => textOf(node) === label)
  assert.ok(result, `Missing button: ${label}`)
  return result
}

function click(node) {
  act(() => node.props.onClick({ stopPropagation() {} }))
}

function header(view, label) {
  return view.root.findByType('thead').findAllByType('th').find((node) => node.props['data-pdf-header'] === label)
}

test('elapsed-day comparisons include the threshold and zero without changing source rows', () => {
  const details = Object.freeze([29, 30, 31, 0].map((days) => Object.freeze(issue(days))))
  assert.deepEqual(filterRecentIssuesByElapsedDays(details, 30).map((row) => row.elapsed_days), [30, 31])
  assert.deepEqual(filterRecentIssuesByElapsedDays(details, 0, 'gte').map((row) => row.elapsed_days), [29, 30, 31, 0])
  assert.deepEqual(filterRecentIssuesByElapsedDays(details, 30, 'lte').map((row) => row.elapsed_days), [29, 30, 0])
  assert.deepEqual(filterRecentIssuesByElapsedDays(details, 0, 'lte').map((row) => row.elapsed_days), [0])
  assert.deepEqual(filterRecentIssuesByElapsedDays(details, null, 'gte'), details)
  assert.deepEqual(filterRecentIssuesByElapsedDays(details, null, 'lte'), details)
  assert.deepEqual(details.map((row) => row.elapsed_days), [29, 30, 31, 0])
})

test('typing does not apply the filter until search submits and thirty defaults to thirty or more days', (t) => {
  const details = Object.freeze([29, 30, 31].map((days) => Object.freeze(issue(days))))
  const { view, changes } = render(t, details)
  assert.equal(input(view).props.type, 'number')
  assert.equal(button(view, '검색').props.type, 'submit')
  assert.match(textOf(view.root), /경과일/)
  assert.equal(comparisonInput(view).props.value, 'gte')
  assert.deepEqual(comparisonInput(view).findAllByType('option').map((option) => [option.props.value, textOf(option)]), [['gte', '이상'], ['lte', '이하']])
  type(view, '30')
  assert.deepEqual(keys(view), ['TACEA-029', 'TACEA-030', 'TACEA-031'])
  assert.deepEqual(changes, [])
  submit(view)
  assert.deepEqual(keys(view), ['TACEA-030', 'TACEA-031'])
  assert.deepEqual(changes, [[30, 'gte']])
  type(view, '29')
  assert.deepEqual(keys(view), ['TACEA-030', 'TACEA-031'])
  type(view, '30')
  selectComparison(view, 'lte')
  assert.deepEqual(keys(view), ['TACEA-030', 'TACEA-031'])
  assert.deepEqual(changes, [[30, 'gte']])
  submit(view)
  assert.deepEqual(keys(view), ['TACEA-029', 'TACEA-030'])
  assert.deepEqual(changes, [[30, 'gte'], [30, 'lte']])
  assert.deepEqual(details.map((row) => row.elapsed_days), [29, 30, 31])
})

test('zero is searchable and an empty submitted value restores every issue', (t) => {
  const { view, changes } = render(t, [issue(0), issue(1), issue(30)], { elapsedDaysThreshold: 30, elapsedDaysComparison: 'lte' })
  type(view, '0')
  submit(view)
  assert.deepEqual(keys(view), ['TACEA-000'])
  assert.deepEqual(changes.at(-1), [0, 'lte'])
  type(view, '')
  assert.deepEqual(keys(view), ['TACEA-000'])
  submit(view)
  assert.deepEqual(keys(view), ['TACEA-000', 'TACEA-001', 'TACEA-030'])
  assert.deepEqual(changes.at(-1), [null, 'lte'])
})

test('invalid numeric inputs do not apply a drafted comparison and expose an error', (t) => {
  const { view, changes } = render(t, [issue(0), issue(30), issue(31)], { elapsedDaysThreshold: 30 })
  selectComparison(view, 'lte')
  for (const value of ['-1', '1.5', 'NaN', 'Infinity', '9007199254740992']) {
    type(view, value)
    submit(view)
    assert.deepEqual(keys(view), ['TACEA-030', 'TACEA-031'])
    assert.deepEqual(changes, [])
    assert.equal(input(view).props['aria-invalid'], true)
    assert.ok(view.root.findAllByProps({ role: 'alert' }).some((node) => textOf(node).length > 0))
  }
})

test('native invalid number input with an empty value cannot clear the applied filter', (t) => {
  const { view, changes, numberInput } = render(t, [issue(0), issue(30), issue(31)], { elapsedDaysThreshold: 30 })
  numberInput.validity.badInput = true
  type(view, '', true)
  submit(view)
  assert.deepEqual(keys(view), ['TACEA-030', 'TACEA-031'])
  assert.deepEqual(changes, [])
  assert.equal(input(view).props['aria-invalid'], true)
  assert.ok(view.root.findAllByProps({ role: 'alert' }).length > 0)
  numberInput.validity.badInput = false
  type(view, '')
  submit(view)
  assert.deepEqual(changes, [[null, 'gte']])
  assert.deepEqual(keys(view), ['TACEA-000', 'TACEA-030', 'TACEA-031'])
})

test('reset clears native bad-input validity even when the controlled draft is already empty', (t) => {
  const { view, changes, numberInput } = render(t, [issue(0), issue(30), issue(31)], { elapsedDaysThreshold: 30 })
  numberInput.validity.badInput = true
  type(view, '', true)
  submit(view)
  assert.equal(input(view).props.value, '')
  assert.equal(numberInput.validity.badInput, true)
  click(button(view, '초기화'))
  assert.equal(numberInput.value, '')
  assert.equal(numberInput.validity.badInput, false)
  assert.equal(input(view).props.value, '')
  assert.equal(button(view, '초기화').props.disabled, true)
  assert.deepEqual(changes, [[null, 'gte']])
  assert.deepEqual(keys(view), ['TACEA-000', 'TACEA-030', 'TACEA-031'])
  submit(view)
  assert.equal(view.root.findAllByProps({ role: 'alert' }).length, 0)
  assert.deepEqual(changes, [[null, 'gte'], [null, 'gte']])
})

test('native input without a React change event enables reset when the sanitized value stays empty', (t) => {
  const { view, changes, numberInput } = render(t, [issue(0), issue(30)])
  assert.equal(button(view, '초기화').props.disabled, true)
  numberInput.validity.badInput = true
  nativeInput(view, '', true)
  assert.equal(input(view).props.value, '')
  assert.equal(button(view, '초기화').props.disabled, false)
  click(button(view, '초기화'))
  assert.equal(numberInput.validity.badInput, false)
  assert.equal(button(view, '초기화').props.disabled, true)
  assert.deepEqual(changes, [[null, 'gte']])
  assert.deepEqual(keys(view), ['TACEA-000', 'TACEA-030'])
})

test('reset clears an invalid draft and the applied filter without submitting the form', (t) => {
  const { view, changes } = render(t, [issue(0), issue(30), issue(31)], { elapsedDaysThreshold: 30 })
  type(view, '-1')
  submit(view)
  const reset = button(view, '초기화')
  assert.equal(reset.props.type, 'button')
  click(reset)
  assert.equal(input(view).props.value, '')
  assert.deepEqual(changes, [[null, 'gte']])
  assert.deepEqual(keys(view), ['TACEA-000', 'TACEA-030', 'TACEA-031'])
  assert.notEqual(input(view).props['aria-invalid'], true)
  assert.equal(view.root.findAllByProps({ role: 'alert' }).length, 0)
})

test('reset clears draft and applied comparisons even when the numeric input is empty', (t) => {
  const { view, changes } = render(t, [issue(0), issue(30)])
  assert.equal(button(view, '초기화').props.disabled, true)
  selectComparison(view, 'lte')
  assert.equal(button(view, '초기화').props.disabled, false)
  click(button(view, '초기화'))
  assert.equal(comparisonInput(view).props.value, 'gte')
  assert.equal(button(view, '초기화').props.disabled, true)
  selectComparison(view, 'lte')
  submit(view)
  assert.equal(button(view, '초기화').props.disabled, false)
  selectComparison(view, 'gte')
  assert.equal(button(view, '초기화').props.disabled, false)
  click(button(view, '초기화'))
  assert.equal(input(view).props.value, '')
  assert.equal(comparisonInput(view).props.value, 'gte')
  assert.equal(button(view, '초기화').props.disabled, true)
  assert.deepEqual(changes, [[null, 'gte'], [null, 'lte'], [null, 'gte']])
  assert.deepEqual(keys(view), ['TACEA-000', 'TACEA-030'])
})

test('external applied filter changes synchronize the numeric draft and dropdown', (t) => {
  const { view, updateFilter } = render(t, [issue(29), issue(30), issue(31)], { elapsedDaysThreshold: 30 })
  type(view, '25')
  selectComparison(view, 'lte')
  updateFilter(29, 'lte')
  assert.equal(input(view).props.value, '29')
  assert.equal(comparisonInput(view).props.value, 'lte')
  assert.deepEqual(keys(view), ['TACEA-029'])
  updateFilter(29, 'gte')
  assert.equal(input(view).props.value, '29')
  assert.equal(comparisonInput(view).props.value, 'gte')
  assert.deepEqual(keys(view), ['TACEA-029', 'TACEA-030', 'TACEA-031'])
})

test('new data from other dashboard filters retains the applied elapsed-day threshold', (t) => {
  const { view, updateDetails, changes } = render(t, [issue(29), issue(30), issue(31)])
  type(view, '30')
  submit(view)
  const replacement = Object.freeze([
    Object.freeze(issue(10, { type: '라이센스', status: '할 일' })),
    Object.freeze(issue(30, { type: '개선' })),
    Object.freeze(issue(40, { type: '개선' })),
  ])
  updateDetails(replacement)
  assert.deepEqual(keys(view), ['TACEA-030', 'TACEA-040'])
  assert.equal(input(view).props.value, '30')
  assert.deepEqual(changes, [[30, 'gte']])
  assert.deepEqual(replacement.map((row) => row.elapsed_days), [10, 30, 40])
})

test('applying a filter resets page two to page one while preserving sorting and column widths', (t) => {
  const details = Object.freeze(Array.from({ length: 120 }, (_, index) => Object.freeze(issue(119 - index))))
  const { view } = render(t, details)
  click(header(view, '생성일 (경과)'))
  const resize = view.root.findAllByProps({ title: '드래그하여 너비 조절' })[0]
  act(() => resize.props.onPointerDown({ preventDefault() {}, stopPropagation() {}, clientX: 100, pointerId: 1, target: { setPointerCapture() {} } }))
  act(() => resize.props.onPointerMove({ clientX: 110 }))
  act(() => resize.props.onPointerUp())
  const widths = view.root.findAllByType('col').map((column) => column.props.style.width)
  assert.notEqual(widths[0], '10.00%')
  click(button(view, '2'))
  assert.equal(keys(view)[0], 'TACEA-050')
  type(view, '60')
  submit(view)
  assert.deepEqual(keys(view), Array.from({ length: 50 }, (_, index) => `TACEA-${String(index + 60).padStart(3, '0')}`))
  assert.match(textOf(header(view, '생성일 (경과)')), /↑/)
  assert.deepEqual(view.root.findAllByType('col').map((column) => column.props.style.width), widths)
  click(header(view, '생성일 (경과)'))
  assert.equal(keys(view)[0], 'TACEA-119')
  assert.match(textOf(header(view, '생성일 (경과)')), /↓/)
  click(button(view, '2'))
  assert.equal(keys(view)[0], 'TACEA-069')
  selectComparison(view, 'lte')
  assert.equal(keys(view)[0], 'TACEA-069')
  submit(view)
  assert.deepEqual(keys(view), Array.from({ length: 50 }, (_, index) => `TACEA-${String(60 - index).padStart(3, '0')}`))
  assert.deepEqual(view.root.findAllByType('col').map((column) => column.props.style.width), widths)
  assert.deepEqual(details.map((row) => row.elapsed_days), Array.from({ length: 120 }, (_, index) => 119 - index))
})

test('an empty filtered result has a filter-specific message and remains resettable', (t) => {
  const { view } = render(t, [issue(10)])
  type(view, '11')
  submit(view)
  assert.deepEqual(keys(view), [])
  assert.match(textOf(view.root), /경과일이 11일 이상인 이슈가 없습니다/)
  type(view, '9')
  selectComparison(view, 'lte')
  submit(view)
  assert.deepEqual(keys(view), [])
  assert.match(textOf(view.root), /경과일이 9일 이하인 이슈가 없습니다/)
  click(button(view, '초기화'))
  assert.deepEqual(keys(view), ['TACEA-010'])
})

for (const { comparison, label, threshold, firstDay } of [
  { comparison: 'gte', label: '이상', threshold: 20, firstDay: 20 },
  { comparison: 'lte', label: '이하', threshold: 64, firstDay: 0 },
]) {
  test(`PDF mode includes every ${comparison} match beyond one page and omits filter controls`, (t) => {
    const details = Object.freeze(Array.from({ length: 85 }, (_, index) => Object.freeze(issue(index))))
    const { view } = render(t, details, { elapsedDaysThreshold: threshold, elapsedDaysComparison: comparison, exportMode: true })
    assert.equal(view.root.findAllByType('form').length, 0)
    assert.equal(view.root.findAllByType('input').length, 0)
    assert.equal(view.root.findAllByType('select').length, 0)
    assert.equal(view.root.findAllByType('button').length, 0)
    assert.equal(view.root.findByType('table').props['data-pdf-table-layout'], 'recent')
    assert.deepEqual(keys(view), Array.from({ length: 65 }, (_, index) => `TACEA-${String(index + firstDay).padStart(3, '0')}`))
    assert.equal(details.length, 85)
    assert.equal(details.at(-1).elapsed_days, 84)
  })

  test(`dashboard export snapshots retain the applied ${comparison} threshold after the visible filter changes`, async (t) => {
    const DashboardContent = loadDashboardContent()
    const details = Object.freeze(Array.from({ length: 85 }, (_, index) => Object.freeze(issue(index))))
    const report = {
      id: 1, scope: 'standard', report_year: null,
      week_start: '2026-08-01', week_end: '2026-08-31', report_date: '2026-08-31 23:59',
      ai_analysis: null,
      widgets: { w7: { name: '최근 이슈', total: details.length, data: { issue_details: details } } },
    }
    let view
    await act(async () => { view = TestRenderer.create(React.createElement(DashboardContent, { report })) })
    t.after(() => act(() => view.unmount()))
    type(view, String(threshold))
    selectComparison(view, comparison)
    submit(view)
    type(view, '10')
    const otherComparison = comparison === 'gte' ? 'lte' : 'gte'
    selectComparison(view, otherComparison)
    await act(async () => button(view, 'PDF 내보내기').props.onClick())

    const stage = view.root.findByType('ExportStage')
    const expectedKeys = Array.from({ length: 65 }, (_, index) => `TACEA-${String(index + firstDay).padStart(3, '0')}`)
    assert.ok(stage.props.metadata.filters.includes(`최근 이슈: 경과일 ${threshold}일 ${label}`))
    assert.deepEqual(keys(stage), expectedKeys)
    assert.equal(stage.findAllByType('form').length, 0)
    assert.equal(stage.findAllByType('select').length, 0)
    type(view, String(threshold))
    submit(view)
    assert.equal(keys(view).length, 21)
    assert.equal(keys(view)[0], comparison === 'gte' ? 'TACEA-000' : 'TACEA-064')
    assert.deepEqual(keys(stage), expectedKeys)
    assert.ok(stage.props.metadata.filters.includes(`최근 이슈: 경과일 ${threshold}일 ${label}`))
    assert.equal(details.length, 85)
  })
}
