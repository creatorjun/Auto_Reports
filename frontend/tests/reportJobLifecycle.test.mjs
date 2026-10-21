// frontend/tests/reportJobLifecycle.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

function deferred() {
  let resolve
  let reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

function setup({ streams = false } = {}) {
  const requests = []
  const events = []
  const timers = new Map()
  const sources = []
  let nextTimer = 0
  class Source {
    listeners = new Map()
    closed = false
    constructor(url) { this.url = url; sources.push(this) }
    addEventListener(event, callback) { this.listeners.set(event, callback) }
    close() { this.closed = true }
    emit(event, data) { this.listeners.get(event)?.({ data: JSON.stringify(data) }) }
  }
  const client = {
    get: (url, options) => {
      const pending = deferred()
      requests.push({ url, options, ...pending })
      return pending.promise
    },
  }
  const filename = new URL('../src/infrastructure/api/reportApi.ts', import.meta.url)
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }, fileName: filename.pathname,
  }).outputText
  const module = { exports: {} }
  new Function('require', 'module', 'exports', 'EventSource', 'setTimeout', 'clearTimeout', compiled)(
    (dependency) => { assert.equal(dependency, './client'); return { default: client, getAccessToken: () => null } },
    module, module.exports, streams ? Source : undefined,
    (callback, delay) => { const id = ++nextTimer; timers.set(id, { callback, delay }); return id },
    (id) => timers.delete(id),
  )
  const callbacks = {
    onStatus: (value) => events.push(['status', value]),
    onComplete: (value) => events.push(['complete', value]),
    onError: (value) => events.push(['error', value]),
    onTransportError: (value) => events.push(['transport', value]),
    onTimeout: () => events.push(['timeout']),
  }
  return {
    api: module.exports.reportApi, requests, events, timers, sources, callbacks,
    fireTimer: (delay) => {
      const entry = [...timers].find(([, timer]) => delay === undefined || timer.delay === delay)
      assert.ok(entry, `Missing timer for ${delay}`)
      timers.delete(entry[0])
      return entry[1].callback()
    },
  }
}

async function settle() { for (let i = 0; i < 5; i++) await Promise.resolve() }

for (const status of [{ status: 'running' }, { status: 'done', report_id: 7 }, { status: 'error', error: 'failed' }]) {
  test(`closing a pending poll aborts its request and ignores late ${status.status} status`, async () => {
    const state = setup()
    const subscription = state.api.watchJob('job-1', state.callbacks, 30000)
    subscription.close()
    state.requests[0].resolve({ data: status })
    await settle()
    assert.deepEqual(state.events, [])
    assert.equal(state.requests[0].options?.signal.aborted, true)
    assert.equal(state.timers.size, 0)
    assert.equal(state.requests.length, 1)
  })
}

test('closing a pending poll ignores its late transport failure', async () => {
  const state = setup()
  const subscription = state.api.watchJob('job-1', state.callbacks, 30000)
  subscription.close()
  state.requests[0].reject(new Error('network failure'))
  await settle()
  assert.deepEqual(state.events, [])
  assert.equal(state.requests[0].options?.signal.aborted, true)
  assert.equal(state.timers.size, 0)
})

for (const failure of [false, true]) {
  test(`a polling deadline aborts the request and ignores late ${failure ? 'failure' : 'completion'}`, async () => {
    const state = setup()
    state.api.watchJob('job-1', state.callbacks, 30000)
    state.fireTimer(30000)
    if (failure) state.requests[0].reject(new Error('request aborted'))
    else state.requests[0].resolve({ data: { status: 'done', report_id: 7 } })
    await settle()
    assert.deepEqual(state.events, [['timeout']])
    assert.equal(state.requests[0].options?.signal.aborted, true)
    assert.equal(state.timers.size, 0)
  })
}

for (const status of [{ status: 'running' }, { status: 'done', report_id: 7 }]) {
  test(`a status callback can close a ${status.status} poll without further work`, async () => {
    const state = setup()
    let subscription
    subscription = state.api.watchJob('job-1', { ...state.callbacks, onStatus: () => subscription.close() }, 30000)
    state.requests[0].resolve({ data: status })
    await settle()
    assert.deepEqual(state.events, [])
    assert.equal(state.timers.size, 0)
  })
}

test('repeated stream failures start only one polling fallback and ignore stale stream events', async () => {
  const state = setup({ streams: true })
  const subscription = state.api.watchJob('job-1', state.callbacks, 30000)
  state.sources[0].emit('error')
  state.sources[0].emit('error')
  state.sources[0].emit('status', { status: 'running' })
  state.sources[0].emit('done', { status: 'done', report_id: 99 })
  assert.equal(state.requests.length, 1)
  assert.equal(state.sources[0].closed, true)
  assert.deepEqual(state.events, [])
  state.requests[0].resolve({ data: { status: 'done', report_id: 7 } })
  await settle()
  assert.deepEqual(state.events, [['status', { status: 'done', report_id: 7 }], ['complete', 7]])
  assert.equal(state.timers.size, 0)
  subscription.close()
})

test('active polling retains retry hints, completion and request cancellation', async () => {
  const state = setup()
  state.api.watchJob('job-1', state.callbacks, 30000)
  state.requests[0].resolve({ data: { status: 'running', retry_after: 2 } })
  await settle()
  state.fireTimer(2000)
  assert.equal(state.requests.length, 2)
  state.requests[1].resolve({ data: { status: 'done', report_id: 7 } })
  await settle()
  assert.deepEqual(state.events, [
    ['status', { status: 'running', retry_after: 2 }],
    ['status', { status: 'done', report_id: 7 }],
    ['complete', 7],
  ])
  assert.equal(state.requests[1].options?.signal.aborted, true)
  assert.equal(state.timers.size, 0)
})

test('an active polling transport failure is reported once and closes the subscription', async () => {
  const state = setup()
  state.api.watchJob('job-1', state.callbacks, 30000)
  const error = new Error('network failure')
  state.requests[0].reject(error)
  await settle()
  assert.deepEqual(state.events, [['transport', error]])
  assert.equal(state.timers.size, 0)
})

for (const terminal of ['done', 'error', 'timeout']) {
  test(`active streaming retains ${terminal} behavior and closes its source`, () => {
    const state = setup({ streams: true })
    state.api.watchJob('job-1', state.callbacks, 30000)
    state.sources[0].emit('status', { status: 'running' })
    if (terminal === 'timeout') state.sources[0].emit('timeout')
    else state.sources[0].emit('done', terminal === 'done' ? { status: 'done', report_id: 7 } : { status: 'error', error: 'failed' })
    assert.deepEqual(state.events, [
      ['status', { status: 'running' }],
      terminal === 'done' ? ['complete', 7] : terminal === 'error' ? ['error', 'failed'] : ['timeout'],
    ])
    assert.equal(state.sources[0].closed, true)
    assert.equal(state.requests.length, 0)
    assert.equal(state.timers.size, 0)
  })
}

test('an immediately expired polling subscription leaves no timer or request', () => {
  const state = setup()
  state.api.watchJob('job-1', state.callbacks, 0)
  assert.deepEqual(state.events, [['timeout']])
  assert.equal(state.requests.length, 0)
  assert.equal(state.timers.size, 0)
})
