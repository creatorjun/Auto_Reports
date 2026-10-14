// frontend/tests/tablePreferences.test.mjs
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

function sourceLoader() {
  const modules = new Map()
  function load(relative) {
    const base = path.join(sourceRoot, relative)
    const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
    assert.ok(filename, `Missing module ${relative}`)
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX }, fileName: filename }).outputText
    new Function('require', 'module', 'exports', compiled)((dependency) => {
      if (dependency === '@/presentation/context/JiraContext') return { useJira: () => ({ jiraBase: 'https://jira.example.test', jiraBrowse: 'https://jira.example.test/browse' }) }
      if (dependency.startsWith('@/')) return load(dependency.slice(2))
      if (dependency.startsWith('.')) return load(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)).replaceAll('\\', '/'))
      return require(dependency)
    }, module, module.exports)
    return module.exports
  }
  return load
}

function browserStorage(t, entries = {}, failure) {
  const data = new Map(Object.entries(entries))
  const writes = []
  const storage = {
    getItem(key) { if (failure === 'read') throw new Error('Storage is blocked'); return data.get(key) ?? null },
    setItem(key, value) { if (failure === 'write') throw new Error('Storage quota exceeded'); writes.push([key, value]); data.set(key, value) },
    removeItem(key) { data.delete(key) },
  }
  const previous = ['window', 'localStorage'].map((key) => [key, Object.getOwnPropertyDescriptor(globalThis, key)])
  const getStorage = () => { if (failure === 'access') throw new Error('Storage access denied'); return storage }
  Object.defineProperty(globalThis, 'window', { configurable: true, value: Object.defineProperty({}, 'localStorage', { get: getStorage }) })
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, get: getStorage })
  t.after(() => { for (const [key, descriptor] of previous) { if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key] } })
  return { data, writes }
}

const defaults = Object.freeze({ key: 0.4, summary: 0.6 })
const storedWidths = { key: 0.55, summary: 0.45 }
const storedSort = { key: 'summary', direction: 'desc' }
const preference = (sort = storedSort, widths = storedWidths) => JSON.stringify({ version: 1, sort, widths })
const storageKey = (key) => `auto-reports-table:${key}`

function hookView(t, key = 'test:one', min = 0.15, load = sourceLoader()) {
  const { useTablePreferences } = load('presentation/hooks/useTablePreferences')
  let current
  function Probe({ preferenceKey }) { current = useTablePreferences(preferenceKey, defaults, min); return null }
  let view
  act(() => { view = TestRenderer.create(React.createElement(Probe, { preferenceKey: key })) })
  t.after(() => act(() => view.unmount()))
  return {
    get current() { return current },
    setKey(nextKey) { act(() => view.update(React.createElement(Probe, { preferenceKey: nextKey }))) },
    unmount() { act(() => view.unmount()) },
  }
}

test('saved sort and widths survive unmount and a fresh module load with functional updates intact', (t) => {
  const { data } = browserStorage(t)
  const first = hookView(t)
  assert.equal(first.current.sort, null)
  assert.deepEqual(first.current.widths, defaults)
  act(() => {
    first.current.setSort({ key: 'summary', direction: 'asc' })
    first.current.setSort((previous) => ({ ...previous, direction: 'desc' }))
    first.current.setWidths((previous) => ({ ...previous, key: 0.55, summary: 0.45 }))
  })
  assert.deepEqual(JSON.parse(data.get(storageKey('test:one'))), { version: 1, sort: storedSort, widths: storedWidths })
  first.unmount()
  const reloaded = hookView(t)
  assert.deepEqual(reloaded.current.sort, storedSort)
  assert.deepEqual(reloaded.current.widths, storedWidths)
  assert.deepEqual(defaults, { key: 0.4, summary: 0.6 })
})

test('switching table keys loads each table without writing the outgoing settings into the next table', (t) => {
  const secondSort = { key: 'key', direction: 'asc' }
  const { data, writes } = browserStorage(t, {
    [storageKey('test:one')]: preference(),
    [storageKey('test:two')]: preference(secondSort, defaults),
  })
  const view = hookView(t)
  writes.length = 0
  view.setKey('test:two')
  assert.deepEqual(view.current.sort, secondSort)
  assert.deepEqual(view.current.widths, defaults)
  for (const [key, value] of writes.filter(([key]) => key === storageKey('test:two'))) assert.deepEqual(JSON.parse(value), { version: 1, sort: secondSort, widths: defaults }, key)
  assert.deepEqual(JSON.parse(data.get(storageKey('test:one'))), { version: 1, sort: storedSort, widths: storedWidths })
  view.setKey('test:one')
  assert.deepEqual(view.current.sort, storedSort)
  assert.deepEqual(view.current.widths, storedWidths)
  writes.length = 0
  view.setKey(undefined)
  act(() => view.current.setSort({ key: 'key', direction: 'desc' }))
  assert.equal(writes.length, 0)
})

