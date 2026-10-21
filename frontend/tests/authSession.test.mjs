// frontend/tests/authSession.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import axios from 'axios'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const { create } = require('zustand')
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query')
const { MemoryRouter, Route, Routes } = require('react-router-dom')
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')

function deferred() {
  let resolve
  let reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

function setup({ store: providedStore } = {}) {
  const store = providedStore ?? create((set) => ({
    accessToken: null, username: 'cached-name', loginRequired: true, sessionReady: false,
    setAuth: (accessToken, username) => set({ accessToken, username, sessionReady: true }),
    setLoginRequired: (value) => set(value ? { loginRequired: value } : { loginRequired: value, sessionReady: true }),
    clearAuth: () => set({ accessToken: null, username: null, loginRequired: true, sessionReady: true }),
  }))
  const modules = new Map()
  function load(relative) {
    if (relative === 'presentation/state/authStore') return { useAuthStore: store }
    if (relative === 'presentation/components/common/BrandLogo') return { default: () => React.createElement('img', { alt: 'SecuLayer' }) }
    const base = path.join(root, relative)
    const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
    assert.ok(filename, `Missing module ${relative}`)
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    const source = fs.readFileSync(filename, 'utf8').replaceAll('import.meta.env.VITE_API_BASE_URL', 'undefined')
    const compiled = ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX }, fileName: filename,
    }).outputText
    new Function('require', 'module', 'exports', compiled)((dependency) => {
      if (dependency.startsWith('@/')) return load(dependency.slice(2))
      if (dependency.startsWith('.')) return load(path.relative(root, path.resolve(path.dirname(filename), dependency)).replaceAll('\\', '/'))
      return require(dependency)
    }, module, module.exports)
    return module.exports
  }
  const http = load('infrastructure/api/client')
  const { authApi } = load('infrastructure/api/authApi')
  let redirects = 0
  http.configureHttpClient({
    getAccessToken: () => store.getState().accessToken,
    getUsername: () => store.getState().username,
    setAuth: (token, username) => store.getState().setAuth(token, username),
    clearAuth: () => store.getState().clearAuth(),
    redirectToLogin: () => { redirects++ },
  })
  return { store, load, client: http.default, auth: authApi, get redirects() { return redirects } }
}

function response(config, data, status = 200) {
  return { config, data, status, statusText: String(status), headers: {} }
}

function fail(config, status) {
  throw new axios.AxiosError('Request failed', 'ERR_BAD_RESPONSE', config, null, response(config, { detail: 'Not authenticated' }, status))
}

function loadAuthStore(browser) {
  const filename = path.join(root, 'presentation/state/authStore.ts')
  const source = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }, fileName: filename,
  }).outputText
  const module = { exports: {} }
  new Function('require', 'module', 'exports', 'globalThis', source)(require, module, module.exports, browser)
  return module.exports.useAuthStore
}

async function settle() {
  await act(async () => { await new Promise((resolve) => setTimeout(resolve, 5)) })
}

async function until(predicate) {
  const deadline = Date.now() + 2000
  while (!predicate()) {
    assert.ok(Date.now() < deadline, 'Timed out waiting for authentication state')
    await settle()
  }
}

function mountJiraLogin(t, app) {
  const { default: Page } = app.load('presentation/pages/LoginPage')
  const { ApplicationServicesProvider } = app.load('presentation/context/ApplicationServicesContext')
  const queries = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  const navigations = []
  const previousWindow = globalThis.window
  globalThis.window = { location: { assign: (url) => navigations.push(url) } }
  let view
  act(() => {
    view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { auth: app.auth } },
      React.createElement(QueryClientProvider, { client: queries },
        React.createElement(MemoryRouter, { initialEntries: ['/login'], future: { v7_startTransition: true, v7_relativeSplatPath: true } },
          React.createElement(Page)))))
  })
  t.after(() => { act(() => view.unmount()); queries.clear(); globalThis.window = previousWindow })
  const button = (label) => view.root.findAllByType('button').find((item) => item.children.filter((child) => typeof child === 'string').join('') === label)
  return { view, queries, navigations, button }
}

