// frontend/tests/slaIssueSorting.test.mjs
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
  '@/presentation/context/JiraContext': {
    useJira: () => ({ jiraBase: 'https://jira.example.test' }),
  },
  '@/presentation/context/ApplicationServicesContext': {
    useApplicationServices: () => ({ slaDashboard: { getCommentImage: () => assert.fail('Unexpected image request') } }),
  },
  '@/presentation/hooks/useSlaDashboard': {
    useSlaIssueComments: () => ({
      data: [], isLoading: false, isError: false, isFetching: false,
      isFetchingNextPage: false, isFetchNextPageError: false, hasNextPage: false,
      fetchNextPage: () => assert.fail('Unexpected comment request'),
      refetch: () => assert.fail('Unexpected comment refetch'),
    }),
  },
}

function loadSource(relative) {
  if (/\.(svg|png)$/.test(relative)) return { default: relative }
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
    if (Object.hasOwn(dependencies, dependency)) return dependencies[dependency]
    return dependency.startsWith('@/') ? loadSource(dependency.slice(2)) : require(dependency)
  }, module, module.exports)
  return module.exports
}

const { default: SlaIssueActivityTable } = loadSource('presentation/components/sla/SlaIssueActivityTable')
const columns = [
  { key: 'key', label: '티켓 번호' },
  { key: 'summary', label: '티켓 제목' },
  { key: 'created', label: '생성일' },
  { key: 'status', label: '진행상태' },
]

function issue(key, overrides = {}) {
  return { key, summary: `제목 ${key}`, created: '2026-09-10 10:00', status: '처리 중', type: '장애 문의', ...overrides }
}

function render(t, issues) {
  const previousWindow = globalThis.window
  globalThis.window = {
    matchMedia: () => ({ matches: true, addEventListener() {}, removeEventListener() {} }),
  }
  let view
  act(() => { view = TestRenderer.create(React.createElement(SlaIssueActivityTable, { issues })) })
  t.after(() => {
    act(() => view.unmount())
    if (previousWindow === undefined) delete globalThis.window
    else globalThis.window = previousWindow
  })
  return view
}

function keys(view) {
  return view.root.findByType('tbody').findAllByType('a').map((anchor) => anchor.children.filter((child) => typeof child === 'string').join(''))
}

function header(view, label) {
  return view.root.findByType('thead').findAllByType('th').find((cell) => cell.findByType('button').props['aria-label'].startsWith(`${label} `))
}

function clickHeader(view, label) {
  act(() => header(view, label).findByType('button').props.onClick())
}

function clickPage(view, number) {
  const button = view.root.findAllByType('button').find((candidate) => candidate.children.length === 1 && candidate.children[0] === String(number))
  assert.ok(button, `Missing page ${number}`)
  act(() => button.props.onClick())
}

for (const { key, label } of columns) {
  test(`${label} header toggles ascending and descending with accessible sort state`, (t) => {
    const issues = Object.freeze([
      Object.freeze(issue('TACEA-10', { summary: '다리', created: '2026-09-10 11:00', status: '결과 대기 중' })),
      Object.freeze(issue('TACEA-2', { summary: '나무', created: '2026-09-10 12:00', status: '할 일' })),
      Object.freeze(issue('TACEA-100', { summary: '가방', created: '2026-08-31 09:00', status: '처리 중' })),
    ])
    const expected = {
      key: ['TACEA-2', 'TACEA-10', 'TACEA-100'],
      summary: ['TACEA-100', 'TACEA-2', 'TACEA-10'],
      created: ['TACEA-100', 'TACEA-10', 'TACEA-2'],
      status: ['TACEA-10', 'TACEA-100', 'TACEA-2'],
    }
    const view = render(t, issues)
    assert.deepEqual(keys(view), ['TACEA-10', 'TACEA-2', 'TACEA-100'])
    const headers = view.root.findByType('thead').findAllByType('th')
    assert.equal(headers.length, 4)
    assert.ok(headers.every((cell) => cell.props.scope === 'col' && cell.props['aria-sort'] === 'none'))
    assert.equal(header(view, label).findByType('button').props.type, 'button')
    assert.equal(header(view, label).findByType('button').props['aria-label'], `${label} 오름차순 정렬`)
    clickHeader(view, label)
    assert.deepEqual(keys(view), expected[key])
    assert.equal(header(view, label).props['aria-sort'], 'ascending')
    assert.equal(header(view, label).findByType('button').props['aria-label'], `${label} 내림차순 정렬`)
    clickHeader(view, label)
    assert.deepEqual(keys(view), [...expected[key]].reverse())
    assert.equal(header(view, label).props['aria-sort'], 'descending')
    assert.equal(header(view, label).findByType('button').props['aria-label'], `${label} 오름차순 정렬`)
    clickHeader(view, label)
    assert.equal(header(view, label).props['aria-sort'], 'ascending')
    const next = columns.find((column) => column.key !== key)
    clickHeader(view, next.label)
    assert.deepEqual(keys(view), expected[next.key])
    assert.equal(header(view, next.label).props['aria-sort'], 'ascending')
    assert.equal(header(view, label).props['aria-sort'], 'none')
    assert.deepEqual(issues.map((entry) => entry.key), ['TACEA-10', 'TACEA-2', 'TACEA-100'])
  })
}

