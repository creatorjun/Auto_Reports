// frontend/tests/lazyFilePreview.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { createRequire } from 'node:module'
import test from 'node:test'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import ts from 'typescript'

const require = createRequire(import.meta.url)

function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

function loadPreview(importPreview) {
  const source = fs.readFileSync(new URL('../src/presentation/components/storage/LazyFilePreviewModal.tsx', import.meta.url), 'utf8')
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText
  const module = { exports: {} }
  const resolve = (name) => {
    if (name === './FilePreviewModal') return importPreview()
    if (name.endsWith('/IssueModalShell')) return { default: ({ onClose, children }) => React.createElement('section', null, React.createElement('button', { onClick: onClose }, '닫기'), children) }
    if (name.endsWith('/LoadingSpinner')) return { default: ({ text }) => React.createElement('p', null, text) }
    return require(name)
  }
  new Function('require', 'module', 'exports', compiled)(resolve, module, module.exports)
  return module.exports.default
}

const Preview = (props) => React.createElement('preview', props)

test('preview bundle loads only when opened and forwards current file navigation props', async () => {
  const request = deferred()
  let calls = 0
  const LazyPreview = loadPreview(() => { calls += 1; return request.promise })
  assert.equal(calls, 0)
  const onClose = () => {}
  const onNavigate = () => {}
  const props = { name: 'first.md', folder: 'reports', fileList: ['first.md', 'second.pdf'], onClose, onNavigate }
  let view
  await act(async () => { view = TestRenderer.create(React.createElement(LazyPreview, props)) })
  assert.equal(calls, 1)
  assert.match(JSON.stringify(view.toJSON()), /미리보기 불러오는 중/)
  await act(async () => { view.update(React.createElement(LazyPreview, { ...props, name: 'second.pdf' })) })
  await act(async () => { request.resolve({ default: Preview }) })
  assert.deepEqual(view.root.findByType('preview').props, { ...props, name: 'second.pdf' })
  act(() => view.unmount())
  await act(async () => { view = TestRenderer.create(React.createElement(LazyPreview, props)) })
  assert.equal(calls, 1)
  assert.equal(view.root.findByType('preview').props.name, 'first.md')
  act(() => view.unmount())
})

test('closing while the bundle loads prevents a late preview mount', async () => {
  const request = deferred()
  const LazyPreview = loadPreview(() => request.promise)
  let view, closed = 0, mounts = 0
  await act(async () => { view = TestRenderer.create(React.createElement(LazyPreview, { name: 'large.md', onClose: () => { closed += 1; view.unmount() } })) })
  act(() => view.root.findByType('button').props.onClick())
  await act(async () => { request.resolve({ default: () => { mounts += 1; return null } }) })
  assert.equal(closed, 1)
  assert.equal(mounts, 0)
  assert.equal(view.toJSON(), null)
})

test('failed bundle loading stays closable and retries on the next open', async () => {
  let calls = 0, closed = 0, view
  const LazyPreview = loadPreview(() => { calls += 1; return calls === 1 ? Promise.reject(new Error('offline')) : Promise.resolve({ default: Preview }) })
  const props = { name: 'report.csv', onClose: () => { closed += 1; view.unmount() } }
  await act(async () => { view = TestRenderer.create(React.createElement(LazyPreview, props)) })
  assert.match(view.root.findByProps({ role: 'alert' }).children.join(''), /다시 시도/)
  act(() => view.root.findByType('button').props.onClick())
  assert.equal(closed, 1)
  await act(async () => { view = TestRenderer.create(React.createElement(LazyPreview, props)) })
  assert.equal(calls, 2)
  assert.equal(view.root.findByType('preview').props.name, 'report.csv')
  act(() => view.unmount())
})