test('a remembered Jira account does not automatically resume after the ordinary session is rejected', async (t) => {
  const app = setup()
  const requests = []
  app.client.defaults.adapter = async (config) => {
    requests.push({ url: config.url, method: config.method })
    if (config.url === '/auth/providers') return response(config, { jira: { enabled: true, remembered: true } })
    if (config.url === '/auth/refresh' || config.url === '/auth/me') fail(config, 401)
    throw new Error(`Unexpected remembered-login request ${config.url}`)
  }
  const surface = mountJiraLogin(t, app)
  await until(() => surface.button('이전 Jira 계정으로 로그인'))
  await settle()
  assert.equal(app.store.getState().sessionReady, true)
  assert.equal(app.store.getState().accessToken, null)
  assert.ok(surface.button('다른 Jira 계정으로 로그인'))
  assert.ok(surface.button('기억한 계정 해제'))
  assert.deepEqual(requests.map(({ url }) => url).sort(), ['/auth/me', '/auth/providers', '/auth/refresh'])
  assert.deepEqual(surface.navigations, [])
  assert.equal(app.redirects, 0)
})

test('clicking the remembered Jira account resumes with an explicit request and follows the relative return URL', async (t) => {
  const app = setup()
  app.store.getState().clearAuth()
  const pending = deferred()
  const starts = []
  app.client.defaults.adapter = async (config) => {
    if (config.url === '/auth/providers') return response(config, { jira: { enabled: true, remembered: true } })
    if (config.url === '/auth/jira/start') {
      starts.push({ method: config.method, data: JSON.parse(config.data), credentials: config.withCredentials })
      await pending.promise
      return response(config, { authorization_url: '/' })
    }
    throw new Error(`Unexpected remembered-login request ${config.url}`)
  }
  const surface = mountJiraLogin(t, app)
  await until(() => surface.button('이전 Jira 계정으로 로그인'))
  assert.equal(starts.length, 0)
  act(() => surface.button('이전 Jira 계정으로 로그인').props.onClick())
  await until(() => starts.length === 1 && surface.button('로그인 중...'))
  assert.ok(surface.view.root.findAllByType('button').every((button) => button.props.disabled))
  assert.deepEqual(surface.navigations, [])
  await act(async () => { pending.resolve() })
  await until(() => surface.navigations.length === 1)
  assert.deepEqual(starts, [{ method: 'post', data: { force_authorization: false }, credentials: true }])
  assert.deepEqual(surface.navigations, ['/'])
  assert.equal(app.store.getState().accessToken, null)
})

test('choosing a different Jira account forces authorization instead of resuming the remembered account', async (t) => {
  const app = setup()
  app.store.getState().clearAuth()
  const starts = []
  const authorizationUrl = 'https://auth.atlassian.com/authorize?state=new-account'
  app.client.defaults.adapter = async (config) => {
    if (config.url === '/auth/providers') return response(config, { jira: { enabled: true, remembered: true } })
    if (config.url === '/auth/jira/start') {
      starts.push({ method: config.method, data: JSON.parse(config.data), credentials: config.withCredentials })
      return response(config, { authorization_url: authorizationUrl })
    }
    throw new Error(`Unexpected account-switch request ${config.url}`)
  }
  const surface = mountJiraLogin(t, app)
  await until(() => surface.button('다른 Jira 계정으로 로그인'))
  act(() => surface.button('다른 Jira 계정으로 로그인').props.onClick())
  await until(() => surface.navigations.length === 1)
  assert.deepEqual(starts, [{ method: 'post', data: { force_authorization: true }, credentials: true }])
  assert.deepEqual(surface.navigations, [authorizationUrl])
  assert.equal(app.store.getState().accessToken, null)
})

