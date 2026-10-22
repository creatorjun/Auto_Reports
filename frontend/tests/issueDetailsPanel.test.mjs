// frontend/tests/issueDetailsPanel.test.mjs
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

function loadSource(relative, dependencies = {}, cache = modules) {
  const base = path.join(sourceRoot, relative)
  const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
  assert.ok(filename, `Missing source module: ${relative}`)
  if (cache.has(filename)) return cache.get(filename).exports
  const module = { exports: {} }
  cache.set(filename, module)
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
    fileName: filename,
  }).outputText
  new Function('require', 'module', 'exports', compiled)((dependency) => {
    if (Object.hasOwn(dependencies, dependency)) return dependencies[dependency]
    if (dependency === '@tanstack/react-query') return ReactQuery
    if (dependency.startsWith('@/')) return loadSource(dependency.slice(2), dependencies, cache)
    if (dependency.startsWith('.')) return loadSource(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)), dependencies, cache)
    return require(dependency)
  }, module, module.exports)
  return module.exports
}

const { default: IssueDetailsPanel } = loadSource('presentation/components/common/IssueDetailsPanel')
const { ApplicationServicesProvider } = loadSource('presentation/context/ApplicationServicesContext')

function textOf(node) {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  return node.children.map(textOf).join('')
}

async function settled(condition) {
  for (let index = 0; index < 100; index += 1) {
    if (condition()) return
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 5)) })
  }
  assert.ok(condition(), 'Expected detail state to settle')
}

function button(view, label) {
  const result = view.root.findAllByType('button').find((node) => textOf(node) === label)
  assert.ok(result, `Missing button: ${label}`)
  return result
}

function deferred() {
  let resolve
  let reject
  const promise = new Promise((done, fail) => { resolve = done; reject = fail })
  return { promise, resolve, reject }
}

function imageContent(url, closed, created = []) {
  return {
    read: async () => new ArrayBuffer(0),
    createObjectUrl() {
      created.push(url)
      return { url, close() { closed.push(url) } }
    },
  }
}

function render(t, overrides = {}, props = { issueKey: 'TAC-1', reportId: 42 }) {
  const calls = { descriptions: [], images: [], comments: [], managedDescriptions: [], managedImages: [], managedComments: [], managedCommentImages: [] }
  const slaDashboard = {
    async getDescription(...args) {
      calls.descriptions.push(args)
      return overrides.getDescription ? overrides.getDescription(...args) : { body: '보고서 본문', images: [] }
    },
    async getDescriptionImage(...args) {
      calls.images.push(args)
      assert.ok(overrides.getDescriptionImage, 'Unexpected image request')
      return overrides.getDescriptionImage(...args)
    },
    async getComments(...args) {
      calls.comments.push(args)
      return overrides.getComments ? overrides.getComments(...args) : {
        comments: [{ id: '1', author: '작성자', body: '최근 댓글', created: '2026-10-21', updated: '2026-10-21', images: [] }],
        next_offset: null,
      }
    },
  }
  const services = { slaDashboard, issueManagement: {
    async getDescription(...args) {
      calls.managedDescriptions.push(args)
      return overrides.managed?.getDescription ? overrides.managed.getDescription(...args) : { body: '전체 이슈 본문', images: [] }
    },
    async getDescriptionImage(...args) {
      calls.managedImages.push(args)
      assert.ok(overrides.managed?.getDescriptionImage, 'Unexpected managed description image request')
      return overrides.managed.getDescriptionImage(...args)
    },
    async getComments(...args) {
      calls.managedComments.push(args)
      return overrides.managed?.getComments ? overrides.managed.getComments(...args) : { comments: [], next_offset: null }
    },
    async getCommentImage(...args) {
      calls.managedCommentImages.push(args)
      assert.ok(overrides.managed?.getCommentImage, 'Unexpected managed comment image request')
      return overrides.managed.getCommentImage(...args)
    },
  } }
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  let view
  let mounted = true
  const content = (nextProps) => React.createElement(QueryClientProvider, { client },
    React.createElement(ApplicationServicesProvider, { services }, React.createElement(IssueDetailsPanel, nextProps)))
  act(() => { view = TestRenderer.create(content(props)) })
  const unmount = () => {
    if (!mounted) return
    act(() => view.unmount())
    mounted = false
  }
  t.after(() => { unmount(); client.clear() })
  return { view, calls, client, unmount, update: (nextProps) => act(() => view.update(content(nextProps))) }
}

