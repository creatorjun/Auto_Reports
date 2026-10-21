// frontend/tests/searchCancellation.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

function deferred() {
  let resolve
  let reject
  const promise = new Promise((accept, decline) => { resolve = accept; reject = decline })
  return { promise, resolve, reject }
}

function setup(t) {
  const calls = []
  const timers = new Map()
  let nextTimer = 0
  const search = {
    getJiraBaseUrl: async () => 'https://jira.test',
    search(query, limit, signal) {
      const request = { query, limit, signal, ...deferred() }
      calls.push(request)
      return request.promise
    },
  }
  const filename = path.join(root, 'src/presentation/components/common/SearchWidget.tsx')
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
    fileName: filename,
  }).outputText
  const module = { exports: {} }
  const dependencies = {
    '@/presentation/context/ApplicationServicesContext': { useApplicationServices: () => ({ search }) },
    '@/presentation/config/constants': { DEFAULT_JIRA_BASE_URL: 'https://jira.test' },
    '@/presentation/components/common/IssueModalShell': { default: ({ title, children, onClose }) => React.createElement('section', { 'aria-label': title, onClose }, children) },
  }
  new Function('require', 'module', 'exports', 'setTimeout', 'clearTimeout', 'window', compiled)(
    (dependency) => Object.hasOwn(dependencies, dependency) ? dependencies[dependency] : require(dependency),
    module,
    module.exports,
    (handler, delay) => { const id = ++nextTimer; timers.set(id, { handler, delay }); return id },
    (id) => timers.delete(id),
    { open() {} },
  )
  let view
  act(() => { view = TestRenderer.create(React.createElement(module.exports.default)) })
  t.after(() => act(() => view.unmount()))
  return {
    calls,
    timers,
    view,
    input(query, flush = true) {
      act(() => view.root.findByType('input').props.onChange({ target: { value: query } }))
      if (flush) this.flushDebounce()
    },
    flushDebounce() {
      act(() => {
        for (const [id, timer] of [...timers]) {
          if (timer.delay === 1000 && timers.delete(id)) timer.handler()
        }
      })
    },
    submit() {
      act(() => view.root.findByType('input').props.onKeyDown({ key: 'Enter', preventDefault() {} }))
    },
    blur() {
      act(() => view.root.findByType('input').props.onBlur())
    },
    flushBlur() {
      act(() => {
        for (const [id, timer] of [...timers]) {
          if (timer.delay === 150 && timers.delete(id)) timer.handler()
        }
      })
    },
    loading: () => view.root.findAllByType('svg').some((node) => node.props.className?.includes('animate-spin')),
  }
}

function result(title) {
  return { type: 'jira', key: 'TACEA-1000', title, status: '진행 중', issue_type: '개선', url: 'https://jira.test/browse/TACEA-1000' }
}

function textOf(view) {
  const collect = (node) => node === null ? '' : typeof node === 'string' ? node
    : Array.isArray(node) ? node.map(collect).join(' ') : collect(node.children)
  return collect(view.toJSON())
}

test('an aborted gateway failure leaves the newer search pending and preserves its result', async (t) => {
  const app = setup(t)
  app.input('old query')
  app.input('new query')
  assert.equal(app.calls.length, 2)
  assert.equal(app.calls[0].signal.aborted, true)
  assert.equal(app.calls[1].signal.aborted, false)
  assert.equal(app.calls[1].limit, 5)

  await act(async () => app.calls[0].reject(new Error('Gateway request ended')))
  assert.equal(app.loading(), true)
  await act(async () => app.calls[1].resolve([result('Newest result')]))
  assert.match(textOf(app.view), /Newest result/)
  assert.equal(app.loading(), false)
})

test('an aborted gateway failure arriving after the newer result cannot clear suggestions', async (t) => {
  const app = setup(t)
  app.input('old query')
  app.input('new query')
  await act(async () => app.calls[1].resolve([result('Newest result')]))
  await act(async () => app.calls[0].reject(new Error('Gateway request ended')))
  assert.match(textOf(app.view), /Newest result/)
  assert.equal(app.loading(), false)
})

test('an adapter that resolves an aborted request cannot replace newer suggestions', async (t) => {
  const app = setup(t)
  app.input('old query')
  app.input('new query')
  await act(async () => app.calls[1].resolve([result('Newest result')]))
  await act(async () => app.calls[0].resolve([result('Outdated result')]))
  assert.match(textOf(app.view), /Newest result/)
  assert.doesNotMatch(textOf(app.view), /Outdated result/)
})

test('a current gateway failure still shows the direct ticket fallback and ends loading', async (t) => {
  const app = setup(t)
  app.input('1234')
  await act(async () => app.calls[0].reject(new Error('Gateway unavailable')))
  assert.match(textOf(app.view), /TACEA-1234 이슈 바로가기/)
  assert.equal(app.loading(), false)
})