test('forgetting a Jira account rechecks providers and resets the login choices without starting authorization', async (t) => {
  const app = setup()
  app.store.getState().clearAuth()
  const pending = deferred()
  const requests = []
  let remembered = true
  app.client.defaults.adapter = async (config) => {
    requests.push({ url: config.url, method: config.method, credentials: config.withCredentials })
    if (config.url === '/auth/providers') return response(config, { jira: { enabled: true, remembered } })
    if (config.url === '/auth/jira/forget') {
      await pending.promise
      remembered = false
      return response(config, {})
    }
    throw new Error(`Unexpected forget-account request ${config.url}`)
  }
  const surface = mountJiraLogin(t, app)
  await until(() => surface.button('기억한 계정 해제'))
  act(() => surface.button('기억한 계정 해제').props.onClick())
  await until(() => requests.some(({ url }) => url === '/auth/jira/forget') && surface.button('기억한 계정 해제').props.disabled)
  assert.ok(surface.view.root.findAllByType('button').every((button) => button.props.disabled))
  assert.equal(requests.filter(({ url }) => url === '/auth/providers').length, 1)
  await act(async () => { pending.resolve() })
  await until(() => surface.button('Jira 계정으로 로그인'))
  assert.equal(surface.button('기억한 계정 해제'), undefined)
  assert.equal(surface.button('다른 Jira 계정으로 로그인'), undefined)
  assert.equal(surface.button('Jira 계정으로 로그인').props.disabled, false)
  assert.equal(surface.queries.getQueryData(['auth-providers']).jira.remembered, false)
  assert.deepEqual(requests, [
    { url: '/auth/providers', method: 'get', credentials: true },
    { url: '/auth/jira/forget', method: 'post', credentials: true },
    { url: '/auth/providers', method: 'get', credentials: true },
  ])
  assert.deepEqual(surface.navigations, [])
  assert.equal(app.store.getState().accessToken, null)
})

for (const provider of ['local', 'jira']) {
  test(`${provider} identity stays in memory and refresh restores its name after legacy identity storage is removed`, async () => {
    const entries = new Map([
      ['auth-storage', JSON.stringify({ state: { username: 'Legacy Identity', accessToken: 'legacy-token' }, version: 0 })],
      ['auto-reports-theme', JSON.stringify({ state: { theme: 'dark' } })],
      ['auto-reports-table:sla', JSON.stringify({ widths: { summary: 400 } })],
    ])
    const storage = {
      getItem: (key) => entries.get(key) ?? null,
      setItem: (key, value) => entries.set(key, value),
      removeItem: (key) => entries.delete(key),
    }
    const store = loadAuthStore({ localStorage: storage })
    assert.equal(entries.has('auth-storage'), false)
    assert.equal(store.getState().username, null)
    assert.equal(store.getState().accessToken, null)
    const preferences = [...entries]
    const app = setup({ store })
    app.client.defaults.adapter = async (config) => response(config, {
      access_token: `${provider}-memory-token`, username: `${provider}-identity`, display_name: 'Verified Identity', auth_provider: provider,
    })
    await app.auth.refresh()
    assert.equal(store.getState().username, 'Verified Identity')
    assert.equal(store.getState().accessToken, `${provider}-memory-token`)
    assert.equal(store.getState().sessionReady, true)
    assert.deepEqual([...entries], preferences)
    assert.doesNotMatch(JSON.stringify([...entries]), /Identity|identity|token/)
    store.getState().clearAuth()
    assert.equal(store.getState().username, null)
    assert.equal(store.getState().accessToken, null)
    assert.deepEqual([...entries], preferences)
  })
}

test('unavailable browser storage does not prevent memory-only authentication', () => {
  for (const browser of [{}, Object.defineProperty({}, 'localStorage', { get() { throw new Error('Storage blocked') } })]) {
    const store = loadAuthStore(browser)
    store.getState().setAuth('memory-token', 'Memory User')
    assert.equal(store.getState().username, 'Memory User')
    assert.equal(store.getState().accessToken, 'memory-token')
    store.getState().clearAuth()
    assert.equal(store.getState().accessToken, null)
  }
})

test('startup, login page and expired requests share one refresh and trust server identity', async () => {
  const app = setup()
  const pending = deferred()
  let refreshes = 0
  app.client.defaults.adapter = async (config) => {
    if (config.url === '/auth/refresh') {
      refreshes++
      await pending.promise
      return response(config, { access_token: 'restored', username: 'jira:account-id', display_name: 'Jira User' })
    }
    if (config.headers.Authorization !== 'Bearer restored') fail(config, 401)
    return response(config, { ok: true })
  }
  const first = app.auth.refresh()
  const second = app.auth.refresh()
  const data = app.client.get('/reports/')
  await until(() => refreshes === 1)
  pending.resolve()
  await Promise.all([first, second, data])
  assert.equal(refreshes, 1)
  assert.equal(app.store.getState().accessToken, 'restored')
  assert.equal(app.store.getState().username, 'Jira User')
  assert.equal(app.redirects, 0)
})

