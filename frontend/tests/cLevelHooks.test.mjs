// frontend/tests/cLevelHooks.test.mjs
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
const modules = new Map()
function load(relative) {
  const base = path.join(sourceRoot, relative)
  const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
  assert.ok(filename, `Missing module ${relative}`)
  if (modules.has(filename)) return modules.get(filename).exports
  const module = { exports: {} }
  modules.set(filename, module)
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX }, fileName: filename }).outputText
  new Function('require', 'module', 'exports', compiled)((dependency) => {
    if (dependency.startsWith('@/')) return load(dependency.slice(2))
    if (dependency.startsWith('.')) return load(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)))
    return require(dependency)
  }, module, module.exports)
  return module.exports
}
const { ApplicationServicesProvider } = load('presentation/context/ApplicationServicesContext')
const { useCLevelReport, cLevelQueryKey } = load('presentation/hooks/useCLevelReport')
const { useCLevelExport } = load('presentation/hooks/useCLevelExport')
function deferred() { let resolve; const promise = new Promise((done) => { resolve = done }); return { promise, resolve } }
async function settle() { await act(async () => { await new Promise((resolve) => setTimeout(resolve, 15)) }) }

test('late refresh writes its requested period cache and cannot overwrite the newly selected period', async () => {
  const refresh = deferred()
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity }, mutations: { gcTime: Infinity } } })
  const gateway = { getReport: async (period, date, force) => force ? refresh.promise : { period, date, report_token: date, comments: {} } }
  let observed
  function Probe({ date }) { observed = useCLevelReport('week', date); return null }
  const element = (date) => React.createElement(ApplicationServicesProvider, { services: { cLevelReport: gateway } }, React.createElement(QueryClientProvider, { client: queryClient }, React.createElement(Probe, { date })))
  let view
  await act(async () => { view = TestRenderer.create(element('2026-10-06')) })
  await settle()
  act(() => observed.refresh.mutate())
  await act(async () => view.update(element('2026-10-13')))
  await settle()
  await act(async () => refresh.resolve({ period: 'week', date: '2026-10-06', report_token: 'refreshed', comments: {} }))
  await settle()
  assert.equal(observed.report.data.date, '2026-10-13')
  assert.equal(queryClient.getQueryData(cLevelQueryKey('week', '2026-10-06')).report_token, 'refreshed')
  assert.equal(queryClient.getQueryData(cLevelQueryKey('week', '2026-10-13')).report_token, '2026-10-13')
  act(() => view.unmount())
  queryClient.clear()
})

test('late comment save updates only its frozen report and sends its original token', async () => {
  const saving = deferred()
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity }, mutations: { gcTime: Infinity } } })
  const calls = []
  const gateway = { getReport: async (_, date) => ({ report_token: date, comments: {} }), saveComment: (...args) => { calls.push(args); return saving.promise } }
  let observed
  function Probe({ date }) { observed = useCLevelReport('week', date); return null }
  const element = (date) => React.createElement(ApplicationServicesProvider, { services: { cLevelReport: gateway } }, React.createElement(QueryClientProvider, { client: queryClient }, React.createElement(Probe, { date })))
  let view
  await act(async () => { view = TestRenderer.create(element('2026-10-06')) })
  await settle()
  const input = { delay_reason: 'old period', action_taken: '', prevention_plan: '', included: true }
  let completion
  act(() => { completion = observed.comment.mutateAsync({ key: 'TACEA-1', input }) })
  await act(async () => view.update(element('2026-10-13')))
  await settle()
  await act(async () => { saving.resolve(input); await completion })
  assert.equal(calls[0][1], '2026-10-06')
  assert.deepEqual(queryClient.getQueryData(cLevelQueryKey('week', '2026-10-06')).comments['TACEA-1'], input)
  assert.deepEqual(queryClient.getQueryData(cLevelQueryKey('week', '2026-10-13')).comments, {})
  act(() => view.unmount())
  queryClient.clear()
})

test('changing the report period aborts the previous network signal', async () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } })
  const calls = []
  const gateway = { getReport: (_, date, refresh, signal) => { calls.push({ date, signal }); return new Promise(() => {}) } }
  function Probe({ date }) { useCLevelReport('week', date); return null }
  const element = (date) => React.createElement(ApplicationServicesProvider, { services: { cLevelReport: gateway } }, React.createElement(QueryClientProvider, { client: queryClient }, React.createElement(Probe, { date })))
  let view
  await act(async () => { view = TestRenderer.create(element('2026-10-06')) })
  await act(async () => view.update(element('2026-10-13')))
  assert.equal(calls[0].signal.aborted, true)
  assert.equal(calls[1].signal.aborted, false)
  act(() => view.unmount())
  assert.equal(calls[1].signal.aborted, true)
  queryClient.clear()
})

test('export completion after unmount cannot create or trigger a file download', async () => {
  const rendering = deferred()
  let observed
  let objectUrls = 0
  function Probe() { observed = useCLevelExport(); return null }
  let view
  act(() => { view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { dashboardExport: { renderPdf: () => rendering.promise } } }, React.createElement(Probe))) })
  let completion
  act(() => { completion = observed.download({}, 'pdf', 'report') })
  act(() => view.unmount())
  rendering.resolve({ createObjectUrl() { objectUrls++; return { url: 'url', close() {} } } })
  await completion
  assert.equal(objectUrls, 0)
})

test('export releases active object URLs and timers on unmount', async () => {
  const previousWindow = globalThis.window
  let clicks = 0
  let removed = 0
  let closed = 0
  let observed
  globalThis.window = { document: { createElement: () => ({ click() { clicks++ }, remove() { removed++ } }), body: { appendChild() {} } } }
  function Probe() { observed = useCLevelExport(); return null }
  let view
  try {
    act(() => { view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { dashboardExport: { renderExcel: async () => ({ createObjectUrl: () => ({ url: 'blob:example', close() { closed++ } }) }) } } }, React.createElement(Probe))) })
    await act(async () => observed.download({}, 'xlsx', 'report'))
    assert.equal(clicks, 1)
    assert.equal(removed, 1)
    assert.equal(observed.pending, false)
    act(() => view.unmount())
    assert.equal(closed, 1)
  } finally { globalThis.window = previousWindow }
})
