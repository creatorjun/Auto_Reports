// frontend/tests/recentIssueComments.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import * as ReactQuery from '@tanstack/react-query'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')
const modules = new Map()
const { QueryClient, QueryClientProvider } = ReactQuery

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
    if (dependency === '@tanstack/react-query') return ReactQuery
    if (dependency === '@/presentation/context/JiraContext') return { useJira: () => ({ jiraBase: 'https://jira.example.test' }) }
    if (dependency.startsWith('@/')) return loadSource(dependency.slice(2))
    if (dependency.startsWith('.')) return loadSource(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)))
    return require(dependency)
  }, module, module.exports)
  return module.exports
}

const { default: RecentIssuesWidget } = loadSource('presentation/components/charts/RecentIssuesWidget')
const { default: IssueDetailsPanel } = loadSource('presentation/components/common/IssueDetailsPanel')
const { ApplicationServicesProvider } = loadSource('presentation/context/ApplicationServicesContext')
const { DashboardExportProvider } = loadSource('presentation/context/DashboardExportContext')

function issue(key, summary = key) {
  return {
    key, summary, created: '2026-10-01 09:00', type: '인시던트', status: '처리 중',
    stage_index: 1, elapsed_days: 20, reporter: '보고자', tac_team: '담당자', tac_assignee: 'TAC 담당자',
  }
}

function comments(count, prefix = '') {
  return Array.from({ length: count }, (_, index) => ({
    id: `${prefix}${count - index}`, author: `작성자 ${count - index}`, body: `댓글 본문 ${prefix}${count - index}`,
    created: '2026-10-21 09:00', updated: '2026-10-21 09:00', images: [],
  }))
}

function snapshot(values, offset, limit) {
  return { comments: values.slice(offset, offset + limit), next_offset: offset + limit < values.length ? offset + limit : null }
}

function textOf(node) {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  return node.children.map(textOf).join('')
}

function layout(view, desktop = true) {
  return view.root.find((node) => typeof node.type === 'string' && Object.hasOwn(node.props, desktop ? 'data-pdf-desktop' : 'data-pdf-mobile'))
}

function button(root, label) {
  const result = root.findAllByType('button').find((node) => node.props['aria-label'] === label || textOf(node) === label)
  assert.ok(result, `Missing button: ${label}`)
  return result
}

function bubbleClick(node) {
  let stopped = false
  const event = { stopPropagation() { stopped = true }, preventDefault() {} }
  const path = []
  for (let current = node; current; current = current.parent) {
    if (typeof current.type === 'string' && typeof current.props.onClick === 'function') path.push(current.props.onClick)
  }
  act(() => {
    for (const handler of path) {
      handler(event)
      if (stopped) break
    }
  })
  return stopped
}

async function settled(condition) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (condition()) return
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 5)) })
  }
  assert.ok(condition(), 'Expected comment state to settle')
}

function commentBodies(root) {
  return root.findAllByType('li').map((entry) => entry.findAllByType('p').map(textOf).join(''))
}

function render(t, options = {}) {
  const { details = [issue('TAC-1'), issue('TAC-2')], desktop = true, exportMode = false, getComments, getDescription } = options
  const commentsReportId = Object.hasOwn(options, 'commentsReportId') ? options.commentsReportId : 42
  const calls = []
  const descriptionCalls = []
  const opened = []
  const listeners = new Set()
  const previousWindow = globalThis.window
  const media = {
    matches: desktop, media: '(min-width: 768px)',
    addEventListener(name, listener) { assert.equal(name, 'change'); listeners.add(listener) },
    removeEventListener(name, listener) { assert.equal(name, 'change'); listeners.delete(listener) },
    addListener(listener) { listeners.add(listener) },
    removeListener(listener) { listeners.delete(listener) },
  }
  globalThis.window = {
    matchMedia(query) { assert.equal(query, media.media); return media },
    open(...args) { opened.push(args) },
  }
  const services = { slaDashboard: {
    async getDescription(...args) {
      descriptionCalls.push(args)
      return getDescription ? getDescription(...args) : { body: `이슈 본문 ${args[0]}`, images: [] }
    },
    async getDescriptionImage() {
      return { read: async () => new ArrayBuffer(0), createObjectUrl: () => ({ url: 'blob:description-image', close() {} }) }
    },
    async getComments(...args) {
      calls.push(args)
      return getComments ? getComments(...args) : snapshot(comments(12, `${args[0]}-`), args[1], args[2])
    },
  } }
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  let view
  let currentProps = { details, commentsReportId, elapsedDaysThreshold: null, elapsedDaysComparison: 'gte' }
  const content = () => {
    const widget = React.createElement(RecentIssuesWidget, currentProps)
    return React.createElement(QueryClientProvider, { client },
      React.createElement(ApplicationServicesProvider, { services },
        exportMode ? React.createElement(DashboardExportProvider, null, widget) : widget))
  }
  act(() => { view = TestRenderer.create(content(), { createNodeMock: (node) => node.type === 'table' ? { offsetWidth: 1200 } : null }) })
  t.after(() => {
    act(() => view.unmount())
    client.clear()
    assert.equal(listeners.size, 0)
    if (previousWindow === undefined) delete globalThis.window
    else globalThis.window = previousWindow
  })
  return {
    view, calls, descriptionCalls, opened,
    update(props) { currentProps = { ...currentProps, ...props }; act(() => view.update(content())) },
    setDesktop(value) { act(() => { media.matches = value; listeners.forEach((listener) => listener({ matches: value })) }) },
  }
}

