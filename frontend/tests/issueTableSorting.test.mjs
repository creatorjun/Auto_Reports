// frontend/tests/issueTableSorting.test.mjs
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
const dependencies = {
  '@/presentation/context/JiraContext': { useJira: () => ({ jiraBrowse: 'https://jira.example.test/browse' }) },
  '@/presentation/components/common/IssueModalShell': { default: ({ children }) => React.createElement('section', null, children) },
  '@/presentation/components/common/StatusBadge': { StatusBadge: ({ status }) => React.createElement('span', null, status) },
  '@/presentation/components/common/IssueTypeBadge': { IssueTypeBadge: ({ type }) => React.createElement('span', null, type) },
}

function loadSource(relative) {
  const base = path.join(sourceRoot, relative)
  const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
  assert.ok(filename, `Missing source module: ${relative}`)
  if (modules.has(filename)) return modules.get(filename).exports
  const module = { exports: {} }
  modules.set(filename, module)
  if (filename.endsWith('.json')) {
    const data = JSON.parse(fs.readFileSync(filename, 'utf8'))
    module.exports = { ...data, default: data }
    return module.exports
  }
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
    fileName: filename,
  }).outputText
  new Function('require', 'module', 'exports', compiled)((dependency) => {
    if (Object.hasOwn(dependencies, dependency)) return dependencies[dependency]
    if (dependency.startsWith('@/')) return loadSource(dependency.slice(2))
    if (dependency.startsWith('.')) return loadSource(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)))
    return require(dependency)
  }, module, module.exports)
  return module.exports
}

const consumerNames = ['DataRequest', 'IncompleteIssue', 'IssueReview', 'ResultPending', 'SlaDelay', 'SlaOverdue', 'SlaViolation', 'WeeklyCreated', 'WeeklyResolved']
const consumers = Object.fromEntries(consumerNames.map((name) => [name, loadSource(`presentation/components/tables/${name}Modal`).default]))
const AnnualIssueDetailsModal = loadSource('presentation/components/annual/AnnualIssueDetailsModal').default
const { sortIssueTableRows } = loadSource('presentation/utils/issueTableSorting')

function issue(key, overrides = {}) {
  return { key, summary: `제목 ${key}`, type: '개선', status: '처리 중', resp_status: '처리 중', created: '2026-10-01 10:00', resolved: '2026-10-02 10:00', elapsed_days: 2, elapsed_hours: 2, over_h: 2, ...overrides }
}

function fixture() {
  return Object.freeze([
    Object.freeze(issue('TAC-10', { summary: '다리', type: '서비스 요청', status: '할 일', resp_status: '할 일', created: '2026-10-02 10:00', resolved: '2026-10-02 10:00', elapsed_days: 100, elapsed_hours: 100, over_h: 100, sla_met: true })),
    Object.freeze(issue('TAC-2', { summary: '가방', type: '개선', status: '결과 대기 중', resp_status: '결과 대기 중', created: '2026-10-01T12:00:00+09:00', resolved: '2026-10-01T12:00:00+09:00', elapsed_days: 2, elapsed_hours: 2, over_h: 2, sla_met: null })),
    Object.freeze(issue('TAC-100', { summary: '나무', type: '인시던트', status: '처리 중', resp_status: '처리 중', created: '2026-10-01T04:00:00Z', resolved: '2026-10-01T04:00:00Z', elapsed_days: 10, elapsed_hours: 10, over_h: 10, sla_met: false })),
  ])
}

function render(t, component, issues, extra = {}) {
  let view
  act(() => { view = TestRenderer.create(React.createElement(component, { issues, total: issues.length, title: '상세', stage: '최초 응답 SLA', status: '처리 중', onClose() {}, ...extra })) })
  t.after(() => act(() => view.unmount()))
  return view
}

function keys(view) {
  return view.root.findByType('tbody').findAllByType('tr').map((row) => row.props['aria-label'].split(' ')[0])
}

function header(view, label) {
  return view.root.findByType('thead').findAllByType('th').find((cell) => cell.findByType('button').props['aria-label'].startsWith(`${label} `))
}

function clickHeader(view, label) {
  act(() => header(view, label).findByType('button').props.onClick())
}

function button(view, label) {
  return view.root.findAllByType('button').find((node) => node.props['aria-label'] === label || node.children.join('') === label)
}

