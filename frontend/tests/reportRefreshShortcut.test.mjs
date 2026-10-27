// frontend/tests/reportRefreshShortcut.test.mjs
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

function sourceLoader(overrides = {}) {
  const modules = new Map()
  function load(relative) {
    if (Object.hasOwn(overrides, relative)) return overrides[relative]
    const base = path.join(sourceRoot, relative)
    const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
    assert.ok(filename, `Missing module ${relative}`)
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
      fileName: filename,
    }).outputText
    new Function('require', 'module', 'exports', compiled)((dependency) => {
      if (Object.hasOwn(overrides, dependency)) return overrides[dependency]
      if (dependency.startsWith('@/')) return load(dependency.slice(2))
      if (dependency.startsWith('.')) return load(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)).replaceAll('\\', '/'))
      return require(dependency)
    }, module, module.exports)
    return module.exports
  }
  return load
}

function keyboard() {
  const previousWindow = Object.getOwnPropertyDescriptor(globalThis, 'window')
  const listeners = new Set()
  const eventListeners = new Map([['keydown', listeners]])
  Object.defineProperty(globalThis, 'window', {
    configurable: true,
    value: {
      addEventListener: (type, callback) => {
        if (!eventListeners.has(type)) eventListeners.set(type, new Set())
        eventListeners.get(type).add(callback)
      },
      removeEventListener: (type, callback) => { eventListeners.get(type)?.delete(callback) },
    },
  })
  return {
    listeners,
    restore() {
      if (previousWindow) Object.defineProperty(globalThis, 'window', previousWindow)
      else delete globalThis.window
    },
    key(changes = {}) {
      const event = {
        key: 'r', ctrlKey: false, metaKey: false, altKey: false, shiftKey: false,
        repeat: false, isComposing: false, defaultPrevented: false,
        preventDefault() { this.defaultPrevented = true },
        ...changes,
      }
      act(() => { for (const listener of [...listeners]) listener(event) })
      return event
    },
  }
}

function setup(t, initial = {}) {
  const keys = keyboard()
  const requests = []
  const generation = { generate: (request) => requests.push(request), pending: false, lastRequest: { period: 'month', date: '2026-09-01' }, ...initial }
  const { useReportRefreshShortcut } = sourceLoader({
    'presentation/context/ReportGenerationContext': { useReportGeneration: () => generation },
  })('presentation/hooks/useReportRefreshShortcut')
  let refresh
  function Probe({ enabled }) {
    refresh = useReportRefreshShortcut(enabled)
    return null
  }
  let view
  let mounted = true
  act(() => { view = TestRenderer.create(React.createElement(Probe, { enabled: true })) })
  function unmount() {
    if (!mounted) return
    act(() => view.unmount())
    mounted = false
  }
  t.after(() => { unmount(); keys.restore() })
  return {
    ...keys, generation, requests, unmount,
    get refresh() { return refresh },
    update: (enabled = true) => act(() => view.update(React.createElement(Probe, { enabled }))),
  }
}

async function until(predicate) {
  const deadline = Date.now() + 2500
  while (!predicate()) {
    assert.ok(Date.now() < deadline, 'Timed out waiting for report rerun')
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 5)) })
  }
}

function textOf(node) {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textOf).join(' ')
  return node?.children ? textOf(node.children) : ''
}

test('report API forwards only the latest-report rerun selector without adding draft dates', async () => {
  const calls = []
  const client = { post: async (...args) => { calls.push(args); return { data: { job_id: 'rerun-1' } } } }
  const api = sourceLoader({ 'infrastructure/api/client': { default: client } })('infrastructure/api/reportApi').reportApi
  assert.deepEqual(await api.trigger({ rerun_latest: true }), { job_id: 'rerun-1' })
  assert.deepEqual(calls, [['/trigger/', { rerun_latest: true }]])
})

test('Windows Ctrl+R and Mac Cmd+R suppress reload and request the last generated report queries', (t) => {
  const state = setup(t)
  assert.equal(state.key({ ctrlKey: true }).defaultPrevented, true)
  assert.equal(state.key({ metaKey: true, key: 'R' }).defaultPrevented, true)
  act(() => state.refresh())
  assert.deepEqual(state.requests, [{ rerun_latest: true }, { rerun_latest: true }, { rerun_latest: true }])
})

test('daily report refresh delegates saved dates to the latest-report selector', (t) => {
  const state = setup(t, { lastRequest: { period: 'day', date: '2024-02-29' } })
  assert.equal(state.key({ ctrlKey: true }).defaultPrevented, true)
  assert.deepEqual(state.requests, [{ rerun_latest: true }])
})