test('recent issues defer detail retrieval until icon expansion and show the body above the latest five with cumulative load-more', async (t) => {
  const values = comments(12)
  let release
  const { view, calls, descriptionCalls, opened } = render(t, { getComments: async (_, offset, limit) => {
    if (limit === 5) await new Promise((resolve) => { release = resolve })
    return snapshot(values, offset, limit)
  } })
  assert.deepEqual(calls, [])
  assert.deepEqual(descriptionCalls, [])
  assert.equal(view.root.findAllByType(IssueDetailsPanel).length, 0)
  const toggle = button(layout(view), 'TAC-1 상세 펼치기')
  assert.equal(toggle.props['aria-expanded'], false)
  assert.equal(textOf(toggle), '')
  assert.match(toggle.props.className, /rounded-lg p-2 text-apple-mid hover:bg-apple-gray/)
  assert.equal(toggle.findByType('svg').props.width, 18)
  assert.equal(layout(view).findAllByType('th').some((node) => textOf(node) === '댓글'), false)
  assert.equal(layout(view).findAllByType('th').at(-1).findByType('span').props.className, 'sr-only')
  assert.equal(textOf(layout(view).findAllByType('th').at(-1)), '상세')
  assert.equal(layout(view).findAllByType('col').at(-1).props.style.width, '5%')
  assert.equal(bubbleClick(toggle), true)
  assert.deepEqual(calls, [['TAC-1', 0, 5, 42]])
  assert.match(textOf(layout(view)), /댓글을 불러오는 중입니다/)
  assert.equal(view.root.findAllByType(IssueDetailsPanel).length, 1)
  assert.deepEqual(descriptionCalls.map(([key, reportId]) => [key, reportId]), [['TAC-1', 42]])
  await act(async () => { release() })
  await settled(() => commentBodies(layout(view)).length === 5)
  await settled(() => textOf(layout(view)).includes('이슈 본문 TAC-1'))
  assert.ok(textOf(layout(view)).indexOf('이슈 본문 TAC-1') < textOf(layout(view)).indexOf('최근 작성된 댓글'))
  assert.deepEqual(commentBodies(layout(view)), values.slice(0, 5).map((comment) => comment.body))
  for (const [limit, count] of [[10, 10], [15, 12]]) {
    bubbleClick(button(layout(view), `댓글 더보기 · 최신 ${limit}개`))
    await settled(() => commentBodies(layout(view)).length === count)
    assert.deepEqual(commentBodies(layout(view)), values.slice(0, limit).map((comment) => comment.body))
  }
  assert.deepEqual(calls, [5, 10, 15].map((limit) => ['TAC-1', 0, limit, 42]))
  assert.equal(layout(view).findAllByType('button').some((node) => textOf(node).startsWith('댓글 더보기')), false)
  assert.deepEqual(opened, [])
})