test('logout prevents late refresh resurrection and clears the cookie after refresh completes', async () => {
  const app = setup()
  const pending = deferred()
  const calls = []
  app.client.defaults.adapter = async (config) => {
    calls.push(config.url)
    if (config.url === '/auth/refresh') {
      await pending.promise
      return response(config, { access_token: 'late-token' })
    }
    return response(config, {})
  }
  const restore = app.auth.refresh()
  const rejected = assert.rejects(restore, { status: 401 })
  await until(() => calls.length === 1)
  const logout = app.auth.logout()
  assert.equal(app.store.getState().accessToken, null)
  await settle()
  assert.deepEqual(calls, ['/auth/refresh'])
  pending.resolve()
  await Promise.all([rejected, logout])
  assert.deepEqual(calls, ['/auth/refresh', '/auth/logout'])
  assert.equal(app.store.getState().accessToken, null)
  assert.equal(app.redirects, 0)
})

test('protected owner reporting APIs refresh an expired root access token without starting a new login', async () => {
  const app = setup()
  app.store.getState().setAuth('expired-root-session', 'root')
  let refreshes = 0
  const operations = []
  app.client.defaults.adapter = async (config) => {
    if (config.url === '/auth/refresh') {
      refreshes++
      return response(config, { access_token: 'restored-root-session', username: 'root', display_name: 'root', auth_provider: 'local', is_superadmin: true })
    }
    if (config.headers.Authorization !== 'Bearer restored-root-session') fail(config, 401)
    operations.push(config.url)
    if (config.url === '/auth/jira/privacy/status') return response(config, { owner_authorized: true })
    if (config.url === '/auth/jira/privacy/start') return response(config, { authorization_url: 'https://auth.atlassian.com/authorize?test=owner' })
    throw new Error(`Unexpected owner request ${config.url}`)
  }
  const status = await app.auth.getJiraPrivacyStatus()
  const started = await app.auth.startJiraPrivacy()
  assert.equal(status.owner_authorized, true)
  assert.equal(started.authorization_url, 'https://auth.atlassian.com/authorize?test=owner')
  assert.equal(refreshes, 1)
  assert.deepEqual(operations, ['/auth/jira/privacy/status', '/auth/jira/privacy/start'])
  assert.equal(app.store.getState().accessToken, 'restored-root-session')
  assert.equal(app.store.getState().username, 'root')
  assert.equal(app.redirects, 0)
})

test('a new login waits for prior refresh and cannot inherit its token or display name', async () => {
  const app = setup()
  const pending = deferred()
  const calls = []
  app.client.defaults.adapter = async (config) => {
    calls.push(config.url)
    if (config.url === '/auth/refresh') {
      await pending.promise
      return response(config, { access_token: 'old-account', display_name: 'Previous User' })
    }
    return response(config, { access_token: 'new-account', username: 'admin' })
  }
  const restore = app.auth.refresh()
  const rejected = assert.rejects(restore, { status: 401 })
  await until(() => calls.length === 1)
  const login = app.auth.login({ username: 'admin', password: 'test-password' })
  await settle()
  assert.deepEqual(calls, ['/auth/refresh'])
  pending.resolve()
  const [, result] = await Promise.all([rejected, login])
  assert.deepEqual(calls, ['/auth/refresh', '/auth/login'])
  assert.equal(result.access_token, 'new-account')
  assert.equal(app.store.getState().accessToken, null)
  assert.notEqual(app.store.getState().username, 'Previous User')
})

