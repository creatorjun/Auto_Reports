// frontend/tests/jiraNotifications.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import { MemoryRouter } from 'react-router-dom'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query')
const { create } = require('zustand')
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')

function sourceLoader(overrides = {}) {
  const modules = new Map()
  function load(relative) {
    if (Object.hasOwn(overrides, relative)) return overrides[relative]
    const base = path.join(root, relative)
    const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
    assert.ok(filename, `Missing module ${relative}`)
    if (filename.endsWith('.json')) return JSON.parse(fs.readFileSync(filename, 'utf8'))
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX }, fileName: filename,
    }).outputText
    new Function('require', 'module', 'exports', compiled)((dependency) => {
      if (dependency.startsWith('@/')) return load(dependency.slice(2))
      if (dependency.startsWith('.')) return load(path.relative(root, path.resolve(path.dirname(filename), dependency)).replaceAll('\\', '/'))
      return require(dependency)
    }, module, module.exports)
    return module.exports
  }
  return load
}

const load = sourceLoader()
const { canViewJiraNotifications } = load('domain/Auth')
const { jiraNotificationItems, safeJiraNotificationUrl } = load('application/services/jiraNotifications')
const jira = { username: 'jira:cloud:account-a', display_name: '동일 이름', email_address: 'jira-user@example.test', auth_provider: 'jira', login_required: true, is_superadmin: false }
function item(overrides = {}) { return { id: 'notification-a', title: '담당자가 변경되었습니다', message: '실제 Jira 알림', url: 'https://jira.example.test/browse/TAC-1', actor: '동료', created_at: '2026-10-21T03:00:00Z', category: 'direct', is_read: false, group_size: 1, ...overrides } }
function page(items = [item()], next_cursor = null, connection_status = 'connected') { return { items, next_cursor, connection_status } }
function deferred() { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no }); return { promise, resolve, reject } }
async function until(predicate) { const deadline = Date.now() + 3000; while (!predicate()) { assert.ok(Date.now() < deadline, 'Timed out waiting for state'); await act(async () => { await new Promise((resolve) => setTimeout(resolve, 15)) }) } }
function makeStore(token = 'session-a') { return create((set) => ({ accessToken: token, username: '동일 이름', loginRequired: true, setAuth: (accessToken) => set({ accessToken }), clearAuth: () => set({ accessToken: null }), setLoginRequired() {} })) }

function setupHook(t, { me = async () => jira, getNotifications = async () => page(), token = 'session-a' } = {}) {
  const store = makeStore(token)
  const instance = sourceLoader({ 'presentation/state/authStore': { useAuthStore: store } })
  const { ApplicationServicesProvider } = instance('presentation/context/ApplicationServicesContext')
  const { useJiraNotifications } = instance('presentation/hooks/useJiraNotifications')
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  let observed, view
  function Probe({ category }) { observed = useJiraNotifications(category); return null }
  const element = (category) => React.createElement(ApplicationServicesProvider, { services: { auth: { me }, jiraNotifications: { getNotifications } } }, React.createElement(QueryClientProvider, { client }, React.createElement(Probe, { category })))
  act(() => { view = TestRenderer.create(element('all')) })
  t.after(() => { act(() => view.unmount()); client.clear() })
  return { store, client, category(value) { act(() => view.update(element(value))) }, unmount() { act(() => view.unmount()) }, get observed() { return observed } }
}

