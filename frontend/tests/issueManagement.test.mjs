// frontend/tests/issueManagement.test.mjs
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
  const filename = [base, `${base}.ts`, `${base}.tsx`].find((file) => fs.existsSync(file) && fs.statSync(file).isFile())
  if (modules.has(filename)) return modules.get(filename).exports
  const module = { exports: {} }
  modules.set(filename, module)
  const code = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
    fileName: filename,
  }).outputText
  new Function('require', 'module', 'exports', code)((dependency) => {
    if (dependency === '@/presentation/context/JiraContext') return { useJira: () => ({ jiraBase: 'https://jira.example.test' }) }
    if (dependency.startsWith('@/')) return loadSource(dependency.slice(2))
    if (dependency.startsWith('.')) return loadSource(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)))
    return require(dependency)
  }, module, module.exports)
  return module.exports
}

const { filterManagedIssues } = loadSource('domain/IssueManagement')
const { filterIssuesByColumns } = loadSource('domain/IssueColumnSearch')
const { default: RecentIssuesWidget } = loadSource('presentation/components/charts/RecentIssuesWidget')
const { TABLE_PAGE_SIZE } = loadSource('presentation/config/constants')
const { normalizeSearchText } = loadSource('domain/Search')
const { DashboardExportProvider } = loadSource('presentation/context/DashboardExportContext')

test('search normalization trims both operands without removing word spacing', () => {
  assert.equal(normalizeSearchText(' \tＳＥＯＵＬ 교통공사\n '), 'seoul 교통공사')
  assert.equal(normalizeSearchText(' \t\n '), '')
  const rows = [issue('T-1', { summary: ' \t[서울교통공사] 확인\n ' }), issue('T-2', { summary: '부산 확인' })]
  assert.deepEqual(filterIssuesByColumns(rows, { summary: ' \t서울교통공사\n ' }).map((row) => row.key), ['T-1'])
  assert.deepEqual(filterIssuesByColumns(rows, { summary: ' \t\n ' }), rows)
})

function issue(key, values = {}) {
  return { key, summary: key, type: '인시던트', status: 'Closed', created: '2026-01-01 09:00', stage_index: 99, elapsed_days: 1, reporter: '', tac_team: '', ...values }
}

test('all statuses and all years are included by default and filters intersect immediately', () => {
  const rows = [issue('T-1'), issue('T-2', { status: '처리 중', created: '2026-09-01 09:00' }), issue('T-3', { type: '케이스', created: '2025-01-01 09:00' })]
  assert.deepEqual(filterManagedIssues(rows, null, null, null, null), rows)
  assert.deepEqual(filterManagedIssues(rows, new Set(), null, null, null), [])
  assert.deepEqual(filterManagedIssues(rows, null, new Set(), null, null), [])
  assert.deepEqual(filterManagedIssues(rows, new Set(['인시던트']), new Set(['Closed']), 'h1', 2026).map((row) => row.key), ['T-1'])
  assert.deepEqual(filterManagedIssues(rows, null, null, 'h1', null).map((row) => row.key), ['T-1', 'T-3'])
  assert.deepEqual(filterManagedIssues(rows, null, null, 'h2', 2026).map((row) => row.key), ['T-2'])
})

function textOf(node) {
  return typeof node === 'string' || typeof node === 'number' ? String(node) : node.children.map(textOf).join('')
}

test('live updates preserve page and sorting while filter changes reset the page', (t) => {
  let rows = Array.from({ length: TABLE_PAGE_SIZE * 2 + 1 }, (_, index) => issue(`T-${String(index).padStart(3, '0')}`))
  const render = (key) => React.createElement(RecentIssuesWidget, { title: '전체 이슈 현황', paginationResetKey: key, details: rows, elapsedDaysThreshold: null, elapsedDaysComparison: 'gte' })
  let view
  act(() => { view = TestRenderer.create(render('all')) })
  t.after(() => act(() => view.unmount()))
  const header = () => view.root.findByType('thead').findAllByType('th')[0]
  act(() => header().props.onClick())
  const pageTwo = view.root.findAllByType('button').find((button) => textOf(button) === '2')
  act(() => pageTwo.props.onClick({ stopPropagation() {} }))
  const firstKey = () => textOf(view.root.findByType('tbody').findAllByType('tr')[0].findAllByType('td')[0])
  assert.equal(firstKey(), rows[TABLE_PAGE_SIZE].key)
  rows = [...rows.map((row) => ({ ...row, status: '처리 중' })), issue('T-999')]
  act(() => view.update(render('all')))
  assert.equal(firstKey(), rows[TABLE_PAGE_SIZE].key)
  act(() => view.update(render('filtered')))
  assert.equal(firstKey(), rows[0].key)
  assert.ok(textOf(header()).includes('↑'))
  assert.ok(JSON.stringify(view.toJSON()).includes('전체 이슈 현황'))
})

