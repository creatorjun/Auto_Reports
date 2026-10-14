// frontend/tests/focusManagement.test.mjs
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
const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')
const modules = new Map()
const overrides = {
  'presentation/state/authStore': { useAuthStore: () => ({ loginRequired: false }) },
  'presentation/hooks/useAuth': { useMe: () => ({ data: null }), useLogout: () => ({ mutate: () => {} }) },
  'presentation/components/layout/ThemeToggle': { default: () => null },
}
function load(relative) {
  if (Object.hasOwn(overrides, relative)) return overrides[relative]
  const base = path.join(sourceRoot, relative)
  const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
  assert.ok(filename)
  if (modules.has(filename)) return modules.get(filename).exports
  const module = { exports: {} }
  modules.set(filename, module)
  const code = ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX }, fileName: filename }).outputText
  new Function('require', 'module', 'exports', code)((dependency) => {
    if (dependency.startsWith('@/')) return load(dependency.slice(2))
    if (dependency.startsWith('.')) return load(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)).replaceAll('\\', '/'))
    return require(dependency)
  }, module, module.exports)
  return module.exports
}

const Sidebar = load('presentation/components/layout/Sidebar').default
const Mobile = load('presentation/components/layout/MobileTabBar').default
const { FOCUS_MANAGEMENT_LINKS } = load('presentation/config/focusManagement')

test('desktop groups the report routes in order and both parent menus open on mouse hover', (t) => {
  let view
  act(() => { view = TestRenderer.create(React.createElement(MemoryRouter, { initialEntries: ['/sla-violations/history/3'] }, React.createElement(Sidebar, { collapsed: false, setCollapsed: () => {} }))) })
  t.after(() => act(() => view.unmount()))
  for (const name of ['집중 관리 항목', '연간 보고서']) {
    const trigger = () => view.root.findByProps({ 'aria-label': name })
    assert.equal(trigger().props['aria-expanded'], false)
    act(() => trigger().parent.props.onPointerEnter({ pointerType: 'touch' }))
    assert.equal(trigger().props['aria-expanded'], false)
    act(() => trigger().parent.props.onPointerEnter({ pointerType: 'mouse' }))
    assert.equal(trigger().props['aria-expanded'], true)
    const content = view.root.findByProps({ id: trigger().props['aria-controls'] })
    assert.equal(content.props.hidden, false)
    if (name === '집중 관리 항목') {
      assert.match(trigger().props.className, /nav-link-active/)
      assert.deepEqual(content.findAllByType('a').map((link) => [link.props.href, link.children.join('')]), FOCUS_MANAGEMENT_LINKS.map(({ to, label }) => [to, label]))
    }
    act(() => trigger().props.onClick())
    assert.equal(trigger().props['aria-expanded'], false)
  }
})

test('hover expands a collapsed sidebar and keyboard Escape closes its submenu', (t) => {
  function Collapsible() {
    const [collapsed, setCollapsed] = React.useState(true)
    return React.createElement(Sidebar, { collapsed, setCollapsed })
  }
  let view
  act(() => { view = TestRenderer.create(React.createElement(MemoryRouter, null, React.createElement(Collapsible))) })
  t.after(() => act(() => view.unmount()))
  const trigger = () => view.root.findByProps({ 'aria-label': '집중 관리 항목' })
  act(() => trigger().parent.props.onPointerEnter({ pointerType: 'mouse' }))
  assert.equal(trigger().props['aria-expanded'], true)
  assert.equal(view.root.findByType(Sidebar).props.collapsed, false)
  let focused = false
  act(() => trigger().parent.props.onKeyDown({ key: 'Escape', currentTarget: { querySelector: () => ({ focus: () => { focused = true } }) } }))
  assert.equal(trigger().props['aria-expanded'], false)
  assert.equal(focused, true)
})

test('mobile exposes one focus-management trigger and closes after a child route is selected', (t) => {
  let view
  act(() => { view = TestRenderer.create(React.createElement(MemoryRouter, null, React.createElement(Mobile))) })
  t.after(() => act(() => view.unmount()))
  const trigger = () => view.root.findAllByType('button').find((button) => button.props['aria-controls'])
  const panel = () => view.root.findByProps({ id: trigger().props['aria-controls'] })
  assert.equal(panel().props.hidden, true)
  act(() => trigger().props.onClick())
  assert.equal(panel().props.hidden, false)
  assert.deepEqual(panel().findAllByType('a').map((link) => link.props.href), FOCUS_MANAGEMENT_LINKS.map(({ to }) => to))
  const link = panel().findAllByType('a')[0]
  act(() => link.props.onClick({ button: 0, defaultPrevented: false, preventDefault() {}, metaKey: false, altKey: false, ctrlKey: false, shiftKey: false }))
  assert.equal(panel().props.hidden, true)
  assert.match(trigger().props.className, /text-brand-600/)
})