function clickPage(view, label) {
  const target = button(view, String(label))
  assert.ok(target, `Missing page control: ${label}`)
  act(() => target.props.onClick())
}

const ascendingKeys = {
  '이슈 번호': ['TAC-2', 'TAC-10', 'TAC-100'],
  '티켓': ['TAC-2', 'TAC-10', 'TAC-100'],
  '제목': ['TAC-2', 'TAC-100', 'TAC-10'],
  '유형': ['TAC-2', 'TAC-10', 'TAC-100'],
  '현재 상태': ['TAC-2', 'TAC-100', 'TAC-10'],
  '상태': ['TAC-2', 'TAC-100', 'TAC-10'],
  '생성일시': ['TAC-2', 'TAC-100', 'TAC-10'],
  '해결일시': ['TAC-2', 'TAC-100', 'TAC-10'],
  '경과일': ['TAC-2', 'TAC-100', 'TAC-10'],
  '초과시간': ['TAC-2', 'TAC-100', 'TAC-10'],
  '처리시간': ['TAC-2', 'TAC-100', 'TAC-10'],
  'SLA': ['TAC-100', 'TAC-10', 'TAC-2'],
}

for (const [name, component] of [...Object.entries(consumers), ['AnnualIssueDetails', AnnualIssueDetailsModal]]) {
  test(`${name} sorts every visible column in both directions without changing source data`, (t) => {
    const issues = fixture()
    const view = render(t, component, issues)
    const labels = view.root.findByType('thead').findAllByType('button').map((node) => node.props['aria-label'].replace(' 오름차순 정렬', ''))
    assert.ok(labels.length >= 4)
    assert.deepEqual(keys(view), ['TAC-10', 'TAC-2', 'TAC-100'])
    for (const label of labels) {
      assert.ok(ascendingKeys[label], `Missing expected order for ${label}`)
      assert.equal(header(view, label).props.scope, 'col')
      assert.equal(header(view, label).findByType('button').props.type, 'button')
      clickHeader(view, label)
      assert.deepEqual(keys(view), ascendingKeys[label], `${label}: ascending`)
      assert.equal(header(view, label).props['aria-sort'], 'ascending')
      clickHeader(view, label)
      assert.deepEqual(keys(view), label === 'SLA' ? ['TAC-10', 'TAC-100', 'TAC-2'] : [...ascendingKeys[label]].reverse(), `${label}: descending`)
      assert.equal(header(view, label).props['aria-sort'], 'descending')
      assert.equal(header(view, label).findByType('button').props['aria-label'], `${label} 오름차순 정렬`)
      assert.ok(view.root.findByType('thead').findAllByType('th').filter((cell) => cell !== header(view, label)).every((cell) => cell.props['aria-sort'] === 'none'))
    }
    assert.deepEqual(issues.map((row) => row.key), ['TAC-10', 'TAC-2', 'TAC-100'])
  })
}

test('missing, invalid and equal values stay stable in either sorting direction', () => {
  const data = [
    { key: 'same-1', text: 'same', number: 2, date: '2026-10-01T12:00:00+09:00' },
    { key: 'missing', text: ' ', number: null, date: '' },
    { key: 'same-2', text: 'same', number: 2, date: '2026-10-01T03:00:00Z' },
    { key: 'invalid', text: '—', number: NaN, date: 'invalid' },
    { key: 'first', text: 'first', number: 0, date: '2026-09-30' },
  ]
  for (const type of ['text', 'number', 'date']) {
    const columns = [{ header: type, sortType: type, sortValue: (row) => row[type] }]
    assert.deepEqual(sortIssueTableRows(data, columns, { column: type, direction: 'asc' }).map((row) => row.key), ['first', 'same-1', 'same-2', 'missing', 'invalid'])
    assert.deepEqual(sortIssueTableRows(data, columns, { column: type, direction: 'desc' }).map((row) => row.key), ['same-1', 'same-2', 'first', 'missing', 'invalid'])
  }
})