test('empty fields stay last in either direction and equal values retain their input order', (t) => {
  const issues = [
    issue('TACEA-20', { summary: '같은 제목', created: '2026-09-09 12:00', status: '처리 중' }),
    issue('TACEA-3', { summary: ' ', created: '', status: ' ' }),
    issue('TACEA-2', { summary: '같은 제목', created: '2026-09-09 12:00', status: '처리 중' }),
    issue('TACEA-1', { summary: '가장 먼저', created: '2026-08-31 12:00', status: '결과 대기 중' }),
  ]
  const view = render(t, issues)
  for (const { label } of columns.filter((column) => column.key !== 'key')) {
    clickHeader(view, label)
    assert.deepEqual(keys(view), ['TACEA-1', 'TACEA-20', 'TACEA-2', 'TACEA-3'])
    clickHeader(view, label)
    assert.deepEqual(keys(view), ['TACEA-20', 'TACEA-2', 'TACEA-1', 'TACEA-3'])
  }
  act(() => view.update(React.createElement(SlaIssueActivityTable, {
    issues: [issue('TACEA-2'), issue(' '), issue('tacea-2'), issue('TACEA-1')],
  })))
  clickHeader(view, '티켓 번호')
  assert.deepEqual(keys(view), ['TACEA-1', 'TACEA-2', 'tacea-2', ' '])
  clickHeader(view, '티켓 번호')
  assert.deepEqual(keys(view), ['TACEA-2', 'tacea-2', 'TACEA-1', ' '])
})

test('sorting applies before pagination and resets the visible page on each sort change', (t) => {
  const issues = Object.freeze(Array.from({ length: 61 }, (_, index) => Object.freeze(issue(`TACEA-${61 - index}`))))
  const view = render(t, issues)
  assert.equal(keys(view).length, 50)
  clickPage(view, 2)
  assert.deepEqual(keys(view), Array.from({ length: 11 }, (_, index) => `TACEA-${11 - index}`))
  clickHeader(view, '티켓 번호')
  assert.deepEqual(keys(view), Array.from({ length: 50 }, (_, index) => `TACEA-${index + 1}`))
  clickPage(view, 2)
  assert.deepEqual(keys(view), Array.from({ length: 11 }, (_, index) => `TACEA-${index + 51}`))
  clickHeader(view, '티켓 번호')
  assert.deepEqual(keys(view), Array.from({ length: 50 }, (_, index) => `TACEA-${61 - index}`))
  assert.equal(issues[0].key, 'TACEA-61')
  assert.equal(issues[60].key, 'TACEA-1')
})

test('comment collapse follows its ticket and refreshed props retain the selected sort', (t) => {
  const issues = [issue('TACEA-10'), issue('TACEA-2')]
  const view = render(t, issues)
  const toggle = (key) => view.root.findAllByType('button').find((button) => button.props['aria-label']?.startsWith(`${key} 댓글 `))
  assert.equal(toggle('TACEA-2').props['aria-expanded'], true)
  act(() => toggle('TACEA-2').props.onClick())
  assert.equal(toggle('TACEA-2').props['aria-expanded'], false)
  clickHeader(view, '티켓 번호')
  assert.deepEqual(keys(view), ['TACEA-2', 'TACEA-10'])
  assert.equal(toggle('TACEA-2').props['aria-expanded'], false)
  assert.equal(toggle('TACEA-10').props['aria-expanded'], true)
  act(() => view.update(React.createElement(SlaIssueActivityTable, {
    issues: [issues[0], issue('TACEA-1'), { ...issues[1], summary: '수정된 제목' }],
  })))
  assert.deepEqual(keys(view), ['TACEA-1', 'TACEA-2', 'TACEA-10'])
  assert.equal(header(view, '티켓 번호').props['aria-sort'], 'ascending')
  assert.equal(toggle('TACEA-2').props['aria-expanded'], false)
  assert.equal(toggle('TACEA-1').props['aria-expanded'], true)
  assert.equal(view.root.findAllByType('h3').length, 2)
})

test('empty and single-ticket lists keep working with either sorting direction', (t) => {
  const view = render(t, [])
  for (const { label } of columns) {
    clickHeader(view, label)
    clickHeader(view, label)
    assert.deepEqual(keys(view), [])
  }
  act(() => view.update(React.createElement(SlaIssueActivityTable, { issues: [issue('TACEA-2')] })))
  clickHeader(view, '티켓 번호')
  clickHeader(view, '티켓 번호')
  assert.deepEqual(keys(view), ['TACEA-2'])
})
