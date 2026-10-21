// frontend/tests/storageUploads.test.mjs
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
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query')
const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')

function sourceLoader(overrides = {}, timers = globalThis) {
  const modules = new Map()
  function load(relative) {
    if (Object.hasOwn(overrides, relative)) return overrides[relative]
    const base = path.join(sourceRoot, relative)
    const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
    assert.ok(filename, `Missing module ${relative}`)
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX }, fileName: filename }).outputText
    new Function('require', 'module', 'exports', 'setTimeout', 'clearTimeout', compiled)((dependency) => {
      if (Object.hasOwn(overrides, dependency)) return overrides[dependency]
      if (dependency.startsWith('@/')) return load(dependency.slice(2))
      if (dependency.startsWith('.')) return load(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)).replaceAll('\\', '/'))
      return require(dependency)
    }, module, module.exports, timers.setTimeout, timers.clearTimeout)
    return module.exports
  }
  return load
}

function deferred() {
  let resolve
  let reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

function setup(t, gateway = {}) {
  let nextTimer = 0
  const scheduled = new Map()
  const timers = {
    setTimeout: (callback) => { const id = ++nextTimer; scheduled.set(id, callback); return id },
    clearTimeout: (id) => scheduled.delete(id),
  }
  const load = sourceLoader({}, timers)
  const { ApplicationServicesProvider } = load('presentation/context/ApplicationServicesContext')
  const { useUploadFiles } = load('presentation/hooks/useStorage')
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } })
  const calls = []
  const storage = {
    getQuota: async () => ({ available: 1000 }),
    upload: async (file, folder) => { calls.push([file.name, folder]); return { name: file.name } },
    ...gateway,
  }
  let observed, view
  function Probe() { observed = useUploadFiles('reports'); return null }
  act(() => { view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { storage } }, React.createElement(QueryClientProvider, { client }, React.createElement(Probe)))) })
  t.after(() => { act(() => view.unmount()); client.clear() })
  return { calls, client, scheduled, load, unmount: () => act(() => view.unmount()), get observed() { return observed } }
}

function file(name) { return new File(['data'], name, { type: 'text/plain' }) }

test('batch upload rejects partial failure and stops reporting it as an active upload', async (t) => {
  const state = setup(t, { upload: async (source) => { if (source.name === 'failed.txt') throw new Error('unavailable'); return { name: source.name } } })
  await act(async () => {
    await assert.rejects(state.observed.upload([file('saved.txt'), file('failed.txt')]), /failed.txt/)
  })
  assert.equal(state.observed.isUploading, false)
})

test('upload preflight owns the batch before asynchronous quota retrieval', async (t) => {
  const quota = deferred()
  const state = setup(t, { getQuota: () => quota.promise })
  let first, duplicate
  act(() => {
    first = state.observed.upload([file('first.txt')])
    duplicate = state.observed.upload([file('duplicate.txt')])
  })
  await act(async () => { quota.resolve({ available: 1000 }); await Promise.allSettled([first, duplicate]) })
  assert.deepEqual(state.calls, [['first.txt', 'reports']])
})

test('unmount cancels completion timer and prevents quota continuation from starting writes', async (t) => {
  const completed = setup(t)
  await act(async () => { await completed.observed.upload([file('first.txt')]) })
  assert.equal(completed.scheduled.size, 1)
  completed.unmount()
  assert.equal(completed.scheduled.size, 0)
  const quota = deferred()
  const pending = setup(t, { getQuota: () => quota.promise })
  const { useAuthStore } = pending.load('presentation/state/authStore')
  const subscribe = useAuthStore.subscribe
  let subscriptions = 0
  useAuthStore.subscribe = (listener) => {
    subscriptions += 1
    let subscribed = true
    const unsubscribe = subscribe(listener)
    return () => { if (subscribed) subscriptions -= 1; subscribed = false; unsubscribe() }
  }
  let operation
  act(() => { operation = pending.observed.upload([file('late.txt')]) })
  assert.equal(subscriptions, 1)
  pending.unmount()
  assert.equal(subscriptions, 0)
  await act(async () => { quota.resolve({ available: 1000 }); await Promise.allSettled([operation]) })
  assert.deepEqual(pending.calls, [])
})