test('failed requests from the previous login cannot refresh or clear a newer session', async () => {
  const app = setup()
  const pending = deferred()
  let oldStarted = false
  let refreshes = 0
  app.client.defaults.adapter = async (config) => {
    if (config.url === '/reports/') {
      oldStarted = true
      await pending.promise
      fail(config, 401)
    }
    if (config.url === '/auth/refresh') refreshes++
    return response(config, { access_token: 'new-session', username: 'admin' })
  }
  app.store.getState().setAuth('old-session', 'Old User')
  const oldRequest = app.client.get('/reports/')
  const rejected = assert.rejects(oldRequest, { status: 401 })
  await until(() => oldStarted)
  const result = await app.auth.login({ username: 'admin', password: 'test-password' })
  app.store.getState().setAuth(result.access_token, result.username)
  pending.resolve()
  await rejected
  assert.equal(refreshes, 0)
  assert.equal(app.redirects, 0)
  assert.equal(app.store.getState().accessToken, 'new-session')
})

for (const transition of ['logout', 'login']) {
  for (const operation of ['getLatest', 'trigger']) {
    test(`late successful ${operation} responses cannot cross a ${transition} session boundary`, async () => {
      const app = setup()
      const { reportApi } = app.load('infrastructure/api/reportApi')
      const pending = deferred()
      let started = false
      let refreshes = 0
      app.store.getState().setAuth('old-session', 'Old User')
      app.client.defaults.adapter = async (config) => {
        if (config.url === '/reports/latest' || config.url === '/trigger/') {
          started = true
          await pending.promise
          return response(config, operation === 'getLatest' ? { id: 42 } : { job_id: 'old-job' })
        }
        if (config.url === '/auth/refresh') refreshes++
        return response(config, { access_token: 'new-session', username: 'New User' })
      }
      const request = reportApi[operation]()
      const rejected = assert.rejects(request, { status: 401, detail: '로그인 상태가 변경되었습니다.' })
      await until(() => started)
      if (transition === 'logout') await app.auth.logout()
      else {
        const result = await app.auth.login({ username: 'New User', password: 'test-password' })
        app.store.getState().setAuth(result.access_token, result.username)
      }
      pending.resolve()
      await rejected
      assert.equal(app.store.getState().accessToken, transition === 'logout' ? null : 'new-session')
      assert.equal(refreshes, 0)
      assert.equal(app.redirects, 0)
      assert.deepEqual((await app.client.get('/current-session')).data, { access_token: 'new-session', username: 'New User' })
    })
  }
}

test('Jira start failures do not trigger refresh and a new login resets prior expiry redirection', async () => {
  const app = setup()
  let refreshes = 0
  app.client.defaults.adapter = async (config) => {
    if (config.url === '/auth/refresh') { refreshes++; fail(config, 401) }
    if (config.url === '/auth/jira/start') fail(config, 503)
    if (config.url === '/auth/login') return response(config, { access_token: 'new-session' })
    fail(config, 401)
  }
  await assert.rejects(app.client.get('/reports/'), { status: 401 })
  assert.equal(app.redirects, 1)
  await assert.rejects(app.auth.startJira(), { status: 503 })
  assert.equal(refreshes, 1)
  await app.auth.login({ username: 'admin', password: 'test-password' })
  await assert.rejects(app.client.get('/reports/'), { status: 401 })
  assert.equal(refreshes, 2)
  assert.equal(app.redirects, 2)
})

test('shared restore hook restores a direct login surface once and does not re-login after logout', async (t) => {
  const app = setup()
  const { useAuthSession } = app.load('presentation/hooks/useAuthSession')
  const { ApplicationServicesProvider } = app.load('presentation/context/ApplicationServicesContext')
  let refreshes = 0
  app.client.defaults.adapter = async (config) => {
    if (config.url === '/auth/refresh') {
      refreshes++
      return response(config, { access_token: 'restored', display_name: 'Verified User' })
    }
    return response(config, {})
  }
  const observations = []
  function LoginSurface() { observations.push(useAuthSession()); return null }
  let view
  act(() => {
    view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { auth: app.auth } },
      React.createElement(React.Fragment, null, React.createElement(LoginSurface), React.createElement(LoginSurface))))
  })
  t.after(() => act(() => view.unmount()))
  await until(() => app.store.getState().sessionReady)
  assert.equal(refreshes, 1)
  assert.equal(observations.at(-1).isRestoring, false)
  assert.equal(observations.at(-1).accessToken, 'restored')
  await act(async () => { await app.auth.logout() })
  await settle()
  assert.equal(refreshes, 1)
  assert.equal(observations.at(-1).accessToken, null)
  assert.equal(observations.at(-1).isRestoring, false)
})