test('editing a query cancels the previous request before the next debounce expires', async (t) => {
  const app = setup(t)
  app.input('old query')
  app.input('new query', false)
  assert.equal(app.calls[0].signal.aborted, true)
  await act(async () => app.calls[0].resolve([result('Outdated result')]))
  assert.doesNotMatch(textOf(app.view), /Outdated result/)
  app.flushDebounce()
  assert.equal(app.calls.length, 2)
  await act(async () => app.calls[1].resolve([result('Newest result')]))
  assert.match(textOf(app.view), /Newest result/)
})

test('clearing a query prevents late results from reopening the dropdown', async (t) => {
  const app = setup(t)
  app.input('old query')
  app.input('')
  assert.equal(app.calls[0].signal.aborted, true)
  await act(async () => app.calls[0].resolve([result('Outdated result')]))
  assert.equal(app.calls.length, 1)
  assert.doesNotMatch(textOf(app.view), /Outdated result/)
  assert.equal(app.loading(), false)
})

test('submitting a search cancels suggestions and their pending debounce', async (t) => {
  const app = setup(t)
  app.input('old query')
  app.input('modal query', false)
  app.submit()
  app.flushDebounce()
  assert.equal(app.calls.length, 2)
  assert.equal(app.calls[0].signal.aborted, true)
  assert.equal(app.calls[1].query, 'modal query')
  assert.equal(app.calls[1].signal.aborted, false)
  await act(async () => app.calls[0].reject(new Error('Cancelled suggestions')))
  assert.equal(app.loading(), true)
  await act(async () => app.calls[1].resolve([result('Modal result')]))
  assert.match(textOf(app.view), /Modal result/)
  assert.equal(app.view.root.findByType('section').props['aria-label'], '"modal query" 검색 결과')
})

test('late modal results cannot replace a newer search result or its query', async (t) => {
  const app = setup(t)
  app.input('first modal', false)
  app.submit()
  app.input('second modal', false)
  app.submit()
  assert.equal(app.calls.length, 2)
  assert.equal(app.calls[0].signal.aborted, true)
  await act(async () => app.calls[1].resolve([result('Newest modal result')]))
  await act(async () => app.calls[0].resolve([result('Outdated modal result')]))
  assert.match(textOf(app.view), /Newest modal result/)
  assert.doesNotMatch(textOf(app.view), /Outdated modal result/)
  assert.equal(app.view.root.findByType('section').props['aria-label'], '"second modal" 검색 결과')
  assert.equal(app.loading(), false)
})

test('unmounting aborts pending searches and clears focus timers', async (t) => {
  const app = setup(t)
  app.input('pending modal', false)
  app.submit()
  act(() => app.view.root.findByType('input').props.onBlur())
  act(() => app.view.unmount())
  assert.equal(app.calls[0].signal.aborted, true)
  assert.equal(app.timers.size, 0)
  await act(async () => app.calls[0].resolve([result('Unmounted result')]))
  assert.equal(app.view.toJSON(), null)
})

for (const dismissal of ['Escape', 'blur']) {
  test(`${dismissal} cancels pending suggestions before a dropdown exists`, async (t) => {
    const app = setup(t)
    app.input('pending suggestions')
    if (dismissal === 'Escape') {
      act(() => app.view.root.findByType('input').props.onKeyDown({ key: 'Escape', preventDefault() {} }))
    } else {
      app.blur()
      app.flushBlur()
    }
    assert.equal(app.calls[0].signal.aborted, true)
    await act(async () => app.calls[0].resolve([result('Dismissed result')]))
    assert.doesNotMatch(textOf(app.view), /Dismissed result/)
    assert.equal(app.loading(), false)
  })

  test(`${dismissal} removes a queued autocomplete request`, (t) => {
    const app = setup(t)
    app.input('queued suggestions', false)
    if (dismissal === 'Escape') {
      act(() => app.view.root.findByType('input').props.onKeyDown({ key: 'Escape', preventDefault() {} }))
    } else {
      app.blur()
      app.flushBlur()
    }
    app.flushDebounce()
    assert.equal(app.calls.length, 0)
  })
}

test('a queued blur dismissal preserves a newer modal request', async (t) => {
  const app = setup(t)
  app.input('modal query', false)
  app.blur()
  app.submit()
  app.flushBlur()
  assert.equal(app.calls[0].signal.aborted, false)
  assert.equal(app.loading(), true)
  await act(async () => app.calls[0].resolve([result('Modal result after blur')]))
  assert.match(textOf(app.view), /Modal result after blur/)
})