test('a new batch replaces the previous completion timer without hiding active progress', async (t) => {
  const next = deferred()
  const state = setup(t, { upload: async (source) => source.name === 'next.txt' ? next.promise : { name: source.name } })
  await act(async () => { await state.observed.upload([file('first.txt')]) })
  assert.equal(state.scheduled.size, 1)
  let operation
  act(() => { operation = state.observed.upload([file('next.txt')]) })
  assert.equal(state.scheduled.size, 0)
  assert.equal(state.observed.isUploading, true)
  await act(async () => { next.resolve({ name: 'next.txt' }); await operation })
  assert.equal(state.scheduled.size, 1)
})

test('logout aborts the current upload before another request can start', async (t) => {
  const pending = deferred()
  let signal
  const state = setup(t, { upload: async (_source, _folder, _overwrite, _progress, cancellation) => { signal = cancellation; return pending.promise } })
  let operation
  await act(async () => { operation = state.observed.upload([file('active.txt')]) })
  assert.equal(signal.aborted, false)
  const { useAuthStore } = state.load('presentation/state/authStore')
  act(() => useAuthStore.getState().clearAuth())
  assert.equal(signal.aborted, true)
  state.unmount()
  await act(async () => { pending.resolve({ name: 'active.txt' }); await operation })
  assert.equal(state.scheduled.size, 0)
})

test('batch quota validation and failure details belong to the application service', async () => {
  const { uploadStorageFiles, QuotaExceededError, UploadBatchError } = sourceLoader()('application/services/storageUploads')
  const files = [file('saved.txt'), file('failed.txt')].map((item) => ({ name: item.name, size: item.size, mediaType: item.type, read: () => item.arrayBuffer() }))
  let calls = 0
  await assert.rejects(uploadStorageFiles({ getQuota: async () => ({ available: 1 }), upload: async () => { calls += 1 } }, files, '', false, () => {}), (error) => error instanceof QuotaExceededError && error.available === 1 && error.needed === 8)
  assert.equal(calls, 0)
  const progress = []
  await assert.rejects(uploadStorageFiles({
    getQuota: async () => ({ available: 100 }),
    upload: async (source) => { if (source.name === 'failed.txt') throw new Error('denied'); return { name: source.name } },
  }, files, 'folder', false, (index, item) => progress.push([index, item])), (error) => error instanceof UploadBatchError && error.failedNames.join(',') === 'failed.txt')
  assert.deepEqual(progress, [[0, { name: 'saved.txt', percent: 100, done: true }], [1, { name: 'failed.txt', percent: 0, done: false, failed: true }]])
})

test('chunk upload aborts its server resource when cancellation occurs during file reading', async () => {
  const reading = deferred()
  const calls = []
  const controller = new AbortController()
  const client = {
    post: async (...args) => { calls.push(['post', ...args]); return { data: { upload_id: 'upload-1' } } },
    delete: async (...args) => { calls.push(['delete', ...args]) },
  }
  const api = sourceLoader({ 'infrastructure/api/client': { default: client } })('infrastructure/api/storageApi').storageApi
  const operation = api.upload({ name: 'large.dat', size: 16 * 1024 * 1024, mediaType: 'application/octet-stream', read: () => reading.promise }, '', false, undefined, controller.signal)
  await Promise.resolve()
  controller.abort()
  reading.resolve(new ArrayBuffer(8))
  await assert.rejects(operation, /cancelled/)
  assert.deepEqual(calls.map((call) => call.slice(0, 2)), [['post', '/storage/upload/init'], ['delete', '/storage/upload/abort']])
  assert.equal(calls[0][3].signal, controller.signal)
  assert.deepEqual(calls[1][2], { params: { upload_id: 'upload-1' } })
})