test('disabled login restores guest mode without an access token', async (t) => {
  const app = setup()
  const { useAuthSession } = app.load('presentation/hooks/useAuthSession')
  const { ApplicationServicesProvider } = app.load('presentation/context/ApplicationServicesContext')
  app.client.defaults.adapter = async (config) => {
    if (config.url === '/auth/refresh') fail(config, 404)
    return response(config, { username: 'guest', login_required: false, is_superadmin: false })
  }
  let observed
  function Probe() { observed = useAuthSession(); return null }
  let view
  act(() => { view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { auth: app.auth } }, React.createElement(Probe))) })
  t.after(() => act(() => view.unmount()))
  await until(() => observed && !observed.isRestoring)
  assert.equal(observed.accessToken, null)
  assert.equal(observed.loginRequired, false)
})

test('new authentication waits until logout has cleared the previous cookie', async () => {
  const app = setup()
  const pending = deferred()
  const calls = []
  app.client.defaults.adapter = async (config) => {
    calls.push(config.url)
    if (config.url === '/auth/logout') await pending.promise
    return response(config, { access_token: 'new-session' })
  }
  const logout = app.auth.logout()
  await until(() => calls.length === 1)
  const login = app.auth.login({ username: 'admin', password: 'test-password' })
  await settle()
  assert.deepEqual(calls, ['/auth/logout'])
  pending.resolve()
  const [, result] = await Promise.all([logout, login])
  assert.deepEqual(calls, ['/auth/logout', '/auth/login'])
  assert.equal(result.access_token, 'new-session')
})

for (const { pathname, page } of [{ pathname: '/login', page: 'LoginPage' }, { pathname: '/admin', page: 'AdminLoginPage' }]) {
  for (const validCookie of [true, false]) {
  test(`direct ${pathname} ${validCookie ? 'restores the cookie session and redirects' : 'shows only its intended login method after cookie rejection'}`, async (t) => {
    const app = setup()
    const { default: Page } = app.load(`presentation/pages/${page}`)
    const { ApplicationServicesProvider } = app.load('presentation/context/ApplicationServicesContext')
    const queries = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
    let refreshes = 0
    app.client.defaults.adapter = async (config) => {
      if (config.url === '/auth/providers') return response(config, { jira: { enabled: true } })
      if (config.url === '/auth/refresh') {
        refreshes++
        if (!validCookie) fail(config, 401)
        return response(config, { access_token: 'restored', display_name: 'Jira User' })
      }
      fail(config, 401)
    }
    let view
    act(() => {
      view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { auth: app.auth } },
        React.createElement(QueryClientProvider, { client: queries },
          React.createElement(MemoryRouter, { initialEntries: [pathname], future: { v7_startTransition: true, v7_relativeSplatPath: true } },
            React.createElement(Routes, null,
              React.createElement(Route, { path: pathname, element: React.createElement(Page) }),
              React.createElement(Route, { path: '/', element: React.createElement('div', null, 'Authenticated home') }))))))
    })
    t.after(() => { act(() => view.unmount()); queries.clear() })
    await until(() => app.store.getState().sessionReady)
    await settle()
    const rendered = JSON.stringify(view.toJSON())
    assert.equal(refreshes, 1)
    if (validCookie) {
      assert.match(rendered, /Authenticated home/)
      assert.equal(app.store.getState().username, 'Jira User')
    } else if (pathname === '/login') {
      assert.match(rendered, /Jira 계정으로 로그인/)
      assert.equal(view.root.findAllByType('input').length, 0)
      assert.equal(view.root.findAllByType('form').length, 0)
      assert.deepEqual(view.root.findAllByType('a').map((link) => link.props.href).sort(), ['/privacy', '/terms'])
      assert.doesNotMatch(rendered, /관리자|\/admin|Authenticated home/)
    } else {
      assert.ok(view.root.findAllByType('input').some((input) => input.props.autoComplete === 'current-password'))
      assert.equal(view.root.findAllByType('form').length, 1)
      assert.doesNotMatch(rendered, /Jira 계정으로 로그인|Authenticated home/)
    }
  })
  }
}