test('description and image API encode identifiers, preserve report scope and forward cancellation', async () => {
  const calls = []
  const body = { body: '본문', images: [] }
  const blob = new Blob(['image'])
  const binary = imageContent('blob:api', [])
  const { slaDashboardApi } = loadSource('infrastructure/api/slaDashboardApi', {
    './client': { default: { async get(...args) { calls.push(args); return { data: args[1].responseType ? blob : body } } } },
    './binaryContent': { createBinaryContent(value) { assert.equal(value, blob); return binary } },
  }, new Map())
  const controller = new AbortController()
  assert.deepEqual(await slaDashboardApi.getDescription('TAC/42', 72, controller.signal), body)
  assert.equal(await slaDashboardApi.getDescriptionImage('TAC/42', 'image/2', 73, controller.signal), binary)
  assert.deepEqual(calls, [
    ['/sla-dashboard/issues/TAC%2F42/description', { params: { report_id: 72 }, signal: controller.signal }],
    ['/sla-dashboard/issues/TAC%2F42/description/images/image%2F2', { params: { report_id: 73 }, responseType: 'blob', signal: controller.signal }],
  ])
})

test('details render safe plain body before the latest comments', async (t) => {
  const body = '<img src=x onerror=alert(1)>\n두 번째 줄'
  const { view, calls } = render(t, { getDescription: async () => ({ body, images: [] }) })
  await settled(() => textOf(view.root).includes('최근 댓글') && textOf(view.root).includes(body))
  assert.deepEqual(view.root.findAllByType('h3').map(textOf), ['본문', '최근 작성된 댓글'])
  assert.equal(view.root.findAllByType('img').length, 0)
  assert.equal(view.root.findAll((node) => Object.hasOwn(node.props, 'dangerouslySetInnerHTML')).length, 0)
  assert.equal(view.root.findAllByType('p').some((node) => textOf(node) === body), true)
  assert.deepEqual(calls.comments, [['TAC-1', 0, 5, 42]])
  assert.deepEqual(calls.descriptions[0].slice(0, 2), ['TAC-1', 42])
  assert.equal(calls.descriptions[0][2].aborted, false)
})

test('comments load while body is pending and continue after a body failure and retry', async (t) => {
  const response = deferred()
  let attempts = 0
  const { view, calls } = render(t, {
    getDescription: async () => ++attempts === 1 ? response.promise : { body: '복구된 본문', images: [] },
  })
  await settled(() => textOf(view.root).includes('최근 댓글'))
  assert.match(textOf(view.root), /본문을 불러오는 중입니다/)
  await act(async () => response.reject(new Error('unavailable')))
  await settled(() => textOf(view.root).includes('본문을 불러오지 못했습니다.'))
  assert.match(textOf(view.root), /최근 댓글/)
  act(() => button(view, '본문 다시 시도').props.onClick())
  await settled(() => textOf(view.root).includes('복구된 본문'))
  assert.equal(calls.descriptions.length, 2)
  assert.equal(calls.comments.length, 1)
})

test('empty description and failed comments are represented independently', async (t) => {
  const { view } = render(t, {
    getDescription: async () => ({ body: ' \n ', images: [] }),
    getComments: async () => { throw new Error('comment unavailable') },
  })
  await settled(() => textOf(view.root).includes('댓글을 불러오지 못했습니다.'))
  assert.match(textOf(view.root), /작성된 본문이 없습니다/)
  assert.doesNotMatch(textOf(view.root), /본문을 불러오지 못했습니다/)
})

test('report changes isolate body caches and release the previous image URL before showing the next', async (t) => {
  const closed = []
  const { view, calls, client, update, unmount } = render(t, {
    getDescription: async (_, reportId) => ({ body: `보고서 ${reportId}`, images: [{ attachment_id: '2', alt: '설명 이미지' }] }),
    getDescriptionImage: async (_, __, reportId) => imageContent(`blob:report-${reportId}`, closed),
  })
  await settled(() => view.root.findAllByType('img').length === 1)
  assert.equal(view.root.findByType('img').props.src, 'blob:report-42')
  assert.equal(view.root.findByType('img').props.alt, '설명 이미지')
  update({ issueKey: 'TAC-1', reportId: 43 })
  await settled(() => view.root.findAllByType('img').some((node) => node.props.src === 'blob:report-43'))
  assert.deepEqual(closed, ['blob:report-42'])
  assert.equal(calls.images[0][3].aborted, true)
  assert.equal(calls.images[1][3].aborted, false)
  assert.match(textOf(view.root), /보고서 43/)
  assert.doesNotMatch(textOf(view.root), /보고서 42/)
  assert.equal(client.getQueryData(['sla-dashboard', 'description', 'TAC-1', 43]).body, '보고서 43')
  assert.deepEqual(calls.descriptions.map((call) => call.slice(0, 2)), [['TAC-1', 42], ['TAC-1', 43]])
  unmount()
  assert.equal(calls.images[1][3].aborted, true)
  assert.deepEqual(closed, ['blob:report-42', 'blob:report-43'])
})

