// frontend/tests/slaComments.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { InfiniteQueryObserver, QueryClient } from '@tanstack/react-query'
import ts from 'typescript'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

function loadSource(relative, dependencies = {}) {
  const source = fs.readFileSync(path.join(root, relative), 'utf8')
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText
  const module = { exports: {} }
  const require = (specifier) => {
    assert.ok(Object.hasOwn(dependencies, specifier), `unexpected dependency ${specifier}`)
    return dependencies[specifier]
  }
  new Function('require', 'module', 'exports', compiled)(require, module, module.exports)
  return module.exports
}

const queryKeys = loadSource('src/presentation/config/queryKeys.ts')

function hookOptions(getComments, issueKey = 'TAC-42') {
  const hook = loadSource('src/presentation/hooks/useSlaDashboard.ts', {
    '@tanstack/react-query': { useInfiniteQuery: (options) => options },
    '@/presentation/config/queryKeys': queryKeys,
    '@/presentation/context/ApplicationServicesContext': {
      useApplicationServices: () => ({ slaDashboard: { getComments } }),
    },
  })
  return hook.useSlaIssueComments(issueKey, true)
}

function comments(count) {
  return Array.from({ length: count }, (_, index) => ({
    id: String(count - index),
    author: '작성자',
    body: `댓글 ${count - index}`,
    created: '2026-09-08',
    updated: '2026-09-08',
    images: [],
  }))
}

function snapshot(values, offset, limit) {
  return {
    comments: values.slice(offset, offset + limit),
    next_offset: offset + limit < values.length ? offset + limit : null,
  }
}

async function observe(t, getComments, initialCache) {
  const options = hookOptions(getComments)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  initialCache?.(client)
  const observer = new InfiniteQueryObserver(client, options)
  const unsubscribe = observer.subscribe(() => {})
  t.after(() => { unsubscribe(); client.clear() })
  await observer.refetch()
  return {
    observer,
    client,
    options,
    result: () => observer.getCurrentResult(),
    cache: () => client.getQueryData(options.queryKey),
  }
}

test('comment hook loads latest 5, 10, 15 and the final partial snapshot while retaining one cached page', async (t) => {
  const values = comments(17)
  const calls = []
  const query = await observe(t, async (key, offset, limit) => {
    calls.push([key, offset, limit])
    return snapshot(values, offset, limit)
  })
  assert.deepEqual(query.result().data.map((comment) => comment.id), values.slice(0, 5).map((comment) => comment.id))
  for (const limit of [10, 15, 20]) {
    await query.observer.fetchNextPage({ cancelRefetch: false })
    assert.deepEqual(query.result().data.map((comment) => comment.id), values.slice(0, limit).map((comment) => comment.id))
    assert.equal(query.cache().pages.length, 1)
    assert.deepEqual(query.cache().pageParams, [limit])
  }
  assert.equal(query.result().hasNextPage, false)
  await query.observer.fetchNextPage({ cancelRefetch: false })
  assert.deepEqual(calls, [5, 10, 15, 20].map((limit) => ['TAC-42', 0, limit]))
  assert.equal(query.result().data.length, 17)
})

test('a new latest comment, an edit and a deletion replace the previous snapshot without duplicates or stale entries', async (t) => {
  let values = comments(20)
  const query = await observe(t, async (_, offset, limit) => snapshot(values, offset, limit))
  const newComment = { ...values[0], id: '21', body: '새로 작성한 댓글' }
  values = [newComment, ...values.map((comment) => comment.id === '20' ? { ...comment, body: '수정된 내용' } : comment)]
  await query.observer.fetchNextPage({ cancelRefetch: false })
  assert.equal(query.result().data.length, 10)
  assert.deepEqual(query.result().data, values.slice(0, 10))
  assert.equal(query.result().data[0].id, '21')
  assert.equal(query.result().data.find((comment) => comment.id === '20').body, '수정된 내용')
  values = values.filter((comment) => comment.id !== '18')
  await query.observer.fetchNextPage({ cancelRefetch: false })
  assert.equal(query.result().data.length, 15)
  assert.deepEqual(query.result().data, values.slice(0, 15))
  assert.equal(new Set(query.result().data.map((comment) => comment.id)).size, 15)
  assert.equal(query.result().data.some((comment) => comment.id === '18'), false)
})