for (const { page, title } of [{ page: 'PrivacyPage', title: '개인정보처리방침' }, { page: 'TermsPage', title: '이용약관' }]) {
  test(`${page} renders without authentication providers and exposes policy and support links`, (t) => {
    const app = setup()
    const { default: Page } = app.load(`presentation/pages/${page}`)
    let view
    act(() => {
      view = TestRenderer.create(React.createElement(MemoryRouter, { future: { v7_startTransition: true, v7_relativeSplatPath: true } }, React.createElement(Page)))
    })
    t.after(() => act(() => view.unmount()))
    assert.equal(view.root.findByType('h1').children.join(''), title)
    const links = view.root.findAllByType('a').map((link) => link.props.href)
    for (const expected of ['/login', '/privacy', '/terms', 'mailto:jh.han@seculayer.com']) assert.ok(links.includes(expected))
    assert.ok(!links.includes('/admin'))
    const text = JSON.stringify(view.toJSON())
    assert.match(text, /SecuLayer/)
    assert.match(text, /2026년 10월 16일/)
    assert.equal(app.store.getState().sessionReady, false)
    assert.equal(view.root.findAllByType('input').length, 0)
  })
}

for (const username of ['admin', 'superadmin']) {
  test(`/admin submits ${username} credentials through the existing local login API`, async (t) => {
    const app = setup()
    app.store.getState().clearAuth()
    const { default: AdminLoginPage } = app.load('presentation/pages/AdminLoginPage')
    const { ApplicationServicesProvider } = app.load('presentation/context/ApplicationServicesContext')
    const queries = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
    const requests = []
    app.client.defaults.adapter = async (config) => {
      requests.push({ url: config.url, data: JSON.parse(config.data) })
      return response(config, { access_token: `${username}-session`, username, display_name: username, auth_provider: 'local' })
    }
    let view
    act(() => {
      view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { auth: app.auth } },
        React.createElement(QueryClientProvider, { client: queries },
          React.createElement(MemoryRouter, { initialEntries: ['/admin'], future: { v7_startTransition: true, v7_relativeSplatPath: true } },
            React.createElement(Routes, null,
              React.createElement(Route, { path: '/admin', element: React.createElement(AdminLoginPage) }),
              React.createElement(Route, { path: '/', element: React.createElement('div', null, 'Authenticated home') }))))))
    })
    t.after(() => { act(() => view.unmount()); queries.clear() })
    act(() => {
      view.root.findByProps({ id: 'admin-username' }).props.onChange({ target: { value: username } })
      view.root.findByProps({ id: 'admin-password' }).props.onChange({ target: { value: 'test-password' } })
    })
    act(() => view.root.findByType('form').props.onSubmit({ preventDefault() {} }))
    await until(() => app.store.getState().accessToken === `${username}-session`)
    assert.deepEqual(requests, [{ url: '/auth/login', data: { username, password: 'test-password' } }])
    assert.match(JSON.stringify(view.toJSON()), /Authenticated home/)
  })
}

for (const identity of [null, { username: 'admin', auth_provider: 'local' }, { username: 'jira:site:employee', auth_provider: 'jira' }]) {
  test(`/admin/jira-privacy rejects ${identity?.auth_provider ?? 'unauthenticated'} access without requesting owner status`, async (t) => {
    const app = setup()
    if (identity) app.store.getState().setAuth('ordinary-session', identity.username)
    else app.store.getState().clearAuth()
    const { default: Page } = app.load('presentation/pages/AdminJiraPrivacyPage')
    const { ApplicationServicesProvider } = app.load('presentation/context/ApplicationServicesContext')
    const queries = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
    const requests = []
    app.client.defaults.adapter = async (config) => {
      requests.push(config.url)
      if (config.url === '/auth/me') return response(config, { ...identity, login_required: true, is_superadmin: false })
      throw new Error(`Unexpected owner request ${config.url}`)
    }
    let view
    act(() => {
      view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { auth: app.auth } },
        React.createElement(QueryClientProvider, { client: queries },
          React.createElement(MemoryRouter, { initialEntries: ['/admin/jira-privacy'], future: { v7_startTransition: true, v7_relativeSplatPath: true } },
            React.createElement(Routes, null,
              React.createElement(Route, { path: '/admin/jira-privacy', element: React.createElement(Page) }),
              React.createElement(Route, { path: '/admin', element: React.createElement('div', null, 'Administrator sign-in') }))))))
    })
    t.after(() => { act(() => view.unmount()); queries.clear() })
    await until(() => JSON.stringify(view.toJSON()).includes(identity ? '접근 권한이 없습니다' : 'Administrator sign-in'))
    assert.deepEqual(requests, identity ? ['/auth/me'] : [])
    assert.doesNotMatch(JSON.stringify(view.toJSON()), /등록 계정|개인정보 보고 연결|offline_access/)
    assert.equal(view.root.findAllByType('button').length, 0)
  })
}