test('expanded state follows each issue through sorting and filtering and closes independently', async (t) => {
  const { view, calls } = render(t, { details: [issue('TAC-2', '두 번째'), issue('TAC-1', '첫 번째')] })
  bubbleClick(button(layout(view), 'TAC-2 상세 펼치기'))
  bubbleClick(button(layout(view), 'TAC-1 상세 펼치기'))
  await settled(() => commentBodies(layout(view)).length === 10)
  bubbleClick(layout(view).findByProps({ 'data-pdf-header': '이슈' }))
  const dataRows = () => layout(view).findByType('tbody').findAllByType('tr').filter((row) => row.findAllByType('td')[0]?.props.colSpan === undefined)
  assert.deepEqual(dataRows().map((row) => textOf(row.findAllByType('td')[0])), ['TAC-1', 'TAC-2'])
  assert.equal(button(layout(view), 'TAC-1 상세 접기').props['aria-expanded'], true)
  assert.equal(button(layout(view), 'TAC-2 상세 접기').props['aria-expanded'], true)
  bubbleClick(button(layout(view), 'TAC-1 상세 접기'))
  assert.equal(view.root.findAllByType(IssueDetailsPanel).length, 1)
  assert.equal(view.root.findByType(IssueDetailsPanel).props.issueKey, 'TAC-2')
  const search = layout(view).findByProps({ 'aria-label': '제목 컬럼 검색' })
  act(() => search.props.onChange({ target: { value: '첫 번째' } }))
  assert.equal(view.root.findAllByType(IssueDetailsPanel).length, 0)
  assert.equal(button(layout(view), 'TAC-1 상세 펼치기').props['aria-expanded'], false)
  act(() => search.props.onChange({ target: { value: '' } }))
  assert.equal(view.root.findByType(IssueDetailsPanel).props.issueKey, 'TAC-2')
  assert.equal(button(layout(view), 'TAC-2 상세 접기').props['aria-expanded'], true)
  assert.equal(calls.length, 2)
})

test('expanded details unmount off-page and return for the same ticket without another fetch', async (t) => {
  const { view, calls, descriptionCalls, opened } = render(t, { details: Array.from({ length: 51 }, (_, index) => issue(`TAC-${index + 1}`)) })
  bubbleClick(button(layout(view), 'TAC-1 상세 펼치기'))
  await settled(() => commentBodies(layout(view)).length === 5)
  bubbleClick(button(view.root, '다음 페이지'))
  assert.equal(view.root.findAllByType(IssueDetailsPanel).length, 0)
  assert.equal(button(layout(view), 'TAC-51 상세 펼치기').props['aria-expanded'], false)
  bubbleClick(button(view.root, '이전 페이지'))
  await settled(() => commentBodies(layout(view)).length === 5)
  assert.equal(view.root.findAllByType(IssueDetailsPanel).length, 1)
  assert.equal(button(layout(view), 'TAC-1 상세 접기').props['aria-expanded'], true)
  assert.equal(calls.length, 1)
  assert.equal(descriptionCalls.length, 1)
  assert.deepEqual(opened, [])
})

test('expanded details use the current report scope when the selected report changes', async (t) => {
  const { view, calls, descriptionCalls, update } = render(t, { getDescription: async (key, reportId) => ({ body: `${key} 보고서 ${reportId} 본문`, images: [] }) })
  bubbleClick(button(layout(view), 'TAC-1 상세 펼치기'))
  await settled(() => textOf(layout(view)).includes('TAC-1 보고서 42 본문'))
  update({ commentsReportId: 43 })
  await settled(() => textOf(layout(view)).includes('TAC-1 보고서 43 본문'))
  assert.ok(!textOf(layout(view)).includes('TAC-1 보고서 42 본문'))
  assert.deepEqual(descriptionCalls.map(([key, reportId]) => [key, reportId]), [['TAC-1', 42], ['TAC-1', 43]])
  assert.deepEqual(calls, [42, 43].map((reportId) => ['TAC-1', 0, 5, reportId]))
  assert.equal(view.root.findAllByType(IssueDetailsPanel).length, 1)
})