test('failed load-more preserves successful comments and cursor then retries the same cumulative limit', async (t) => {
  const values = comments(18)
  const calls = []
  let shouldFail = false
  const query = await observe(t, async (_, offset, limit) => {
    calls.push(limit)
    if (shouldFail) throw new Error('Jira temporarily unavailable')
    return snapshot(values, offset, limit)
  })
  await query.observer.fetchNextPage({ cancelRefetch: false })
  const successful = query.result().data
  shouldFail = true
  await query.observer.fetchNextPage({ cancelRefetch: false })
  assert.equal(query.result().isFetchNextPageError, true)
  assert.equal(query.result().isRefetchError, false)
  assert.equal(query.result().isFetching, false)
  assert.equal(query.result().hasNextPage, true)
  assert.deepEqual(query.result().data, successful)
  assert.deepEqual(query.cache().pageParams, [10])
  shouldFail = false
  await query.observer.fetchNextPage({ cancelRefetch: false })
  assert.equal(query.result().isFetchNextPageError, false)
  assert.deepEqual(query.result().data, values.slice(0, 15))
  assert.deepEqual(query.cache().pageParams, [15])
  assert.deepEqual(calls, [5, 10, 15, 15])
})

test('refetch keeps the expanded limit and distinguishes background errors from load-more errors', async (t) => {
  let values = comments(18)
  let shouldFail = false
  const calls = []
  const query = await observe(t, async (_, offset, limit) => {
    calls.push(limit)
    if (shouldFail) throw new Error('Refetch temporarily unavailable')
    return snapshot(values, offset, limit)
  }, (client) => client.setQueryData(['sla-dashboard', 'comments', 'TAC-42'], {
    pages: [snapshot(comments(40), 0, 5)],
    pageParams: [0],
  }))
  assert.deepEqual(calls, [5])
  await query.observer.fetchNextPage({ cancelRefetch: false })
  await query.observer.fetchNextPage({ cancelRefetch: false })
  values = [{ ...values[0], id: '19' }, ...values]
  await query.observer.refetch()
  assert.deepEqual(calls, [5, 10, 15, 15])
  assert.deepEqual(query.result().data, values.slice(0, 15))
  assert.deepEqual(query.cache().pageParams, [15])
  assert.equal(query.cache().pages.length, 1)
  const successful = query.result().data
  shouldFail = true
  await query.observer.refetch()
  assert.equal(query.result().isRefetchError, true)
  assert.equal(query.result().isFetchNextPageError, false)
  assert.deepEqual(query.result().data, successful)
  assert.deepEqual(query.cache().pageParams, [15])
  shouldFail = false
  await query.observer.refetch()
  assert.equal(query.result().isError, false)
  assert.equal(query.result().data.length, 15)
})

test('concurrent load-more calls with cancelRefetch false share one request and preserve visible comments while pending', async (t) => {
  const values = comments(15)
  const calls = []
  let release
  const query = await observe(t, async (_, offset, limit) => {
    calls.push(limit)
    if (limit === 10) await new Promise((resolve) => { release = resolve })
    return snapshot(values, offset, limit)
  })
  const first = query.observer.fetchNextPage({ cancelRefetch: false })
  const second = query.observer.fetchNextPage({ cancelRefetch: false })
  assert.equal(query.result().isFetchingNextPage, true)
  assert.equal(query.result().data.length, 5)
  assert.deepEqual(calls, [5, 10])
  assert.equal(typeof release, 'function')
  release()
  await Promise.all([first, second])
  assert.deepEqual(calls, [5, 10])
  assert.equal(query.result().data.length, 10)
  assert.equal(query.result().isFetchingNextPage, false)
})

test('comment API forwards cumulative limits and keeps the five-comment default', async () => {
  const calls = []
  const response = snapshot(comments(15), 0, 10)
  const { slaDashboardApi } = loadSource('src/infrastructure/api/slaDashboardApi.ts', {
    './client': { default: { get: async (...args) => { calls.push(args); return { data: response } } } },
    './binaryContent': { createBinaryContent: (content) => content },
  })
  assert.deepEqual(await slaDashboardApi.getComments('TAC-42'), response)
  assert.deepEqual(await slaDashboardApi.getComments('TAC/42', 0, 15), response)
  assert.deepEqual(calls, [
    ['/sla-dashboard/issues/TAC-42/comments', { params: { offset: 0, limit: 5 } }],
    ['/sla-dashboard/issues/TAC%2F42/comments', { params: { offset: 0, limit: 15 } }],
  ])
})