function setupSidebar(t, { me = async () => jira, getNotifications = async () => page(), startJira = async () => ({ authorization_url: 'https://auth.example.test/authorize' }), collapsed = false, mobileOpen = false, layout = false } = {}) {
  const previous = { document: globalThis.document, Node: globalThis.Node, window: globalThis.window }
  const listeners = new Map()
  class NodeStub { isConnected = true; focused = 0; focus() { this.focused++ } contains(target) { return target === this } }
  globalThis.Node = NodeStub
  globalThis.document = { addEventListener: (name, callback) => listeners.set(name, callback), removeEventListener: (name, callback) => { if (listeners.get(name) === callback) listeners.delete(name) } }
  const redirects = []
  globalThis.window = { location: { assign: (url) => redirects.push(url) } }
  const store = makeStore()
  const instance = sourceLoader({
    'presentation/state/authStore': { useAuthStore: store },
    'presentation/state/reportStore': { useReportStore: () => ({ currentReport: null }) },
    'presentation/state/uiStore': { useUiStore: () => ({ triggerMessage: null }) },
    'presentation/components/common/BrandLogo': { default: () => React.createElement('div', null, 'SecuLayer') },
    'presentation/components/common/SearchWidget': { default: () => React.createElement('input', { 'aria-label': '검색' }) },
    'presentation/components/layout/ThemeToggle': { default: () => React.createElement('button', null, '테마') },
    'presentation/context/JiraContext': { JiraProvider: ({ children }) => children },
    'presentation/context/ReportGenerationContext': { ReportGenerationProvider: ({ children }) => children },
    'presentation/components/layout/Header': { default: () => null },
  })
  const { ApplicationServicesProvider } = instance('presentation/context/ApplicationServicesContext')
  const Sidebar = instance('presentation/components/layout/Sidebar').default
  const Layout = instance('presentation/components/layout/Layout').default
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } } })
  const trigger = new NodeStub()
  const panel = new NodeStub()
  let view
  const element = (props) => React.createElement(ApplicationServicesProvider, { services: { auth: { me, startJira, logout: async () => {} }, jiraNotifications: { getNotifications } } }, React.createElement(QueryClientProvider, { client }, React.createElement(MemoryRouter, null, layout ? React.createElement(Layout) : React.createElement(Sidebar, { collapsed, mobileOpen, setCollapsed: () => {}, ...props }))))
  act(() => { view = TestRenderer.create(element(), { createNodeMock: ({ props }) => props.role === 'dialog' ? panel : null }) })
  t.after(() => { act(() => view.unmount()); client.clear(); Object.assign(globalThis, previous) })
  return { view, client, store, trigger, panel, redirects, listeners, update(props) { act(() => view.update(element(props))) }, outside: () => new NodeStub(), open() { act(() => view.root.findByProps({ 'aria-label': 'Jira 알림' }).props.onClick({ currentTarget: trigger })) } }
}

test('Jira notification eligibility requires explicit verified Jira login', () => {
  assert.equal(canViewJiraNotifications(jira), true)
  for (const me of [undefined, { ...jira, login_required: false }, { ...jira, auth_provider: 'local', is_superadmin: true }, { ...jira, auth_provider: undefined }, { ...jira, auth_provider: 'JIRA' }]) assert.equal(canViewJiraNotifications(me), false)
})

test('pages deduplicate IDs and reconnect pages suppress every previously loaded item; unsafe URLs never become links', () => {
  assert.deepEqual(jiraNotificationItems([page(), page([item(), item({ id: 'b' })])]).map((row) => row.id), ['notification-a', 'b'])
  assert.deepEqual(jiraNotificationItems([page(), page([item()], null, 'reconnect_required')]), [])
  for (const url of [null, 'javascript:alert(1)', '//evil.test', '/relative', 'http://jira.example.test', 'https://user:pass@example.test']) assert.equal(safeJiraNotificationUrl(url), null)
  assert.equal(safeJiraNotificationUrl('https://jira.example.test/browse/TAC-1'), 'https://jira.example.test/browse/TAC-1')
})

test('notification adapter forwards only category/cursor and cancellation through the shared client', async () => {
  const calls = []
  const response = page()
  const instance = sourceLoader({ 'infrastructure/api/client': { default: { async get(...args) { calls.push(args); return { data: response } } } } })
  const { jiraNotificationApi } = instance('infrastructure/api/jiraNotificationApi')
  const signal = new AbortController().signal
  assert.equal(await jiraNotificationApi.getNotifications({ category: 'watching', cursor: 'opaque/+=' }, signal), response)
  assert.deepEqual(calls, [['/jira/notifications', { params: { category: 'watching', cursor: 'opaque/+=' }, signal }]])
  assert.deepEqual(Object.keys(jiraNotificationApi), ['getNotifications'])
})

test('feed waits for server identity, and local, guest or failed identity never starts requests', async (t) => {
  const identity = deferred()
  let calls = 0
  const state = setupHook(t, { me: () => identity.promise, getNotifications: async () => { calls++; return page() } })
  assert.equal(calls, 0)
  await act(async () => identity.resolve(jira))
  await until(() => state.observed.items.length === 1)
  assert.equal(calls, 1)
  for (const profile of [{ ...jira, auth_provider: 'local' }, { ...jira, login_required: false }]) {
    const blocked = setupHook(t, { me: async () => profile, getNotifications: async () => { throw new Error('must not fetch') } })
    await until(() => blocked.client.getQueryState(['me', 'session-a'])?.status === 'success')
    assert.equal(blocked.observed.allowed, false)
    assert.deepEqual(blocked.observed.items, [])
  }
  const failed = setupHook(t, { me: async () => { throw new Error('unavailable') }, getNotifications: async () => { throw new Error('must not fetch') } })
  await until(() => failed.client.getQueryState(['me', 'session-a'])?.status === 'error')
  assert.equal(failed.observed.allowed, false)
})

