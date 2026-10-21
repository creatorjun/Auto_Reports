// frontend/tests/reportMutationSession.test.mjs
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
    const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX }, fileName: filename }).outputText
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

function deferred() {
  let resolve
  let reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

async function settle() { await act(async () => { await new Promise((resolve) => setTimeout(resolve, 10)) }) }
async function until(predicate) {
  const deadline = Date.now() + 2500
  while (!predicate()) { assert.ok(Date.now() < deadline, 'Timed out waiting for generation state'); await settle() }
}

const cases = [
  { name: 'SLA violations', module: 'presentation/hooks/useSlaViolations', hook: 'useGenerateSlaViolationReport', service: 'slaViolations', report: { id: 20 }, key: ['sla-violations', 'latest'] },
  { name: 'redeployment', module: 'presentation/hooks/useRedeployments', hook: 'useRefreshRedeployments', service: 'redeployments', report: { id: 30 }, key: ['redeployments', 'latest'] },
]

function setup(t, item, gateway = {}) {
  const load = sourceLoader()
  const { ApplicationServicesProvider } = load('presentation/context/ApplicationServicesContext')
  const { useAuthStore } = load('presentation/state/authStore')
  const useMutation = load(item.module)[item.hook]
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } })
  useAuthStore.getState().setAuth('first-token', 'user')
  let observed, view, calls = 0
  function Probe() { observed = useMutation(); return null }
  const service = { generate: async () => { calls += 1; return item.report }, ...gateway }
  act(() => { view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { [item.service]: service } }, React.createElement(QueryClientProvider, { client }, React.createElement(Probe)))) })
  t.after(() => { act(() => view.unmount()); client.clear() })
  return { client, auth: useAuthStore, unmount: () => act(() => view.unmount()), get calls() { return calls }, get observed() { return observed } }
}

for (const item of cases) {
  test(`${item.name} does not repopulate cleared caches after logout during completion`, async (t) => {
    const state = setup(t, item)
    const cancellation = deferred()
    let cancellations = 0
    state.client.cancelQueries = () => ++cancellations === 1 ? Promise.resolve() : cancellation.promise
    act(() => state.observed.mutate({ period: 'week', date: '2026-10-14' }))
    await until(() => cancellations === 2)
    act(() => state.auth.getState().clearAuth())
    state.client.clear()
    cancellation.resolve()
    await until(() => !state.observed.isPending)
    assert.equal(state.client.getQueryCache().getAll().length, 0)
  })

  test(`${item.name} does not start generation if logout occurs during preflight`, async (t) => {
    const state = setup(t, item)
    const cancellation = deferred()
    let started = false
    state.client.cancelQueries = () => { started = true; return cancellation.promise }
    act(() => state.observed.mutate({ period: 'week', date: '2026-10-14' }))
    await until(() => started)
    act(() => state.auth.getState().clearAuth())
    cancellation.resolve()
    await until(() => state.observed.isError)
    assert.equal(state.calls, 0)
  })

  test(`${item.name} preserves completion after ordinary navigation and token refresh`, async (t) => {
    const result = deferred()
    const state = setup(t, item, { generate: () => result.promise })
    act(() => state.observed.mutate({ period: 'week', date: '2026-10-14' }))
    await settle()
    state.unmount()
    state.auth.getState().setAuth('refreshed-token', 'user')
    result.resolve(item.report)
    await until(() => state.client.getQueryData(item.key))
    assert.deepEqual(state.client.getQueryData(item.key), item.report)
  })
}

for (const [name, module, hook, key] of [
  ['securityNews', 'presentation/hooks/useSecurityNews', 'useSecurityNews', ['security-news']],
  ['slaStatus', 'presentation/hooks/useSlaStatus', 'useSlaStatus', ['sla-status']],
]) {
  test(`${name} manual refresh cannot restore cache after logout`, async (t) => {
    const oldWindow = globalThis.window
    globalThis.window = { setInterval, clearInterval }
    const load = sourceLoader()
    const { ApplicationServicesProvider } = load('presentation/context/ApplicationServicesContext')
    const { useAuthStore } = load('presentation/state/authStore')
    const useRefresh = load(module)[hook]
    const result = deferred()
    const initial = { refreshing: false, refresh_in_progress: false, retry_after_seconds: 0 }
    let refreshes = 0
    let reads = 0
    const readSnapshot = () => ++reads === 1 ? Promise.resolve(initial) : new Promise(() => {})
    const service = name === 'securityNews'
      ? { getSnapshot: readSnapshot, refresh: () => { refreshes += 1; return result.promise } }
      : { getSnapshot: (refresh) => { if (!refresh) return readSnapshot(); refreshes += 1; return result.promise } }
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } })
    let observed, view
    function Probe() { observed = useRefresh(); return null }
    act(() => { view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { [name]: service } }, React.createElement(QueryClientProvider, { client }, React.createElement(Probe)))) })
    t.after(() => { act(() => view.unmount()); client.clear(); globalThis.window = oldWindow })
    await until(() => observed.data === initial)
    act(() => observed.refresh())
    await until(() => refreshes === 1)
    act(() => useAuthStore.getState().clearAuth())
    client.clear()
    result.resolve({ ...initial, id: 'old-session-data' })
    await settle()
    assert.equal(client.getQueryData(key), undefined)
  })
}