test('collapsing pending body and image requests cancels them without creating a late object URL', async (t) => {
  const body = deferred()
  const first = render(t, { getDescription: async () => body.promise })
  await settled(() => first.calls.descriptions.length === 1)
  first.unmount()
  assert.equal(first.calls.descriptions[0][2].aborted, true)
  await act(async () => body.resolve({ body: '늦은 본문', images: [] }))

  const pendingImage = deferred()
  const created = []
  const closed = []
  const second = render(t, {
    getDescription: async () => ({ body: '', images: [{ attachment_id: '2', alt: '' }] }),
    getDescriptionImage: async () => pendingImage.promise,
  })
  await settled(() => second.calls.images.length === 1)
  assert.doesNotMatch(textOf(second.view.root), /작성된 본문이 없습니다/)
  second.unmount()
  assert.equal(second.calls.images[0][3].aborted, true)
  await act(async () => pendingImage.resolve(imageContent('blob:late', closed, created)))
  assert.deepEqual(created, [])
  assert.deepEqual(closed, [])
})

test('failed image fetch and decode can be retried without refetching body or comments', async (t) => {
  let attempts = 0
  const closed = []
  const { view, calls } = render(t, {
    getDescription: async () => ({ body: '이미지 본문', images: [{ attachment_id: '2', alt: '' }] }),
    getDescriptionImage: async () => {
      attempts += 1
      if (attempts === 1) throw new Error('temporary failure')
      return imageContent(`blob:image-${attempts}`, closed)
    },
  })
  await settled(() => textOf(view.root).includes('본문 이미지를 불러오지 못했습니다.'))
  assert.match(textOf(view.root), /이미지 본문/)
  assert.match(textOf(view.root), /최근 댓글/)
  act(() => button(view, '이미지 다시 시도').props.onClick())
  await settled(() => view.root.findAllByType('img').length === 1)
  assert.equal(view.root.findByType('img').props.alt, '본문 첨부 이미지')
  act(() => view.root.findByType('img').props.onError())
  assert.match(textOf(view.root), /본문 이미지를 불러오지 못했습니다/)
  act(() => button(view, '이미지 다시 시도').props.onClick())
  await settled(() => view.root.findAllByType('img').some((node) => node.props.src === 'blob:image-3'))
  assert.deepEqual(closed, ['blob:image-2'])
  assert.equal(calls.descriptions.length, 1)
  assert.equal(calls.comments.length, 1)
  assert.equal(calls.images.length, 3)
})

test('managed description and comment adapters encode every identifier without report parameters', async () => {
  const calls = []
  const body = { body: '전체 이슈 본문', images: [] }
  const page = { comments: [], next_offset: null }
  const blob = new Blob(['image'])
  const binary = imageContent('blob:managed-api', [])
  const { issueManagementApi } = loadSource('infrastructure/api/issueManagementApi', {
    './client': { default: { async get(url, options) {
      calls.push([url, options])
      return { data: options?.responseType ? blob : url.endsWith('/comments') ? page : body }
    } } },
    './binaryContent': { createBinaryContent(value) { assert.equal(value, blob); return binary } },
  }, new Map())
  const controller = new AbortController()
  assert.deepEqual(await issueManagementApi.getDescription('TAC/42', controller.signal), body)
  assert.equal(await issueManagementApi.getDescriptionImage('TAC/42', 'image/2', controller.signal), binary)
  assert.deepEqual(await issueManagementApi.getComments('TAC/42', 0, 10), page)
  assert.equal(await issueManagementApi.getCommentImage('TAC/42', 'comment/1', 'image/3'), binary)
  assert.equal(calls[0][0], '/issue-management/issues/TAC%2F42/description')
  assert.equal(calls[0][1].signal, controller.signal)
  assert.equal(calls[1][0], '/issue-management/issues/TAC%2F42/description/images/image%2F2')
  assert.equal(calls[1][1].signal, controller.signal)
  assert.equal(calls[1][1].responseType, 'blob')
  assert.equal(calls[2][0], '/issue-management/issues/TAC%2F42/comments')
  assert.deepEqual(calls[2][1].params, { offset: 0, limit: 10 })
  assert.equal(calls[3][0], '/issue-management/issues/TAC%2F42/comments/comment%2F1/images/image%2F3')
  assert.equal(calls[3][1].responseType, 'blob')
  assert.ok(calls.every(([, options]) => !Object.hasOwn(options?.params ?? {}, 'report_id')))
})