test('pagination uses server cursor, deduplicates notifications, stops repeated cursors, and refresh restarts from first page', async (t) => {
  const calls = []
  const state = setupHook(t, { getNotifications: async (request) => { calls.push(request); return request.cursor ? page([item(), item({ id: 'b' })], 'next') : page([item()], 'next') } })
  await until(() => state.observed.items.length === 1)
  act(() => { state.observed.loadMore(); state.observed.loadMore() })
  await until(() => state.observed.items.length === 2)
  assert.deepEqual(calls, [{ category: 'all' }, { category: 'all', cursor: 'next' }])
  assert.equal(state.observed.hasMore, false)
  await act(async () => state.observed.refresh())
  assert.deepEqual(state.client.getQueryData(['jira-notifications', 'session-a', 'all']).pageParams, [null])
  await until(() => state.observed.items.length === 1 && !state.observed.isFetching)
  assert.deepEqual(calls.at(-1), { category: 'all' })
  assert.deepEqual(state.observed.items.map((row) => row.id), ['notification-a'])
  state.category('direct')
  await until(() => calls.at(-1).category === 'direct' && !state.observed.isFetching)
  assert.deepEqual(calls.at(-1), { category: 'direct' })
})

test('pagination errors and reconnect responses hide all previous notifications', async (t) => {
  let fail = true
  const state = setupHook(t, { getNotifications: async ({ cursor }) => { if (!cursor) return page([item()], 'next'); if (fail) throw new Error('feed unavailable'); return page([], null, 'reconnect_required') } })
  await until(() => state.observed.items.length === 1)
  act(() => state.observed.loadMore())
  await until(() => state.observed.isError)
  assert.deepEqual(state.observed.items, [])
  assert.equal(state.observed.hasMore, false)
  fail = false
  await act(async () => state.observed.refresh())
  await until(() => state.observed.items.length === 1)
  act(() => state.observed.loadMore())
  await until(() => state.observed.reconnectRequired)
  assert.deepEqual(state.observed.items, [])
  assert.equal(state.observed.hasMore, false)
})

test('session token changes cancel old requests and do not expose same-display-name account data', async (t) => {
  const old = deferred()
  let calls = 0, oldSignal
  const state = setupHook(t, { getNotifications(_request, signal) { calls++; if (calls === 1) { oldSignal = signal; return old.promise } return Promise.resolve(page([item({ id: 'account-b' })])) } })
  await until(() => calls === 1)
  act(() => state.store.getState().setAuth('session-b'))
  assert.deepEqual(state.observed.items, [])
  await until(() => state.observed.items[0]?.id === 'account-b')
  assert.equal(oldSignal.aborted, true)
  await act(async () => old.resolve(page([item({ id: 'private-account-a' })])))
  assert.deepEqual(state.observed.items.map((row) => row.id), ['account-b'])
  act(() => state.store.getState().clearAuth())
  assert.deepEqual(state.observed.items, [])
  assert.equal(state.observed.allowed, false)
})