test('malformed JSON and unsupported versions safely restore default table state', (t) => {
  const malformed = ['{', 'null', '[]', 'true', JSON.stringify({ version: 2, sort: storedSort, widths: storedWidths })]
  const entries = Object.fromEntries(malformed.map((value, index) => [storageKey(`bad:${index}`), value]))
  browserStorage(t, entries)
  malformed.forEach((_, index) => {
    const view = hookView(t, `bad:${index}`)
    assert.equal(view.current.sort, null)
    assert.deepEqual(view.current.widths, defaults)
    view.unmount()
  })
})

test('invalid sort and invalid widths fall back independently while valid saved state is retained', (t) => {
  const badSorts = [{ key: 'removed', direction: 'asc' }, { key: 'key', direction: 'up' }, { key: '__proto__', direction: 'desc' }, 'summary']
  const badWidths = [{ key: 0.1, summary: 0.9 }, { key: 0.55, summary: 0.65 }, { key: 0.55 }, { key: '0.55', summary: 0.45 }, { key: null, summary: 1 }]
  const entries = Object.fromEntries([
    ...badSorts.map((sort, index) => [storageKey(`sort:${index}`), preference(sort)]),
    ...badWidths.map((widths, index) => [storageKey(`width:${index}`), preference(storedSort, widths)]),
    [storageKey('width:infinite'), '{"version":1,"sort":{"key":"summary","direction":"desc"},"widths":{"key":1e309,"summary":0.45}}'],
    [storageKey('width:column-min'), preference(storedSort, { key: 0.2, summary: 0.8 })],
  ])
  browserStorage(t, entries)
  badSorts.forEach((_, index) => {
    const view = hookView(t, `sort:${index}`)
    assert.equal(view.current.sort, null)
    assert.deepEqual(view.current.widths, storedWidths)
    view.unmount()
  })
  for (const key of [...badWidths.map((_, index) => `width:${index}`), 'width:infinite', 'width:column-min']) {
    const view = hookView(t, key, { key: 0.3, summary: 0.15 })
    assert.deepEqual(view.current.sort, storedSort)
    assert.deepEqual(view.current.widths, defaults)
    view.unmount()
  }
})

for (const failure of ['access', 'read', 'write']) {
  test(`table controls remain usable when browser storage fails during ${failure}`, (t) => {
    browserStorage(t, {}, failure)
    const view = hookView(t)
    act(() => {
      view.current.setSort(storedSort)
      view.current.setWidths(storedWidths)
    })
    assert.deepEqual(view.current.sort, storedSort)
    assert.deepEqual(view.current.widths, storedWidths)
  })
}

const ticket = {
  key: 'TACEA-10', summary: '가 문의', issue_type: '개선', created_at: '2026-05-05T16:00:00Z', elapsed_days: 20,
  customer: '서울교통공사', partners: [], reporter: '보고자', assignee: '담당자', tac_assignee: 'TAC', current_status: '처리 중', status_durations: [],
  breaches: [{ metric: 'initial_response', breached_at: '2026-05-06T04:00:00Z', status: '할일' }, { metric: 'resolution', breached_at: '2026-05-08T06:00:00Z', status: '처리 중' }], warnings: [],
}
const slaTickets = [ticket, { ...ticket, key: 'TACEA-2', summary: '나 문의', elapsed_days: 2 }]
const textOf = (node) => typeof node === 'string' || typeof node === 'number' ? String(node) : (node.children ?? []).map(textOf).join('')

