// frontend/tests/auditLogs.test.mjs
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
const { create } = require('zustand')
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
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX }, fileName: filename,
    }).outputText
    new Function('require', 'module', 'exports', compiled)((dependency) => {
      if (dependency.startsWith('@/')) return load(dependency.slice(2))
      if (dependency.startsWith('.')) return load(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)).replaceAll('\\', '/'))
      return require(dependency)
    }, module, module.exports)
    return module.exports
  }
  return load
}

const load = sourceLoader()
const { canViewAuditLogs } = load('domain/Auth')
const { auditDefaultFilters, auditFilterError, auditLogQuery, visibleAuditDetails } = load('application/services/auditLog')
const { RequestError } = load('application/errors/RequestError')
const superadmin = { username: 'configured-owner', login_required: true, is_superadmin: true }
const ordinary = { username: 'admin', login_required: true, is_superadmin: false }
const entries = { items: [{ timestamp: '2026-10-13T12:00:00+09:00', event: 'REPORT_DELETE', username: null, ip: null, details: { report_id: '42' } }], total: 1, limit: 50, offset: 0, events: ['REPORT_DELETE'], warnings: [] }
const request = { limit: 50, offset: 0 }

function deferred() {
  let resolve
  let reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

async function settle() {
  await act(async () => { await new Promise((resolve) => setTimeout(resolve, 20)) })
}

async function until(predicate) {
  const deadline = Date.now() + 2000
  while (!predicate()) {
    assert.ok(Date.now() < deadline, 'Timed out waiting for query state')
    await settle()
  }
}

function setup(t, { me = async () => superadmin, getLogs = async () => entries, token = 'owner-session' } = {}) {
  const store = create((set) => ({ accessToken: token, username: 'untrusted-local-name', setAuth: (accessToken, username) => set({ accessToken, username }), clearAuth: () => set({ accessToken: null, username: null }), setLoginRequired: () => {} }))
  const instance = sourceLoader({ 'presentation/state/authStore': { useAuthStore: store } })
  const { ApplicationServicesProvider } = instance('presentation/context/ApplicationServicesContext')
  const { useAuditLogs } = instance('presentation/hooks/useAuditLogs')
  const { useMe } = instance('presentation/hooks/useAuth')
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  let observed
  let auth
  function Probe() { auth = useMe(); observed = useAuditLogs(request); return null }
  const element = React.createElement(ApplicationServicesProvider, { services: { auth: { me }, auditLogs: { getLogs } } }, React.createElement(QueryClientProvider, { client }, React.createElement(Probe)))
  let view
  act(() => { view = TestRenderer.create(element) })
  t.after(() => { act(() => view.unmount()); client.clear() })
  return { store, client, get observed() { return observed }, get auth() { return auth } }
}

test('audit authority requires an authenticated explicit server role and never infers authority from usernames', () => {
  assert.equal(canViewAuditLogs(superadmin), true)
  for (const me of [undefined, ordinary, { username: 'root', login_required: true }, { ...superadmin, is_superadmin: 'true' }, { ...superadmin, login_required: false }]) {
    assert.equal(canViewAuditLogs(me), false)
  }
})

test('audit filters use KST calendar dates and reject inverted ranges', () => {
  const filters = auditDefaultFilters(new Date('2026-10-12T16:00:00Z'))
  assert.equal(filters.start_date, '2026-10-07')
  assert.equal(filters.end_date, '2026-10-13')
  assert.equal(auditFilterError(filters), null)
  assert.match(auditFilterError({ ...filters, start_date: '2026-11-01' }), /시작일/)
  assert.equal(auditFilterError({ ...filters, start_date: '', end_date: '' }), null)
})

test('audit query preserves independent filters, trims optional text and resets negative pagination', () => {
  const filters = { start_date: '2026-10-01', end_date: '', event: ' REPORT_DELETE ', username: ' admin ', ip: '127.0.0.', search: ' 42 ' }
  assert.deepEqual(auditLogQuery(filters, 2), { limit: 50, offset: 100, start_date: '2026-10-01', event: 'REPORT_DELETE', username: 'admin', ip: '127.0.0.', search: '42' })
  assert.equal(auditLogQuery(filters, -1).offset, 0)
})

test('audit details suppress credential-shaped fields while retaining operational evidence', () => {
  assert.deepEqual(visibleAuditDetails({ report_id: '42', path: '/reports', Password: 'hidden', refresh_token: 'hidden', JWT_SECRET: 'hidden', authorization: 'hidden', Cookie: 'hidden', privateKey: 'hidden' }), [['report_id', '42'], ['path', '/reports']])
})

test('audit API forwards pagination filters and cancellation and propagates authorization errors', async () => {
  const calls = []
  const instance = sourceLoader({ 'infrastructure/api/client': { default: { get: async (...args) => { calls.push(args); return { data: entries } } } } })
  const { auditLogApi } = instance('infrastructure/api/auditLogApi')
  const controller = new AbortController()
  const query = { ...request, event: 'LOGIN_FAILED', username: 'admin', search: 'attempt' }
  assert.equal(await auditLogApi.getLogs(query, controller.signal), entries)
  assert.deepEqual(calls[0], ['/audit-logs', { params: query, signal: controller.signal }])
  const denied = new RequestError(403, 'Forbidden')
  const failed = sourceLoader({ 'infrastructure/api/client': { default: { get: async () => { throw denied } } } })('infrastructure/api/auditLogApi').auditLogApi
  await assert.rejects(failed.getLogs(request), (error) => error === denied)
})

test('audit fetching waits for server role and ordinary users cannot trigger a request', async (t) => {
  const pending = deferred()
  let calls = 0
  const state = setup(t, { me: () => pending.promise, getLogs: async () => { calls += 1; return entries } })
  assert.equal(state.observed.allowed, false)
  assert.equal(calls, 0)
  await act(async () => pending.resolve(ordinary))
  await settle()
  assert.equal(state.observed.allowed, false)
  assert.equal(state.observed.data, undefined)
  assert.equal(calls, 0)
})

test('a failed role lookup never starts audit requests', async (t) => {
  let calls = 0
  const state = setup(t, { me: async () => { throw new RequestError(401, 'Expired') }, getLogs: async () => { calls += 1; return entries } })
  await until(() => state.auth.isError)
  assert.equal(state.observed.allowed, false)
  assert.equal(calls, 0)
})

test('switching from administrator to normal user immediately hides old audit data and authority', async (t) => {
  let calls = 0
  let meCalls = 0
  const normalRole = deferred()
  const state = setup(t, { me: async () => ++meCalls === 1 ? superadmin : normalRole.promise, getLogs: async () => { calls += 1; return entries } })
  await until(() => state.observed.data)
  assert.equal(calls, 1)
  act(() => state.store.getState().setAuth('normal-session', 'admin'))
  assert.equal(state.auth.data, undefined)
  assert.equal(state.observed.data, undefined)
  assert.equal(state.observed.allowed, false)
  await act(async () => normalRole.resolve(ordinary))
  await settle()
  assert.equal(state.observed.data, undefined)
  assert.equal(state.observed.allowed, false)
  assert.equal(calls, 1)
  assert.equal(state.client.getQueryCache().findAll({ queryKey: ['audit-logs', 'owner-session'] }).length, 0)
})

test('logout cancels in-flight audit query and a late response cannot expose its data', async (t) => {
  const pending = deferred()
  let signal
  const state = setup(t, { getLogs: (_, cancellation) => { signal = cancellation; return pending.promise } })
  await until(() => signal)
  act(() => state.store.getState().clearAuth())
  assert.equal(signal.aborted, true)
  assert.equal(state.observed.data, undefined)
  await act(async () => pending.resolve(entries))
  await settle()
  assert.equal(state.observed.data, undefined)
  assert.equal(state.observed.allowed, false)
})

test('403 refresh removes a previously visible page and does not retry', async (t) => {
  let calls = 0
  const state = setup(t, { getLogs: async () => { if (++calls > 1) throw new RequestError(403, 'Forbidden'); return entries } })
  await until(() => state.observed.data)
  await act(async () => { await state.observed.refetch() })
  await until(() => state.observed.isError)
  assert.equal(state.observed.data, undefined)
  assert.equal(calls, 2)
})

test('administrator route blocks missing and ordinary roles but renders the configured administrator', () => {
  for (const [me, expected] of [[undefined, false], [ordinary, false], [superadmin, true]]) {
    const instance = sourceLoader({ 'presentation/hooks/useAuth': { useMe: () => ({ data: me, isError: false, isLoading: false }) } })
    const Route = instance('presentation/components/auth/SuperadminRoute').default
    const { MemoryRouter } = require('react-router-dom')
    let view
    act(() => { view = TestRenderer.create(React.createElement(MemoryRouter, null, React.createElement(Route, null, React.createElement('p', { id: 'restricted' }, 'Audit data')))) })
    assert.equal(view.root.findAllByProps({ id: 'restricted' }).length === 1, expected)
    act(() => view.unmount())
  }
})

test('audit page renders missing actors, warnings and safe details and blocks inverted date submissions', () => {
  let refreshes = 0
  const current = { allowed: true, data: { ...entries, warnings: ['이전 로그 일부는 사용자를 확인할 수 없습니다.'] }, isError: false, isPending: false, isFetching: false, refetch: () => { refreshes += 1 } }
  const instance = sourceLoader({ 'presentation/hooks/useAuditLogs': { useAuditLogs: () => current } })
  const Page = instance('presentation/pages/AuditLogPage').default
  const { MemoryRouter } = require('react-router-dom')
  let view
  act(() => { view = TestRenderer.create(React.createElement(MemoryRouter, null, React.createElement(Page))) })
  const rendered = JSON.stringify(view.toJSON())
  assert.match(rendered, /확인 불가/)
  assert.match(rendered, /report_id/)
  assert.match(rendered, /한국 표준시/)
  const dates = view.root.findAllByProps({ type: 'date' })
  act(() => dates[0].props.onChange({ target: { value: '2026-11-01' } }))
  act(() => dates[1].props.onChange({ target: { value: '2026-10-01' } }))
  act(() => view.root.findByType('form').props.onSubmit({ preventDefault() {} }))
  assert.match(JSON.stringify(view.toJSON()), /시작일은 종료일보다/)
  assert.equal(refreshes, 0)
  act(() => view.unmount())
})

test('audit pagination stops at the server limit and guides users to narrow the date range', () => {
  const requests = []
  const current = { allowed: true, data: { ...entries, total: 5001 }, isError: false, isPending: false, isFetching: false, refetch() {} }
  const instance = sourceLoader({ 'presentation/hooks/useAuditLogs': { useAuditLogs: (query) => { requests.push(query); return current } } })
  const Page = instance('presentation/pages/AuditLogPage').default
  const { MemoryRouter } = require('react-router-dom')
  let view
  const textOf = (node) => typeof node === 'string' || typeof node === 'number' ? String(node) : node.children.map(textOf).join('')
  act(() => { view = TestRenderer.create(React.createElement(MemoryRouter, null, React.createElement(Page))) })
  assert.match(textOf(view.root), /최대 100페이지/)
  assert.match(textOf(view.root), /날짜 범위를 좁혀/)
  const next = () => view.root.findAllByType('button').find((button) => textOf(button) === '다음')
  for (let page = 1; page < 100; page += 1) {
    assert.equal(next().props.disabled, false)
    act(() => next().props.onClick())
  }
  assert.equal(next().props.disabled, true)
  assert.match(textOf(view.root), /100 \/ 100 페이지/)
  assert.equal(requests.at(-1).offset, 4950)
  assert.equal(requests.every((query) => query.offset < query.limit * 100), true)
  act(() => view.unmount())
})