test('root privacy setup loads protected status and starts owner authorization without replacing the root session', async (t) => {
  const app = setup()
  app.store.getState().setAuth('root-session', 'root')
  const { default: Page } = app.load('presentation/pages/AdminJiraPrivacyPage')
  const { ApplicationServicesProvider } = app.load('presentation/context/ApplicationServicesContext')
  const queries = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  const requests = []
  const navigations = []
  const previousWindow = globalThis.window
  globalThis.window = { location: { assign: (url) => navigations.push(url) } }
  app.client.defaults.adapter = async (config) => {
    requests.push({ method: config.method, url: config.url, authorization: config.headers.Authorization })
    if (config.url === '/auth/me') return response(config, { username: 'root', auth_provider: 'local', login_required: true, is_superadmin: true })
    if (config.url === '/auth/jira/privacy/status') return response(config, {
      owner_authorized: true, registered_accounts: 12, account_states: { active: 9, pending_updated: 2, pending_closed: 1 },
      next_attempt_at: '2026-10-17T00:00:00Z', last_success_at: '2026-10-16T00:00:00Z', last_error: 'private-internal-error',
      coverage: { known_accounts: 12, unmapped_personal_fields: 0 }, reporting_ready: true,
    })
    if (config.url === '/auth/jira/privacy/start') return response(config, { authorization_url: 'https://auth.atlassian.com/authorize?test=privacy' })
    throw new Error(`Unexpected authentication request ${config.url}`)
  }
  let view
  act(() => {
    view = TestRenderer.create(React.createElement(ApplicationServicesProvider, { services: { auth: app.auth } },
      React.createElement(QueryClientProvider, { client: queries },
        React.createElement(MemoryRouter, { initialEntries: ['/admin/jira-privacy?jira_privacy=success'], future: { v7_startTransition: true, v7_relativeSplatPath: true } }, React.createElement(Page)))))
  })
  t.after(() => { act(() => view.unmount()); queries.clear(); globalThis.window = previousWindow })
  await until(() => view.root.findAllByType('dd').some((item) => item.children.join('') === '12개'))
  const rendered = JSON.stringify(view.toJSON())
  assert.match(rendered, /연결됨/)
  assert.ok(view.root.findAllByType('dd').some((item) => item.children.join('') === '3개'))
  assert.match(rendered, /offline_access/)
  assert.match(rendered, /암호화해 보관/)
  assert.match(rendered, /개인정보 보고 연결이 완료/)
  assert.doesNotMatch(rendered, /private-internal-error/)
  const connect = view.root.findAllByType('button').find((button) => button.children.join('') === '개인정보 보고 연결')
  act(() => connect.props.onClick())
  await until(() => navigations.length === 1)
  assert.deepEqual(navigations, ['https://auth.atlassian.com/authorize?test=privacy'])
  assert.deepEqual(requests, [
    { method: 'get', url: '/auth/me', authorization: 'Bearer root-session' },
    { method: 'get', url: '/auth/jira/privacy/status', authorization: 'Bearer root-session' },
    { method: 'post', url: '/auth/jira/privacy/start', authorization: 'Bearer root-session' },
  ])
  assert.equal(app.store.getState().accessToken, 'root-session')
  assert.equal(app.store.getState().username, 'root')
})
