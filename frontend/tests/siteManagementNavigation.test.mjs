// frontend/tests/siteManagementNavigation.test.mjs
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
const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')
const superadmin = { username: 'configured-owner', login_required: true, is_superadmin: true, auth_provider: 'local' }
const ordinary = { username: 'admin', login_required: true, is_superadmin: false, auth_provider: 'local' }

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

function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

async function until(predicate) {
  const deadline = Date.now() + 2000
  while (!predicate()) {
    assert.ok(Date.now() < deadline, 'Timed out waiting for navigation permission')
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 10)) })
  }
}

function setup(t, { me = async () => superadmin, token = 'owner-session' } = {}) {
  const store = create((set) => ({
    accessToken: token, username: 'root', loginRequired: true,
    setAuth: (accessToken) => set({ accessToken }), clearAuth: () => set({ accessToken: null }),
  }))
  const load = sourceLoader({
    'presentation/state/authStore': { useAuthStore: store },
    'presentation/components/layout/ThemeToggle': { default: () => null },
  })
  const { ApplicationServicesProvider } = load('presentation/context/ApplicationServicesContext')
  const Sidebar = load('presentation/components/layout/Sidebar').default
  const Mobile = load('presentation/components/layout/MobileTabBar').default
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  const element = React.createElement(ApplicationServicesProvider, { services: { auth: { me, logout: async () => {} } } },
    React.createElement(QueryClientProvider, { client }, React.createElement(MemoryRouter, null,
      React.createElement('section', { 'data-navigation': 'desktop' }, React.createElement(Sidebar, { collapsed: false, setCollapsed() {} })),
      React.createElement('section', { 'data-navigation': 'collapsed' }, React.createElement(Sidebar, { collapsed: true, setCollapsed() {} })),
      React.createElement('section', { 'data-navigation': 'mobile' }, React.createElement(Mobile)),
    )))
  let view
  act(() => { view = TestRenderer.create(element) })
  t.after(() => { act(() => view.unmount()); client.clear() })
  return {
    store, client,
    links(surface) { return view.root.findByProps({ 'data-navigation': surface }).findAllByType('a') },
    get profile() { return client.getQueryState(['me', store.getState().accessToken]) },
  }
}

function assertVisibility(app, expected) {
  for (const surface of ['desktop', 'collapsed', 'mobile']) {
    const links = app.links(surface)
    assert.equal(links.some((link) => link.props.href === '/sites'), expected, surface)
    for (const href of ['/', '/issues', '/sla-status', '/sla-violations', '/redeployments', '/sla-dashboard', '/storage', '/security-news']) {
      assert.ok(links.some((link) => link.props.href === href), `${surface} preserves ${href}`)
    }
    if (expected) assert.equal(links.filter((link) => link.props.href === '/sites').length, 1, surface)
  }
}

test('site menu authority requires explicit server booleans and never trusts a username or provider', () => {
  const { canViewSiteManagement } = sourceLoader()('domain/Auth')
  for (const auth_provider of ['local', 'jira']) assert.equal(canViewSiteManagement({ ...superadmin, auth_provider }), true)
  for (const profile of [undefined, null, ordinary, { ...ordinary, username: 'root' }, { ...superadmin, is_superadmin: undefined }, { ...superadmin, is_superadmin: 'true' }, { ...superadmin, is_superadmin: 1 }, { ...superadmin, login_required: false }, { ...superadmin, login_required: 'true' }]) {
    assert.equal(canViewSiteManagement(profile), false)
  }
})

test('all navigation surfaces hide sites until verified administrator permission arrives', async (t) => {
  const pending = deferred()
  const app = setup(t, { me: () => pending.promise })
  assertVisibility(app, false)
  await act(async () => pending.resolve(superadmin))
  await until(() => app.profile?.status === 'success')
  assertVisibility(app, true)
  assert.equal(app.links('collapsed').find((link) => link.props.href === '/sites').props.title, '사이트 관리')
  assert.equal(app.links('mobile').find((link) => link.props.href === '/sites').props['aria-label'], '사이트')
})

test('ordinary local and Jira users and disabled authentication keep sites hidden on every surface', async (t) => {
  for (const profile of [ordinary, { ...ordinary, auth_provider: 'jira' }, { ...superadmin, login_required: false }, { ...ordinary, username: 'root', is_superadmin: undefined }]) {
    const app = setup(t, { me: async () => profile })
    await until(() => app.profile?.status === 'success')
    assertVisibility(app, false)
  }
})

test('failed profile lookup hides sites both initially and after cached administrator permission', async (t) => {
  const failed = setup(t, { me: async () => { throw new Error('Unavailable') } })
  await until(() => failed.profile?.status === 'error')
  assertVisibility(failed, false)
  let fail = false
  const app = setup(t, { me: async () => { if (fail) throw new Error('Expired'); return superadmin } })
  await until(() => app.profile?.status === 'success')
  assertVisibility(app, true)
  fail = true
  await act(async () => { await app.client.invalidateQueries({ queryKey: ['me'] }) })
  await until(() => app.profile?.status === 'error' && app.links('desktop').every((link) => link.props.href !== '/sites'))
  assert.equal(app.profile.data, superadmin)
  assertVisibility(app, false)
})

test('changing from administrator to ordinary session immediately removes sites and preserves other navigation', async (t) => {
  const pending = deferred()
  let requests = 0
  const app = setup(t, { me: async () => ++requests === 1 ? superadmin : pending.promise })
  await until(() => app.profile?.status === 'success')
  assertVisibility(app, true)
  act(() => app.store.getState().setAuth('ordinary-session'))
  assertVisibility(app, false)
  await act(async () => pending.resolve(ordinary))
  await until(() => app.profile?.status === 'success')
  assertVisibility(app, false)
  act(() => app.store.getState().clearAuth())
  assertVisibility(app, false)
})

test('logout hides sites even with a cached profile and late administrator responses cannot restore them', async (t) => {
  const app = setup(t)
  await until(() => app.profile?.status === 'success')
  assertVisibility(app, true)
  act(() => {
    app.client.setQueryData(['me', null], superadmin)
    app.store.getState().clearAuth()
  })
  assertVisibility(app, false)
  const pending = deferred()
  const late = setup(t, { me: () => pending.promise })
  act(() => late.store.getState().clearAuth())
  await act(async () => pending.resolve(superadmin))
  assertVisibility(late, false)
})