test('Sidebar shows identity and Jira notifications above logout, mounts one panel only on click, and restores focus on dismissal', async (t) => {
  let calls = 0
  const app = setupSidebar(t, { getNotifications: async () => { calls++; return page([item({ title: '<script>text</script>', message: '<img src=x>', url: 'javascript:alert(1)' }), item({ id: 'read', is_read: true, group_size: 2 })]) } })
  await until(() => app.view.root.findAllByProps({ 'aria-label': 'Jira 알림' }).length === 1)
  const account = app.view.root.findByProps({ 'aria-label': '로그인 사용자' })
  assert.equal(account.findAllByType('p')[0].children.join(''), '동일 이름')
  assert.equal(account.findAllByType('p')[1].children.join(''), 'jira-user@example.test')
  assert.equal(account.findAllByType('p')[1].props.title, 'jira-user@example.test')
  assert.ok(!JSON.stringify(app.view.toJSON()).includes('account-a'))
  assert.deepEqual(account.parent.children.filter((child) => typeof child === 'object' && child.props['aria-label']).map((child) => child.props['aria-label']), ['로그인 사용자', 'Jira 알림', '로그아웃'])
  assert.equal(calls, 0)
  app.open()
  await until(() => app.view.root.findAllByProps({ 'data-notification-id': 'notification-a' }).length === 1)
  assert.equal(calls, 1)
  assert.equal(app.view.root.findAllByProps({ role: 'dialog' }).length, 1)
  assert.equal(app.panel.focused, 1)
  assert.equal(app.view.root.findAllByType('script').length, 0)
  assert.equal(app.view.root.findAllByType('img').length, 0)
  assert.equal(app.view.root.findByProps({ role: 'dialog' }).findAllByType('a').length, 1)
  assert.equal(app.view.root.findAllByType('span').filter((node) => node.children.includes('읽지 않음')).length, 1)
  assert.ok(JSON.stringify(app.view.toJSON()).includes('읽음 상태는 조회 시점 기준'))
  assert.ok(JSON.stringify(app.view.toJSON()).includes('알림을 열어도 Jira의 읽음 상태는 변경되지 않습니다.'))
  const buttons = app.view.root.findAllByProps({ 'aria-label': 'Jira 알림' })
  for (const button of buttons) assert.deepEqual(button.findAllByType('span').map((span) => span.children.join('')), ['Jira 알림'])
  act(() => app.listeners.get('keydown')({ key: 'Escape', preventDefault() {} }))
  assert.equal(app.view.root.findAllByProps({ role: 'dialog' }).length, 0)
  assert.equal(app.trigger.focused, 1)
  await until(() => app.client.getQueriesData({ queryKey: ['jira-notifications'] }).length === 0)
  app.open()
  await until(() => calls === 2)
  act(() => app.listeners.get('pointerdown')({ target: app.outside() }))
  assert.equal(app.view.root.findAllByProps({ role: 'dialog' }).length, 0)
  assert.equal(app.trigger.focused, 2)
})

test('Jira accounts without a disclosed email never fall back to an internal account ID', async (t) => {
  for (const email_address of [null, undefined, '', '   ']) {
    await t.test(`missing email ${JSON.stringify(email_address)}`, async (t) => {
      const app = setupSidebar(t, { me: async () => ({ ...jira, email_address }) })
      await until(() => app.view.root.findAllByProps({ 'aria-label': '로그인 사용자' }).length === 1)
      const account = app.view.root.findByProps({ 'aria-label': '로그인 사용자' })
      assert.equal(account.findAllByType('p')[1].children.join(''), '이메일 비공개')
      assert.ok(!JSON.stringify(app.view.toJSON()).includes('account-a'))
      app.update({ collapsed: true })
      assert.equal(app.view.root.findByProps({ 'aria-label': '로그인 사용자 동일 이름 · 이메일 비공개' }).props.title, '동일 이름 · 이메일 비공개')
      assert.ok(!JSON.stringify(app.view.toJSON()).includes('account-a'))
    })
  }
})

test('local login keeps its ID and does not show a Jira email or notification control', async (t) => {
  const app = setupSidebar(t, { me: async () => ({ ...jira, username: 'admin', auth_provider: 'local' }) })
  await until(() => app.view.root.findAllByProps({ 'aria-label': '로그인 사용자' }).length === 1)
  const account = app.view.root.findByProps({ 'aria-label': '로그인 사용자' })
  assert.equal(account.findAllByType('p')[1].children.join(''), 'ID: admin')
  assert.equal(app.view.root.findAllByProps({ 'aria-label': 'Jira 알림' }).length, 0)
  assert.ok(!JSON.stringify(app.view.toJSON()).includes('jira-user@example.test'))
  app.update({ collapsed: true })
  assert.equal(app.view.root.findByProps({ 'aria-label': '로그인 사용자 동일 이름 · ID: admin' }).props.title, '동일 이름 · ID: admin')
})

test('closing panel cancels pending feed; changing identity hides controls and the single panel immediately', async (t) => {
  const pending = deferred()
  let signal
  const app = setupSidebar(t, { getNotifications: (_request, value) => { signal = value; return pending.promise } })
  await until(() => app.view.root.findAllByProps({ 'aria-label': 'Jira 알림' }).length === 1)
  app.open()
  await until(() => !!signal)
  act(() => app.view.root.findByProps({ 'aria-label': 'Jira 알림 닫기' }).props.onClick())
  assert.equal(signal.aborted, true)
  await act(async () => pending.resolve(page()))
  assert.equal(app.view.root.findAllByProps({ role: 'dialog' }).length, 0)
  app.open()
  act(() => app.store.getState().clearAuth())
  assert.equal(app.view.root.findAllByProps({ role: 'dialog' }).length, 0)
  assert.equal(app.view.root.findAllByProps({ 'aria-label': 'Jira 알림' }).length, 0)
  assert.ok(!JSON.stringify(app.view.toJSON()).includes('jira-user@example.test'))
})