test('thousands of cached issues use bounded pagination and can reach the final page', (t) => {
  const rows = Array.from({ length: 3241 }, (_, index) => issue(`T-${index}`))
  let view
  act(() => { view = TestRenderer.create(React.createElement(RecentIssuesWidget, { paginationResetKey: 'all', details: rows, elapsedDaysThreshold: null, elapsedDaysComparison: 'gte' })) })
  t.after(() => act(() => view.unmount()))
  const numbered = () => view.root.findAllByType('button').filter((button) => /^\d+$/.test(textOf(button)))
  assert.ok(numbered().length <= 7)
  const lastPage = numbered().find((button) => textOf(button) === '65')
  act(() => lastPage.props.onClick({ stopPropagation() {} }))
  assert.equal(view.root.findByType('tbody').findAllByType('tr').length, 41)
  assert.equal(view.root.findByProps({ 'aria-label': '다음 페이지' }).props.disabled, true)
  assert.ok(numbered().length <= 7)
})

test('column searches match full text, combine with AND and ignore case and outer spaces', () => {
  const rows = [issue('T-1', { summary: '[서울교통공사] ABC 확인', reporter: '홍길동', tac_team: '지원팀', tac_assignee: '담당자', elapsed_days: 30 }), issue('T-2', { summary: '[서울시청] 문의', status: '처리 중' }), issue('T-3', { summary: '[부산교통공사] 문의' })]
  assert.deepEqual(filterIssuesByColumns(rows, { summary: '서울' }).map((row) => row.key), ['T-1', 'T-2'])
  assert.deepEqual(filterIssuesByColumns(rows, { summary: ' abc ', reporter: '홍', tac: '지원', tac_assignee: '담당', elapsed: '30일', status: 'closed', key: 't-1' }).map((row) => row.key), ['T-1'])
  assert.deepEqual(filterIssuesByColumns(rows, { summary: '서울', status: '처리' }).map((row) => row.key), ['T-2'])
  assert.deepEqual(filterIssuesByColumns(rows, { elapsed: '2026-01' }), rows)
  assert.deepEqual(filterIssuesByColumns(rows, { summary: '   ' }), rows)
})

test('typing filters every cached page immediately, keeps inputs for zero results and survives updates', (t) => {
  let rows = Array.from({ length: 110 }, (_, index) => issue(`T-${index}`, { summary: index >= 100 ? '[서울교통공사] 문의' : '[부산] 문의' }))
  const render = () => React.createElement(RecentIssuesWidget, { paginationResetKey: 'all', details: rows, elapsedDaysThreshold: null, elapsedDaysComparison: 'gte' })
  let view
  act(() => { view = TestRenderer.create(render()) })
  t.after(() => act(() => view.unmount()))
  const input = (label) => view.root.findByProps({ 'aria-label': `${label} 컬럼 검색` })
  const type = (label, value) => act(() => input(label).props.onChange({ target: { value } }))
  assert.equal(view.root.findByType('thead').findAllByType('input').length, 7)
  let stopped = false
  act(() => input('제목').props.onClick({ stopPropagation() { stopped = true } }))
  assert.ok(stopped)
  stopped = false
  act(() => input('제목').props.onKeyDown({ stopPropagation() { stopped = true } }))
  assert.ok(stopped)
  assert.ok(!textOf(view.root.findByType('thead')).includes('↑'))
  assert.ok(!textOf(view.root.findByType('thead')).includes('↓'))
  type('제목', '서울')
  assert.equal(view.root.findByType('tbody').findAllByType('tr').length, 10)
  assert.ok(textOf(view.root.findByType('tbody')).includes('T-100'))
  type('진행 상태', '없음')
  assert.ok(textOf(view.root.findByType('tbody')).includes('검색 조건에 맞는 이슈가 없습니다.'))
  assert.equal(input('제목').props.value, '서울')
  type('진행 상태', '')
  rows = [...rows, issue('T-new', { summary: '[서울시청] 문의' })]
  act(() => view.update(render()))
  assert.equal(view.root.findByType('tbody').findAllByType('tr').length, 11)
  assert.equal(input('제목').props.value, '서울')
  type('제목', '')
  assert.equal(view.root.findByType('tbody').findAllByType('tr').length, TABLE_PAGE_SIZE)
})