test('mobile expansion and breakpoint changes mount only one details panel without opening Jira', async (t) => {
  const { view, calls, descriptionCalls, opened, setDesktop } = render(t, { desktop: false })
  assert.equal(bubbleClick(button(layout(view, false), 'TAC-1 상세 펼치기')), true)
  await settled(() => commentBodies(layout(view, false)).length === 5)
  await settled(() => textOf(layout(view, false)).includes('이슈 본문 TAC-1'))
  assert.ok(textOf(layout(view, false)).indexOf('이슈 본문 TAC-1') < textOf(layout(view, false)).indexOf('최근 작성된 댓글'))
  assert.equal(layout(view).findAllByType(IssueDetailsPanel).length, 0)
  assert.equal(view.root.findAllByType(IssueDetailsPanel).length, 1)
  bubbleClick(button(layout(view, false), '댓글 더보기 · 최신 10개'))
  await settled(() => commentBodies(layout(view, false)).length === 10)
  assert.deepEqual(opened, [])
  setDesktop(true)
  await settled(() => commentBodies(layout(view)).length === 10)
  assert.equal(layout(view, false).findAllByType(IssueDetailsPanel).length, 0)
  assert.equal(view.root.findAllByType(IssueDetailsPanel).length, 1)
  assert.equal(button(layout(view), 'TAC-1 상세 접기').props['aria-expanded'], true)
  assert.equal(calls.length, 2)
  assert.deepEqual(descriptionCalls.map(([key, reportId]) => [key, reportId]), [['TAC-1', 42]])
  setDesktop(false)
  await settled(() => commentBodies(layout(view, false)).length === 10)
  assert.equal(view.root.findAllByType(IssueDetailsPanel).length, 1)
  assert.equal(calls.length, 2)
  assert.equal(bubbleClick(button(layout(view, false), 'TAC-1 상세 접기')), true)
  assert.equal(view.root.findAllByType(IssueDetailsPanel).length, 0)
  assert.deepEqual(opened, [])
})

test('comment errors expose retry and preserve the previous five comments after load-more fails', async (t) => {
  let fail = true
  const values = comments(11)
  const { view, calls, opened } = render(t, { desktop: false, getComments: async (_, offset, limit) => {
    if (fail) throw new Error('Jira temporarily unavailable')
    return snapshot(values, offset, limit)
  } })
  bubbleClick(button(layout(view, false), 'TAC-1 상세 펼치기'))
  await settled(() => textOf(layout(view, false)).includes('댓글을 불러오지 못했습니다.'))
  fail = false
  bubbleClick(button(layout(view, false), '다시 시도'))
  await settled(() => commentBodies(layout(view, false)).length === 5)
  fail = true
  bubbleClick(button(layout(view, false), '댓글 더보기 · 최신 10개'))
  await settled(() => textOf(layout(view, false)).includes('댓글을 더 불러오지 못했습니다.'))
  assert.deepEqual(commentBodies(layout(view, false)), values.slice(0, 5).map((comment) => comment.body))
  fail = false
  bubbleClick(button(layout(view, false), '다시 시도'))
  await settled(() => commentBodies(layout(view, false)).length === 10)
  assert.deepEqual(calls, [5, 5, 10, 10].map((limit) => ['TAC-1', 0, limit, 42]))
  assert.deepEqual(opened, [])
})

test('empty comment results keep the issue visible and omit load-more', async (t) => {
  const { view } = render(t, { getComments: async () => ({ comments: [], next_offset: null }) })
  bubbleClick(button(layout(view), 'TAC-1 상세 펼치기'))
  await settled(() => textOf(layout(view)).includes('작성된 댓글이 없습니다.'))
  assert.equal(button(layout(view), 'TAC-1 상세 접기').props['aria-expanded'], true)
  assert.equal(layout(view).findAllByType('button').some((node) => textOf(node).startsWith('댓글 더보기')), false)
})

for (const configuration of [{ exportMode: true }, { commentsReportId: undefined }]) {
  test(`${configuration.exportMode ? 'exported' : 'unscoped'} issue tables do not render detail controls or retrieve descriptions and comments`, (t) => {
    const { view, calls, descriptionCalls } = render(t, configuration)
    assert.equal(view.root.findAllByType(IssueDetailsPanel).length, 0)
    assert.equal(view.root.findAllByType('button').some((node) => /상세 (펼치기|접기)$/.test(node.props['aria-label'] ?? '')), false)
    assert.equal(layout(view).findAllByType('th').some((node) => textOf(node) === '댓글'), false)
    assert.deepEqual(calls, [])
    assert.deepEqual(descriptionCalls, [])
    assert.equal(layout(view).findAllByType('col').length, 8)
  })
}