test('reconnect state offers Jira login and rejects late redirect after the session changes', async (t) => {
  const login = deferred()
  let starts = 0
  const app = setupSidebar(t, { getNotifications: async () => page([item()], null, 'reconnect_required'), startJira: () => { starts++; return login.promise } })
  await until(() => app.view.root.findAllByProps({ 'aria-label': 'Jira 알림' }).length === 1)
  app.open()
  await until(() => app.view.root.findAllByType('button').some((node) => node.children.includes('Jira 다시 로그인')))
  assert.equal(app.view.root.findAllByProps({ 'data-notification-id': 'notification-a' }).length, 0)
  act(() => app.view.root.findAllByType('button').find((node) => node.children.includes('Jira 다시 로그인')).props.onClick())
  await until(() => starts === 1)
  act(() => app.store.getState().setAuth('other-session'))
  await act(async () => login.resolve({ authorization_url: 'https://auth.example.test/authorize' }))
  assert.deepEqual(app.redirects, [])
})

test('collapsed sidebar provides identity tooltip and icon notification access, while closing mobile drawer cancels its panel', async (t) => {
  let signal
  const pending = deferred()
  const app = setupSidebar(t, { collapsed: true, mobileOpen: true, getNotifications: (_request, value) => { signal = value; return pending.promise } })
  await until(() => app.view.root.findAllByProps({ 'aria-label': 'Jira 알림' }).length === 1)
  assert.equal(app.view.root.findByProps({ 'aria-label': '로그인 사용자 동일 이름 · jira-user@example.test' }).props.title, '동일 이름 · jira-user@example.test')
  assert.equal(app.view.root.findByProps({ 'aria-label': 'Jira 알림' }).props.title, 'Jira 알림')
  app.open()
  await until(() => !!signal)
  assert.match(app.view.root.findByProps({ role: 'dialog' }).props.className, /xl:left-16/)
  app.update({ collapsed: false, mobileOpen: false })
  assert.equal(app.view.root.findAllByProps({ role: 'dialog' }).length, 0)
  assert.equal(signal.aborted, true)
  await act(async () => pending.resolve(page()))
})

test('mobile account button opens the single shared Sidebar with identity, notifications and logout and closes its active panel', async (t) => {
  let calls = 0
  const app = setupSidebar(t, { layout: true, getNotifications: async () => { calls++; return page() } })
  await until(() => app.view.root.findAllByProps({ 'aria-label': '계정 메뉴' }).length === 1)
  assert.equal(app.view.root.findAllByType('aside').length, 1)
  assert.equal(calls, 0)
  act(() => app.view.root.findByProps({ 'aria-label': '계정 메뉴' }).props.onClick({ currentTarget: app.trigger }))
  assert.equal(app.view.root.findByProps({ 'aria-label': '계정 메뉴' }).props['aria-expanded'], true)
  assert.equal(app.view.root.findAllByProps({ 'aria-label': '로그인 사용자' }).length, 1)
  assert.equal(app.view.root.findByProps({ 'aria-label': '로그인 사용자' }).findAllByType('p')[1].children.join(''), 'jira-user@example.test')
  assert.equal(app.view.root.findAllByProps({ 'aria-label': '로그아웃' }).length, 1)
  app.open()
  await until(() => app.view.root.findAllByProps({ 'data-notification-id': 'notification-a' }).length === 1)
  assert.equal(app.view.root.findAllByProps({ role: 'dialog' }).length, 1)
  assert.equal(calls, 1)
  act(() => app.view.root.findByProps({ 'aria-label': '계정 메뉴 바깥 영역 닫기' }).props.onClick())
  assert.equal(app.view.root.findByProps({ 'aria-label': '계정 메뉴' }).props['aria-expanded'], false)
  assert.equal(app.view.root.findAllByProps({ role: 'dialog' }).length, 0)
  await until(() => app.client.getQueriesData({ queryKey: ['jira-notifications'] }).length === 0)
})
