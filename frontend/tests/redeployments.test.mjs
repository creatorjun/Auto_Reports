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
let pageReport
const setCurrentReport = () => {}
function load(relative) {
  if (relative === 'presentation/context/JiraContext') return { useJira: () => ({ jiraBrowse: 'https://jira.example/browse' }) }
  if (relative === 'presentation/hooks/useRedeployments') return { useRedeployments: () => ({ data: pageReport }), useRefreshRedeployments: () => ({ mutate() {} }) }
  if (relative === 'presentation/state/reportStore') return { useReportStore: (select) => select({ setCurrentReport }) }
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
const { default: RedeploymentPage } = load('presentation/pages/RedeploymentPage')
const ticket = (key, overrides = {}) => ({ key, summary: '[고객사] 재배포', issue_type: '개선', status: '결과 대기 중', closed: false, created_at: '2025-12-01T09:00:00+09:00', resolved_at: null, completion_month: null, cause: '개발오류', reason: '파일 누락', repatch_count: 2, customer: '고객사', partners: [], assignee: '담당자', reporter: '보고자', ...overrides })

function renderPage(t, tickets) {
  pageReport = { period_start: '2026-01-01', generated_at: '2026-03-10T00:00:00Z', warnings: [], tickets }
  let view
  act(() => { view = TestRenderer.create(React.createElement(RedeploymentPage)) })
  t.after(() => act(() => view.unmount()))
  const text = (node) => typeof node === 'string' ? node : (node.children ?? []).map(text).join('')
  const button = (label) => {
    const result = view.root.findAllByType('button').find((node) => text(node) === label)
    assert.ok(result, `Missing button: ${label}`)
    return result
  }
  const column = (label, mobile = false) => view.root.findByProps({ 'aria-label': `${label} 컬럼 검색${mobile ? ' 모바일' : ''}` })
  const change = (node, value) => act(() => node.props.onChange({ target: { value } }))
  const click = (node) => act(() => node.props.onClick())
  const listed = () => view.root.findByType(Tickets).props.tickets.map((item) => item.key)
  const refresh = (tickets) => {
    pageReport = { ...pageReport, tickets }
    act(() => view.update(React.createElement(RedeploymentPage)))
  }
  return { view, text, button, column, change, click, listed, refresh }
}

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

test('month filtering matches the chart cohort and combines with cause and search', () => {
  const items = [
    ticket('TACEA-1', { closed: true, completion_month: '2026-01', resolved_at: '2026-02-09T10:00:00+09:00' }),
    ticket('TACEA-2', { completion_month: '2026-01' }),
    ticket('TACEA-3', { closed: true, completion_month: '2025-01' }),
    ticket('TACEA-4', { closed: true }),
    ticket('TACEA-5', { closed: true, completion_month: '2026-01', cause: '환경변경' }),
  ]
  const copy = structuredClone(items)
  assert.deepEqual(filterRedeployments(items, 'all', '', '', '2026-01').map((item) => item.key), ['TACEA-5', 'TACEA-1'])
  assert.deepEqual(filterRedeployments(items, 'all', '개발오류', '파일', '2026-01').map((item) => item.key), ['TACEA-1'])
  assert.equal(filterRedeployments(items, 'all', '', '', '2026-02').length, 0)
  assert.equal(filterRedeployments(items, 'all', '', '', '').length, 5)
  assert.deepEqual(items, copy)
})

test('column searches normalize text and intersect with scope, cause, month and global search without mutating tickets', () => {
  const target = { closed: true, completion_month: '2026-01', summary: '서울 ABC 재배포', issue_type: '서비스 요청', reason: 'FILE 누락' }
  const items = [
    ticket('TACEA-1', target),
    ticket('TACEA-2', { ...target, summary: '부산 ABC 재배포' }),
    ticket('TACEA-3', { ...target, status: 'Closed' }),
    ticket('TACEA-4', { ...target, cause: '환경변경' }),
    ticket('TACEA-5', { ...target, reason: '설정 누락' }),
    ticket('TACEA-6', { ...target, completion_month: '2026-02' }),
    ticket('TACEA-7', { ...target, closed: false }),
    ticket('TACEA-8', { ...target, issue_type: '개선' }),
    ticket('TACEA-9', { ...target, repatch_count: 3 }),
  ]
  const copy = structuredClone(items)
  const columns = { ticket: ' 서울 ａｂｃ ', issue_type: '서비스요청', status: '결과 대기', cause: 'ｆｉｌｅ', repatch_count: '２회', completion_month: '２０２６-０１' }
  assert.deepEqual(filterRedeployments(items, 'closed', '개발오류', ' ＦＩＬＥ ', '2026-01', columns).map((item) => item.key), ['TACEA-1'])
  assert.deepEqual(items, copy)
  assert.equal(filterRedeployments(items, 'all', '', '', '', { ticket: ' \t ', status: '\n' }).length, items.length)
})

test('column searches use visible values for customer, reason, missing fields, zero counts and active completion months', () => {
  const items = [
    ticket('TACEA-1', { customer: '서울', cause: '환경변경', reason: '인증서 갱신', repatch_count: 0 }),
    ticket('TACEA-2', { closed: true, customer: null, cause: null, reason: null, repatch_count: null }),
    ticket('TACEA-3', { closed: true, completion_month: '2026-01', repatch_count: 10 }),
  ]
  const keys = (columns) => filterRedeployments(items, 'all', '', '', '', columns).map((item) => item.key)
  for (const [column, query, expected] of [
    ['ticket', '서울', ['TACEA-1']], ['ticket', '고객사 미입력', ['TACEA-2']],
    ['cause', '인증서', ['TACEA-1']], ['cause', '원인 미입력', ['TACEA-2']], ['cause', '상세 사유 미입력', ['TACEA-2']],
    ['repatch_count', '미입력', ['TACEA-2']], ['repatch_count', '0회', ['TACEA-1', 'TACEA-3']],
    ['completion_month', '미입력', ['TACEA-2']], ['completion_month', '진행 중', ['TACEA-1']],
    ['completion_month', '2026-01', ['TACEA-3']],
  ]) assert.deepEqual(keys({ [column]: query }), expected, `${column}: ${query}`)
  assert.deepEqual(keys({ ticket: '서울', repatch_count: '0회' }), ['TACEA-1'])
})

test('desktop and mobile column searches share state, compose together and reset when only text filters are active', (t) => {
  const page = renderPage(t, [ticket('TACEA-1', { summary: '서울 재배포', status: '검토 중' }), ticket('TACEA-2', { summary: '부산 재배포' })])
  const labels = ['번호 / 제목', '유형', '현재 상태', '재배포 원인', '재패치', '완료 월']
  assert.equal(page.button('초기화').props.disabled, true)
  assert.equal(page.view.root.findByType('thead').findAllByType('input').length, labels.length)
  for (const label of labels) {
    assert.equal(page.column(label).props.value, '')
    assert.equal(page.column(label, true).props.value, '')
  }
  page.change(page.column('번호 / 제목', true), '서울')
  assert.equal(page.column('번호 / 제목').props.value, '서울')
  assert.equal(page.button('초기화').props.disabled, false)
  assert.deepEqual(page.listed(), ['TACEA-1'])
  for (const [label, query] of [['유형', '개선'], ['재배포 원인', '개발오류'], ['재패치', '2회'], ['완료 월', '진행 중']]) {
    page.change(page.column(label, true), query)
    assert.equal(page.column(label).props.value, query)
  }
  assert.deepEqual(page.listed(), ['TACEA-1'])
  page.change(page.column('현재 상태'), '결과')
  assert.equal(page.column('현재 상태', true).props.value, '결과')
  assert.deepEqual(page.listed(), [])
  assert.ok(page.text(page.view.root.findByType('tbody')).includes('조건에 맞는 재배포 티켓이 없습니다.'))
  page.click(page.button('초기화'))
  for (const label of labels) for (const mobile of [false, true]) assert.equal(page.column(label, mobile).props.value, '')
  assert.deepEqual(page.listed(), ['TACEA-2', 'TACEA-1'])
  assert.equal(page.button('초기화').props.disabled, true)
  page.change(page.view.root.findByProps({ type: 'search' }), '부산')
  assert.equal(page.button('초기화').props.disabled, false)
  page.click(page.button('초기화'))
  assert.equal(page.view.root.findByProps({ type: 'search' }).props.value, '')
  assert.deepEqual(page.listed(), ['TACEA-2', 'TACEA-1'])
})

test('reset clears month, cause, global and column searches while restoring the chosen scope', (t) => {
  const page = renderPage(t, [
    ticket('TACEA-1', { summary: '서울 재배포', closed: true, completion_month: '2026-01' }),
    ticket('TACEA-2', { summary: '부산 재배포', cause: '환경변경' }),
    ticket('TACEA-3', { summary: '서울 재배포' }),
  ])
  page.click(page.button('진행 중'))
  page.click(page.view.root.findAllByType('button').find((node) => page.text(node).startsWith('개발오류')))
  page.change(page.view.root.findByProps({ type: 'search' }), '서울')
  page.change(page.column('현재 상태', true), '결과')
  const month = () => page.view.root.findByProps({ 'aria-label': '2026-01 재배포 완료 1건' })
  page.click(month())
  assert.deepEqual(page.listed(), ['TACEA-1'])
  assert.equal(month().props['aria-pressed'], true)
  page.click(page.button('초기화'))
  assert.equal(month().props['aria-pressed'], false)
  assert.equal(page.button('진행 중').props['aria-pressed'], true)
  assert.equal(page.view.root.findByProps({ type: 'search' }).props.value, '')
  assert.equal(page.column('현재 상태').props.value, '')
  assert.deepEqual(page.listed(), ['TACEA-3', 'TACEA-2'])
  assert.equal(page.button('초기화').props.disabled, true)
})

test('column changes and reset return to page one while refresh preserves pagination and active searches', (t) => {
  const rows = Array.from({ length: 52 }, (_, index) => ticket(`TACEA-${index + 1}`, { summary: `${index % 2 ? '서울' : '부산'} 재배포` }))
  const page = renderPage(t, rows)
  page.click(page.button('다음'))
  assert.equal(page.button('이전').props.disabled, false)
  page.refresh(structuredClone(rows))
  assert.equal(page.button('이전').props.disabled, false)
  assert.ok(page.text(page.view.root).includes('2 / 3'))
  page.change(page.column('번호 / 제목'), '서울')
  assert.equal(page.listed().length, 26)
  assert.equal(page.button('이전').props.disabled, true)
  page.click(page.button('다음'))
  page.click(page.button('초기화'))
  assert.equal(page.listed().length, 52)
  assert.equal(page.button('이전').props.disabled, true)
  page.change(page.column('번호 / 제목', true), '서울')
  page.change(page.view.root.findByProps({ type: 'search' }), '갱신')
  assert.deepEqual(page.listed(), [])
  page.refresh([...rows, ticket('TACEA-53', { summary: '서울 갱신 재배포' }), ticket('TACEA-54', { summary: '부산 갱신 재배포' })])
  assert.deepEqual(page.listed(), ['TACEA-53'])
  assert.equal(page.column('번호 / 제목').props.value, '서울')
  assert.equal(page.column('번호 / 제목', true).props.value, '서울')
  assert.equal(page.view.root.findByProps({ type: 'search' }).props.value, '갱신')
})

test('month selection resets pagination, composes filters and toggles back to the previous scope', (t) => {
  pageReport = { period_start: '2026-01-01', generated_at: '2026-03-10T00:00:00Z', warnings: [], tickets: [
    ...Array.from({ length: 26 }, (_, index) => ticket(`TACEA-${index + 1}`, { closed: true, completion_month: '2026-01', cause: index % 2 ? '개발오류' : '환경변경', summary: index === 0 ? '검색 대상' : '재배포' })),
    ticket('TACEA-27', { closed: true, completion_month: '2026-02' }),
    ticket('TACEA-28', { completion_month: '2026-01' }),
  ] }
  let rendered
  act(() => { rendered = TestRenderer.create(React.createElement(RedeploymentPage)) })
  t.after(() => act(() => rendered.unmount()))
  const text = (node) => typeof node === 'string' ? node : (node.children ?? []).map(text).join('')
  const button = (label) => rendered.root.findAllByType('button').find((item) => text(item) === label)
  const monthButton = (month, count) => rendered.root.findByProps({ 'aria-label': `${month} 재배포 완료 ${count}건` })
  const listed = () => rendered.root.findByType(Tickets).props.tickets
  act(() => button('다음').props.onClick())
  act(() => monthButton('2026-01', 26).props.onClick())
  assert.equal(monthButton('2026-01', 26).props['aria-pressed'], true)
  assert.equal(listed().length, 26)
  assert.equal(button('이전').props.disabled, true)
  act(() => rendered.root.findAllByType('button').find((item) => text(item).startsWith('환경변경')).props.onClick())
  assert.equal(listed().length, 13)
  act(() => rendered.root.findByProps({ type: 'search' }).props.onChange({ target: { value: '검색 대상' } }))
  assert.deepEqual(listed().map((item) => item.key), ['TACEA-1'])
  act(() => rendered.root.findByProps({ type: 'search' }).props.onChange({ target: { value: '' } }))
  act(() => button('진행 중').props.onClick())
  assert.equal(monthButton('2026-01', 26).props['aria-pressed'], false)
  assert.deepEqual(listed().map((item) => item.key), ['TACEA-28'])
  act(() => monthButton('2026-02', 1).props.onClick())
  assert.deepEqual(listed().map((item) => item.key), ['TACEA-27'])
  act(() => monthButton('2026-02', 1).props.onClick())
  assert.deepEqual(listed().map((item) => item.key), ['TACEA-28'])
  act(() => monthButton('2026-03', 0).props.onClick())
  assert.equal(listed().length, 0)
  act(() => button('2026-03 · 해제 ×').props.onClick())
  assert.deepEqual(listed().map((item) => item.key), ['TACEA-28'])
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
