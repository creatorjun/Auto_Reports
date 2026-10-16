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

function setup() {
  const store = create((set) => ({
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

for (const validCookie of [true, false]) {
  test(`direct /login ${validCookie ? 'restores the cookie session and redirects' : 'shows local and Jira login after cookie rejection'}`, async (t) => {
    const app = setup()
    const { default: LoginPage } = app.load('presentation/pages/LoginPage')
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
          React.createElement(MemoryRouter, { initialEntries: ['/login?jira=success'], future: { v7_startTransition: true, v7_relativeSplatPath: true } },
            React.createElement(Routes, null,
              React.createElement(Route, { path: '/login', element: React.createElement(LoginPage) }),
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
    } else {
      assert.match(rendered, /Jira 계정으로 로그인/)
      assert.ok(view.root.findAllByType('input').some((input) => input.props.autoComplete === 'current-password'))
      assert.doesNotMatch(rendered, /Authenticated home/)
    }
  })
}