for (const title of ['최근 이슈 현황', '전체 이슈 현황']) {
  test(`${title} exposes all column searches by default on desktop and mobile`, (t) => {
    const rows = [issue('T-1', { summary: '[서울교통공사] 문의' }), issue('T-2', { summary: '[부산] 문의' })]
    let view
    act(() => { view = TestRenderer.create(React.createElement(RecentIssuesWidget, {
      title, details: rows, elapsedDaysThreshold: null, elapsedDaysComparison: 'gte',
    })) })
    t.after(() => act(() => view.unmount()))
    const labels = ['이슈', '제목', '진행 상태', '보고자', '담당자', 'TAC 담당자', '생성일 (경과)']
    const input = (label, mobile = false) => view.root.findByProps({ 'aria-label': `${label} 컬럼 검색${mobile ? ' 모바일' : ''}` })
    for (const label of labels) {
      assert.equal(input(label).props.type, 'text')
      assert.equal(input(label, true).props.type, 'text')
      assert.equal(input(label).props.value, '')
      assert.equal(input(label, true).props.value, '')
    }
    assert.equal(view.root.findByType('thead').findAllByType('input').length, labels.length)
    assert.equal(view.root.findByProps({ 'data-pdf-mobile': '' }).findAllByType('input').length, labels.length)
    act(() => input('제목', true).props.onChange({ target: { value: '서울' } }))
    assert.equal(input('제목').props.value, '서울')
    assert.deepEqual(tableKeys(view.root), ['T-1'])
    assert.ok(textOf(view.root.findByProps({ 'data-pdf-mobile': '' })).includes('T-1'))
    assert.ok(!textOf(view.root.findByProps({ 'data-pdf-mobile': '' })).includes('T-2'))
    act(() => input('제목').props.onChange({ target: { value: '' } }))
    assert.equal(input('제목', true).props.value, '')
    assert.deepEqual(tableKeys(view.root), ['T-1', 'T-2'])
  })
}

function tableKeys(root) {
  return root.findByType('tbody').findAllByType('tr').filter((row) => row.findAllByType('td').length > 1).map((row) => textOf(row.findAllByType('td')[0]))
}

function click(node) {
  act(() => node.props.onClick({ stopPropagation() {} }))
}

function pageButton(root, page) {
  const button = root.findAllByType('button').find((node) => textOf(node) === String(page))
  assert.ok(button, `Missing page ${page}`)
  return button
}