test('shared pagination sorts all rows before slicing and returns to the first page', (t) => {
  const issues = Array.from({ length: 61 }, (_, index) => issue(`TAC-${61 - index}`))
  const view = render(t, consumers.IncompleteIssue, issues)
  clickPage(view, 2)
  assert.deepEqual(keys(view), Array.from({ length: 11 }, (_, index) => `TAC-${11 - index}`))
  clickHeader(view, '이슈 번호')
  assert.deepEqual(keys(view), Array.from({ length: 50 }, (_, index) => `TAC-${index + 1}`))
  assert.equal(button(view, '1').props['aria-current'], 'page')
  clickPage(view, 2)
  assert.deepEqual(keys(view), Array.from({ length: 11 }, (_, index) => `TAC-${index + 51}`))
  clickHeader(view, '이슈 번호')
  assert.deepEqual(keys(view), Array.from({ length: 50 }, (_, index) => `TAC-${61 - index}`))
})

test('annual sorting applies before external pagination and survives search filtering', (t) => {
  const issues = Array.from({ length: 45 }, (_, index) => issue(`TAC-${45 - index}`, { summary: index % 2 ? '검색 대상' : '다른 이슈' }))
  const view = render(t, AnnualIssueDetailsModal, issues, { dateField: 'created' })
  assert.ok(header(view, '생성일시'))
  clickPage(view, '다음')
  assert.equal(keys(view)[0], 'TAC-25')
  clickHeader(view, '티켓')
  assert.deepEqual(keys(view), Array.from({ length: 20 }, (_, index) => `TAC-${index + 1}`))
  clickPage(view, '다음')
  assert.equal(keys(view)[0], 'TAC-21')
  act(() => view.root.findByType('input').props.onChange({ target: { value: '검색 대상' } }))
  assert.deepEqual(keys(view), Array.from({ length: 20 }, (_, index) => `TAC-${(index + 1) * 2}`))
  assert.equal(header(view, '티켓').props['aria-sort'], 'ascending')
  clickPage(view, '다음')
  assert.deepEqual(keys(view), ['TAC-42', 'TAC-44'])
  clickHeader(view, '티켓')
  assert.deepEqual(keys(view), Array.from({ length: 20 }, (_, index) => `TAC-${44 - index * 2}`))
  assert.equal(button(view, '이전').props.disabled, true)
})

test('mobile controls use the same column order and can restore the default order', (t) => {
  const view = render(t, consumers.IssueReview, fixture())
  const select = view.root.findByProps({ 'aria-label': '이슈 정렬 기준' })
  act(() => select.props.onChange({ target: { value: '경과일' } }))
  assert.deepEqual(keys(view), ['TAC-2', 'TAC-100', 'TAC-10'])
  const directionButton = view.root.findAllByType('button').find((node) => node.props['aria-label'] === '경과일 내림차순 정렬' && node.findAllByType('svg').length === 1 && node.children.includes('오름차순'))
  assert.ok(directionButton)
  act(() => directionButton.props.onClick())
  assert.deepEqual(keys(view), ['TAC-10', 'TAC-100', 'TAC-2'])
  const mobileKeys = view.root.findAll((node) => node.type === 'div' && node.props.role === 'link').map((node) => node.props['aria-label'].split(' ')[0])
  assert.deepEqual(mobileKeys, keys(view))
  act(() => select.props.onChange({ target: { value: '' } }))
  assert.deepEqual(keys(view), ['TAC-10', 'TAC-2', 'TAC-100'])
  assert.ok(view.root.findByType('thead').findAllByType('th').every((cell) => cell.props['aria-sort'] === 'none'))
})

test('sorted rows retain accessible Jira navigation and support empty lists', (t) => {
  const previousWindow = globalThis.window
  const opened = []
  globalThis.window = { open: (...args) => opened.push(args) }
  t.after(() => { if (previousWindow === undefined) delete globalThis.window; else globalThis.window = previousWindow })
  const view = render(t, consumers.WeeklyCreated, fixture())
  clickHeader(view, '이슈 번호')
  const firstRow = view.root.findByType('tbody').findAllByType('tr')[0]
  assert.equal(firstRow.props.tabIndex, 0)
  let prevented = false
  act(() => firstRow.props.onKeyDown({ key: 'Enter', preventDefault() { prevented = true } }))
  assert.equal(prevented, true)
  assert.deepEqual(opened, [['https://jira.example.test/browse/TAC-2', '_blank', 'noopener,noreferrer']])
  act(() => view.update(React.createElement(consumers.WeeklyCreated, { issues: [], total: 0, onClose() {} })))
  clickHeader(view, '이슈 번호')
  assert.deepEqual(keys(view), [])
})