test('native reload variants and unrelated keys retain their default behavior', (t) => {
  const state = setup(t)
  for (const shortcut of [
    {},
    { key: 'F5' },
    { ctrlKey: true, shiftKey: true },
    { metaKey: true, shiftKey: true },
    { ctrlKey: true, altKey: true },
    { metaKey: true, altKey: true },
    { ctrlKey: true, metaKey: true },
    { ctrlKey: true, key: 'f' },
    { ctrlKey: true, isComposing: true },
  ]) assert.equal(state.key(shortcut).defaultPrevented, false)
  state.key({ ctrlKey: true, defaultPrevented: true })
  assert.equal(state.requests.length, 0)
})

test('held shortcut keys and pending generation suppress reload without another request', (t) => {
  const state = setup(t)
  assert.equal(state.key({ ctrlKey: true, repeat: true }).defaultPrevented, true)
  assert.equal(state.requests.length, 0)
  state.generation.pending = true
  state.update()
  assert.equal(state.key({ metaKey: true }).defaultPrevented, true)
  act(() => state.refresh())
  assert.equal(state.requests.length, 0)
  state.generation.pending = false
  state.update()
  state.key({ ctrlKey: true })
  assert.deepEqual(state.requests, [{ rerun_latest: true }])
})

test('disabled and unmounted dashboards unregister the browser reload override', (t) => {
  const state = setup(t)
  assert.equal(state.listeners.size, 1)
  state.update(false)
  assert.equal(state.listeners.size, 0)
  assert.equal(state.key({ ctrlKey: true }).defaultPrevented, false)
  state.update(true)
  assert.equal(state.listeners.size, 1)
  state.unmount()
  assert.equal(state.listeners.size, 0)
  assert.equal(state.key({ metaKey: true }).defaultPrevented, false)
  assert.equal(state.requests.length, 0)
})

test('shortcut ignores unsaved form selections, deduplicates jobs, and replaces the complete report after success', async (t) => {
  const keys = keyboard()
  const requests = []
  const navigation = []
  const previous = {
    id: 7, scope: 'standard', report_year: null, week_start: '2026-10-05', week_end: '2026-10-09',
    widgets: { w1: { total: 1 }, w7: { total: 1 } },
  }
  const created = { ...previous, id: 8, widgets: { w1: { total: 3 }, w7: { total: 2 } } }
  let stream
  const load = sourceLoader({
    'react-router-dom': { useLocation: () => ({ pathname: '/' }), useNavigate: () => (url) => navigation.push(url) },
  })
  const { ApplicationServicesProvider } = load('presentation/context/ApplicationServicesContext')
  const { ReportGenerationProvider, useReportGeneration } = load('presentation/context/ReportGenerationContext')
  const { useReportRefreshShortcut } = load('presentation/hooks/useReportRefreshShortcut')
  const Form = load('presentation/components/common/DashboardGenerateForm').default
  const reports = {
    trigger: async (request) => { requests.push(request); return { job_id: 'rerun-1' } },
    watchJob: (jobId, callbacks) => { stream = { jobId, callbacks }; return { close() {} } },
    getById: async (id) => { assert.equal(id, created.id); return created },
  }
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } })
  client.setQueryData(['reports', 'latest'], previous)
  let generation
  function Probe() {
    generation = useReportGeneration()
    useReportRefreshShortcut()
    return React.createElement(Form, { report: previous })
  }
  let view
  t.after(() => { if (view) act(() => view.unmount()); client.clear(); keys.restore() })
  act(() => {
    view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { reports } },
      React.createElement(QueryClientProvider, { client }, React.createElement(ReportGenerationProvider, null, React.createElement(Probe)))))
  })
  act(() => view.root.findAllByType('button').find((node) => textOf(node) === '월간').props.onClick())
  act(() => view.root.findByType('input').props.onChange({ target: { value: '2026-09-20' } }))
  assert.equal(keys.key({ ctrlKey: true }).defaultPrevented, true)
  assert.equal(keys.key({ metaKey: true }).defaultPrevented, true)
  await until(() => stream)
  assert.deepEqual(requests, [{ rerun_latest: true }])
  assert.equal(generation.lastRequest, null)
  assert.equal(generation.pending, true)
  assert.equal(view.root.findByType('input').props.value, '2026-09-20')
  assert.equal(client.getQueryData(['reports', 'latest']), previous)
  act(() => stream.callbacks.onComplete(created.id))
  await until(() => !generation.pending)
  assert.deepEqual(client.getQueryData(['reports', 'latest']), created)
  assert.deepEqual(client.getQueryData(['reports', created.id]), created)
  assert.deepEqual(navigation, ['/reports/8'])
  assert.equal(view.root.findByType('input').props.value, '2026-09-20')
  assert.equal(view.root.findAllByType('button').find((node) => textOf(node) === '월간').props['aria-pressed'], true)
})