test('managed content uses its own cache and image gateway and releases both image URLs when collapsed', async (t) => {
  const closed = []
  const { view, calls, client, update, unmount } = render(t, { managed: {
    getDescription: async () => ({ body: '전체 이슈 전용 본문', images: [{ attachment_id: '2', alt: '전체 본문 이미지' }] }),
    getDescriptionImage: async () => imageContent('blob:managed-description', closed),
    getComments: async () => ({ comments: [{ id: '3', author: '작성자', body: '전체 이슈 댓글', created: '', updated: '', images: [{ attachment_id: '4', alt: '전체 댓글 이미지' }] }], next_offset: null }),
    getCommentImage: async () => imageContent('blob:managed-comment', closed),
  } })
  await settled(() => textOf(view.root).includes('보고서 본문') && textOf(view.root).includes('최근 댓글'))
  update({ issueKey: 'TAC-1', source: 'issue-management' })
  await settled(() => view.root.findAllByType('img').length === 2)
  assert.match(textOf(view.root), /전체 이슈 전용 본문/)
  assert.match(textOf(view.root), /전체 이슈 댓글/)
  assert.doesNotMatch(textOf(view.root), /보고서 본문/)
  const managedBodyQuery = client.getQueryCache().getAll().find((query) => query.state.data?.body === '전체 이슈 전용 본문')
  assert.ok(managedBodyQuery)
  assert.equal(managedBodyQuery.queryKey[0], 'issue-management')
  assert.equal(calls.descriptions.length, 1)
  assert.equal(calls.comments.length, 1)
  assert.deepEqual(calls.images, [])
  assert.equal(calls.managedDescriptions[0][0], 'TAC-1')
  assert.equal(calls.managedDescriptions[0][1].aborted, false)
  assert.deepEqual(calls.managedComments, [['TAC-1', 0, 5]])
  assert.deepEqual(calls.managedImages[0].slice(0, 2), ['TAC-1', '2'])
  assert.equal(calls.managedImages[0][2].aborted, false)
  assert.deepEqual(calls.managedCommentImages, [['TAC-1', '3', '4']])
  assert.deepEqual(view.root.findAllByType('img').map((node) => node.props.src), ['blob:managed-description', 'blob:managed-comment'])
  unmount()
  assert.equal(calls.managedImages[0][2].aborted, true)
  assert.deepEqual(closed.sort(), ['blob:managed-comment', 'blob:managed-description'])
})

test('managed pending description and image requests are aborted and cannot create URLs after collapse', async (t) => {
  const body = deferred()
  const first = render(t, { managed: { getDescription: async () => body.promise } }, { issueKey: 'TAC-1', source: 'issue-management' })
  await settled(() => first.calls.managedDescriptions.length === 1)
  first.unmount()
  assert.equal(first.calls.managedDescriptions[0][1].aborted, true)
  await act(async () => body.resolve({ body: '늦은 본문', images: [] }))
  assert.deepEqual(first.calls.descriptions, [])

  const pendingImage = deferred()
  const created = []
  const closed = []
  const second = render(t, { managed: {
    getDescription: async () => ({ body: '', images: [{ attachment_id: '2', alt: '' }] }),
    getDescriptionImage: async () => pendingImage.promise,
  } }, { issueKey: 'TAC-1', source: 'issue-management' })
  await settled(() => second.calls.managedImages.length === 1)
  second.unmount()
  assert.equal(second.calls.managedImages[0][2].aborted, true)
  await act(async () => pendingImage.resolve(imageContent('blob:managed-late', closed, created)))
  assert.deepEqual(created, [])
  assert.deepEqual(closed, [])
})