test('column filters reset pagination, retain sorting and widths, and retain their page on refresh', (t) => {
  const original = Object.freeze(Array.from({ length: 140 }, (_, index) => Object.freeze(issue(`T-${String(index).padStart(3, '0')}`, {
    summary: index >= 60 ? '[서울교통공사] 문의' : '[부산] 문의',
    status: index % 2 ? '처리 중' : 'Closed',
  }))))
  let rows = original
  const render = () => React.createElement(RecentIssuesWidget, {
    paginationResetKey: 'all', details: rows, elapsedDaysThreshold: null, elapsedDaysComparison: 'gte',
  })
  let view
  act(() => { view = TestRenderer.create(render(), { createNodeMock: (element) => element.type === 'table' ? { offsetWidth: 1000 } : null }) })
  t.after(() => act(() => view.unmount()))
  const header = () => view.root.findByType('thead').findAllByType('th')[0]
  click(header())
  click(header())
  const resize = view.root.findAllByProps({ title: '드래그하여 너비 조절' })[0]
  act(() => resize.props.onPointerDown({ preventDefault() {}, stopPropagation() {}, clientX: 100, pointerId: 1, target: { setPointerCapture() {} } }))
  act(() => resize.props.onPointerMove({ clientX: 110 }))
  act(() => resize.props.onPointerUp())
  const widths = () => view.root.findAllByType('col').map((column) => column.props.style.width)
  const resizedWidths = widths()
  assert.notEqual(resizedWidths[0], '10.00%')
  click(pageButton(view.root, 2))
  assert.equal(tableKeys(view.root)[0], 'T-089')
  const input = (label) => view.root.findByProps({ 'aria-label': `${label} 컬럼 검색` })
  act(() => input('제목').props.onChange({ target: { value: '서울' } }))
  assert.equal(tableKeys(view.root)[0], 'T-139')
  assert.equal(tableKeys(view.root).length, TABLE_PAGE_SIZE)
  assert.match(textOf(header()), /↓/)
  assert.deepEqual(widths(), resizedWidths)
  click(pageButton(view.root, 2))
  assert.equal(tableKeys(view.root)[0], 'T-089')
  rows = [...original, issue('T-140', { summary: '[서울시청] 문의', status: '처리 중' })]
  act(() => view.update(render()))
  assert.equal(tableKeys(view.root)[0], 'T-090')
  assert.equal(input('제목').props.value, '서울')
  assert.match(textOf(header()), /↓/)
  assert.deepEqual(widths(), resizedWidths)
  act(() => input('진행 상태').props.onChange({ target: { value: '처리' } }))
  assert.deepEqual(tableKeys(view.root), ['T-140', ...Array.from({ length: 40 }, (_, index) => `T-${String(139 - index * 2).padStart(3, '0')}`)])
  assert.deepEqual(widths(), resizedWidths)
  assert.match(textOf(header()), /↓/)
  assert.deepEqual(original.map((row) => row.key), Array.from({ length: 140 }, (_, index) => `T-${String(index).padStart(3, '0')}`))
})

test('separate widget instances keep independent column search state', (t) => {
  const rows = [issue('T-1', { summary: '서울 문의' }), issue('T-2', { summary: '부산 문의', status: '처리 중' }), issue('T-3', { summary: '서울 확인' })]
  const props = { details: rows, elapsedDaysThreshold: null, elapsedDaysComparison: 'gte' }
  let view
  act(() => { view = TestRenderer.create(React.createElement('div', null,
    React.createElement(RecentIssuesWidget, { ...props, key: 'dashboard' }),
    React.createElement(RecentIssuesWidget, { ...props, key: 'management', title: '전체 이슈 현황' }),
  )) })
  t.after(() => act(() => view.unmount()))
  const widgets = () => view.root.findAllByType(RecentIssuesWidget)
  const input = (index, label) => widgets()[index].findByProps({ 'aria-label': `${label} 컬럼 검색` })
  act(() => input(0, '제목').props.onChange({ target: { value: '서울' } }))
  assert.deepEqual(tableKeys(widgets()[0]), ['T-1', 'T-3'])
  assert.deepEqual(tableKeys(widgets()[1]), ['T-1', 'T-2', 'T-3'])
  assert.equal(input(1, '제목').props.value, '')
  act(() => input(1, '진행 상태').props.onChange({ target: { value: '처리' } }))
  assert.deepEqual(tableKeys(widgets()[0]), ['T-1', 'T-3'])
  assert.deepEqual(tableKeys(widgets()[1]), ['T-2'])
  assert.equal(input(0, '진행 상태').props.value, '')
})

test('controlled PDF column filters include every match and omit all search and pagination controls', (t) => {
  const rows = Object.freeze(Array.from({ length: 150 }, (_, index) => Object.freeze(issue(`T-${String(index).padStart(3, '0')}`, {
    summary: index >= 20 ? '[서울교통공사] 문의' : '[부산] 문의',
    status: index % 2 ? '처리 중' : 'Closed',
  }))))
  let view
  act(() => { view = TestRenderer.create(React.createElement(DashboardExportProvider, null,
    React.createElement(RecentIssuesWidget, {
      details: rows, elapsedDaysThreshold: null, elapsedDaysComparison: 'gte',
      columnFilters: { summary: '서울', status: 'closed' },
    }),
  )) })
  t.after(() => act(() => view.unmount()))
  assert.deepEqual(tableKeys(view.root), Array.from({ length: 65 }, (_, index) => `T-${String(20 + index * 2).padStart(3, '0')}`))
  assert.equal(view.root.findAllByType('input').length, 0)
  assert.equal(view.root.findAllByType('button').length, 0)
  assert.equal(view.root.findAllByType('select').length, 0)
  assert.equal(view.root.findByType('table').props['data-pdf-table-layout'], 'recent')
  assert.equal(rows.length, 150)
})