test('both SLA lists independently restore visible ordering and resized columns after leaving and reloading', (t) => {
  const { data } = browserStorage(t)
  let view
  function render(load) {
    const { default: List } = load('presentation/components/sla-violations/SlaViolationList')
    act(() => { view = TestRenderer.create(React.createElement('main', null,
      React.createElement(List, { metric: 'initial_response', tickets: slaTickets }),
      React.createElement(List, { metric: 'resolution', tickets: slaTickets }),
    )) })
  }
  render(sourceLoader())
  t.after(() => act(() => view.unmount()))
  const list = (index) => view.root.findAllByType('section')[index]
  const keys = (index) => list(index).findAllByType('a').map((anchor) => anchor.props.href.split('/').at(-1))
  const sort = (index, label) => list(index).findAllByType('button').find((button) => button.props['aria-label'] === label)
  act(() => sort(0, '번호 오름차순 정렬').props.onClick())
  act(() => sort(1, '경과일 오름차순 정렬').props.onClick())
  act(() => sort(1, '경과일 오름차순 정렬 중, 내림차순 정렬').props.onClick())
  const oldWidths = [list(0).props.style['--sla-ticket-columns'], list(1).props.style['--sla-ticket-columns']]
  act(() => list(0).findByProps({ 'aria-label': '번호 열 너비 조절' }).props.onKeyDown({ key: 'ArrowRight', shiftKey: true, preventDefault() {}, stopPropagation() {} }))
  act(() => list(1).findByProps({ 'aria-label': '제목 열 너비 조절' }).props.onKeyDown({ key: 'ArrowLeft', shiftKey: false, preventDefault() {}, stopPropagation() {} }))
  const adjustedWidths = [list(0).props.style['--sla-ticket-columns'], list(1).props.style['--sla-ticket-columns']]
  assert.notEqual(adjustedWidths[0], oldWidths[0])
  assert.notEqual(adjustedWidths[1], oldWidths[1])
  assert.deepEqual(keys(0), ['TACEA-2', 'TACEA-10'])
  assert.deepEqual(keys(1), ['TACEA-10', 'TACEA-2'])
  assert.equal(data.has(storageKey('sla-violations:initial_response')), true)
  assert.equal(data.has(storageKey('sla-violations:resolution')), true)
  act(() => view.unmount())
  render(sourceLoader())
  assert.deepEqual(keys(0), ['TACEA-2', 'TACEA-10'])
  assert.deepEqual(keys(1), ['TACEA-10', 'TACEA-2'])
  assert.deepEqual([list(0).props.style['--sla-ticket-columns'], list(1).props.style['--sla-ticket-columns']], adjustedWidths)
  assert.equal(sort(0, '번호 오름차순 정렬 중, 내림차순 정렬').props['aria-pressed'], true)
  assert.equal(sort(1, '경과일 내림차순 정렬 중, 오름차순 정렬').props['aria-pressed'], true)
})

test('dashboard recent issue header sorting and drag widths persist while exports and unkeyed tables stay isolated', (t) => {
  const { data } = browserStorage(t)
  const rows = [
    { key: 'T-2', summary: '나 문의', type: '개선', status: '처리 중', created: '2026-05-01 09:00', stage_index: 1, elapsed_days: 2, reporter: '', tac_team: '' },
    { key: 'T-1', summary: '가 문의', type: '인시던트', status: '처리 중', created: '2026-05-02 09:00', stage_index: 1, elapsed_days: 1, reporter: '', tac_team: '' },
  ]
  const props = { tablePreferenceKey: 'dashboard:recent-issues', details: rows, elapsedDaysThreshold: null, elapsedDaysComparison: 'gte' }
  let view
  function render(load, exportMode = false, keyed = true) {
    const { default: Widget } = load('presentation/components/charts/RecentIssuesWidget')
    const { DashboardExportProvider } = load('presentation/context/DashboardExportContext')
    const widget = React.createElement(Widget, { ...props, tablePreferenceKey: keyed ? props.tablePreferenceKey : undefined })
    act(() => { view = TestRenderer.create(exportMode ? React.createElement(DashboardExportProvider, null, widget) : widget, { createNodeMock: (element) => element.type === 'table' ? { offsetWidth: 1000 } : null }) })
  }
  render(sourceLoader())
  t.after(() => act(() => view.unmount()))
  const header = () => view.root.findByProps({ 'data-pdf-header': '이슈' })
  const keys = () => view.root.findByType('tbody').findAllByType('tr').map((row) => textOf(row.findAllByType('td')[0]))
  const widths = () => view.root.findAllByType('col').map((column) => column.props.style.width)
  const defaultWidths = widths()
  act(() => header().props.onClick())
  const resize = view.root.findAllByProps({ title: '드래그하여 너비 조절' })[0]
  act(() => resize.props.onPointerDown({ preventDefault() {}, stopPropagation() {}, clientX: 100, pointerId: 1, target: { setPointerCapture() {} } }))
  act(() => resize.props.onPointerMove({ clientX: 110 }))
  act(() => resize.props.onPointerUp())
  const adjustedWidths = widths()
  assert.notDeepEqual(adjustedWidths, defaultWidths)
  assert.deepEqual(keys(), ['T-1', 'T-2'])
  const saved = data.get(storageKey('dashboard:recent-issues'))
  assert.ok(saved)
  act(() => view.unmount())
  render(sourceLoader())
  assert.deepEqual(widths(), adjustedWidths)
  assert.deepEqual(keys(), ['T-1', 'T-2'])
  assert.match(textOf(header()), /↑/)
  act(() => view.unmount())
  render(sourceLoader(), true)
  assert.deepEqual(widths(), defaultWidths)
  assert.deepEqual(keys(), ['T-2', 'T-1'])
  act(() => view.unmount())
  assert.equal(data.get(storageKey('dashboard:recent-issues')), saved)
  render(sourceLoader(), false, false)
  assert.deepEqual(widths(), defaultWidths)
  assert.deepEqual(keys(), ['T-2', 'T-1'])
  act(() => header().props.onClick())
  assert.equal(data.get(storageKey('dashboard:recent-issues')), saved)
})
