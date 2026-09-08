// frontend/tests/filePreviewModal.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')
const formats = ['txt', 'md', 'csv', 'xlsx', 'docx']

function deferred() {
  let resolve
  let reject
  const promise = new Promise((accept, decline) => { resolve = accept; reject = decline })
  return { promise, resolve, reject }
}

function bytes(value) {
  return new TextEncoder().encode(value).buffer
}

function binary(value) {
  return {
    read: async () => bytes(value),
    createObjectUrl: () => ({ url: 'blob:converted-preview', close() {} }),
  }
}

function eventTarget() {
  const listeners = new Map()
  return {
    addEventListener(type, listener) {
      if (!listeners.has(type)) listeners.set(type, new Set())
      listeners.get(type).add(listener)
    },
    removeEventListener(type, listener) { listeners.get(type)?.delete(listener) },
    dispatch(type, event) { for (const listener of listeners.get(type) ?? []) listener(event) },
    listenerCount: () => [...listeners.values()].reduce((total, entries) => total + entries.size, 0),
  }
}

function loadApplication({ readPreview, convertPreview, imports = {}, canvasContext = true } = {}) {
  const document = {
    ...eventTarget(),
    body: { style: { overflow: '' } },
    fullscreenElement: null,
    documentElement: { requestFullscreen: async () => {} },
    exitFullscreen: async () => {},
  }
  let timerId = 0
  const timers = new Map()
  const window = {
    ...eventTarget(),
    devicePixelRatio: 1,
    setTimeout(handler, delay) {
      const id = ++timerId
      timers.set(id, { handler, delay })
      return id
    },
    clearTimeout: (id) => timers.delete(id),
    timerCount: () => timers.size,
    fireTimers(elapsed) {
      for (const [id, timer] of [...timers]) {
        if (timer.delay <= elapsed && timers.delete(id)) timer.handler()
      }
    },
  }
  const storage = {
    preview: (name, folder) => `preview:${folder}/${name}`,
    download: (name, folder) => `download:${folder}/${name}`,
    readPreview: readPreview ?? (async () => binary('rendered preview content')),
    convertPreview: convertPreview ?? (async () => binary('%PDF-1.7')),
  }
  const dependencies = new Map(Object.entries({
    '@/presentation/context/ApplicationServicesContext': { useApplicationServices: () => ({ storage }) },
    'react-markdown': { default: ({ children }) => React.createElement('article', null, children) },
    'remark-gfm': { default: () => {} },
    'rehype-highlight': { default: () => {} },
    xlsx: {
      read: (buffer) => ({ SheetNames: ['Sheet 1'], Sheets: { 'Sheet 1': new TextDecoder().decode(buffer) } }),
      utils: { sheet_to_html: (value) => `<table><tbody><tr><td>${value}</td></tr></tbody></table>` },
    },
    mammoth: { convertToHtml: async ({ arrayBuffer }) => ({ value: `<p>${new TextDecoder().decode(arrayBuffer)}</p>` }) },
    ...imports,
  }))
  const modules = new Map()
  function loadSource(relative) {
    const filename = path.resolve(sourceRoot, /\.[jt]sx?$/.test(relative) ? relative : `${relative}.ts`)
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    const source = fs.readFileSync(filename, 'utf8').replaceAll('import.meta.url', JSON.stringify(pathToFileURL(filename).href))
    const compiled = ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
      fileName: filename,
    }).outputText
    const resolve = (dependency) => {
      if (dependencies.has(dependency)) {
        const result = dependencies.get(dependency)
        if (result instanceof Error) throw result
        return result
      }
      if (dependency.endsWith('.css')) return {}
      if (dependency.startsWith('@/')) return loadSource(dependency.slice(2))
      if (dependency.startsWith('.')) return loadSource(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)))
      return require(dependency)
    }
    new Function('require', 'module', 'exports', 'document', 'window', 'navigator', compiled)(
      resolve, module, module.exports, document, window, { platform: 'Win32' },
    )
    return module.exports
  }
  const FilePreviewModal = loadSource('presentation/components/storage/FilePreviewModal.tsx').default
  const canvas = { style: {}, getContext: () => canvasContext ? { scale() {} } : null }
  return {
    FilePreviewModal,
    document,
    window,
    storage,
    createNodeMock: (element) => element.type === 'canvas' ? canvas : { clientWidth: 1000 },
  }
}

async function mount(t, app, props = {}) {
  let renderer
  let currentProps = { name: 'document.txt', folder: 'reports', ...props }
  const close = () => renderer.unmount()
  await act(async () => {
    renderer = TestRenderer.create(React.createElement(app.FilePreviewModal, { ...currentProps, onClose: close }), {
      createNodeMock: app.createNodeMock,
    })
  })
  t.after(async () => { await act(async () => renderer.unmount()) })
  return {
    renderer,
    async update(nextProps) {
      currentProps = { ...currentProps, ...nextProps }
      await act(async () => renderer.update(React.createElement(app.FilePreviewModal, { ...currentProps, onClose: close })))
    },
    async close() {
      await act(async () => renderer.root.findAllByType('button').find((button) => button.props.onClick === close).props.onClick())
    },
  }
}

function visibleText(renderer) {
  function collect(node) {
    if (node === null || node === undefined) return ''
    if (typeof node === 'string') return node
    if (Array.isArray(node)) return node.map(collect).join(' ')
    return `${node.props?.dangerouslySetInnerHTML?.__html ?? ''} ${collect(node.children)}`
  }
  return collect(renderer.toJSON()).replace(/\s+/g, ' ').trim()
}

function assertLoading(renderer) {
  assert.equal(renderer.root.findAllByProps({ role: 'status', 'aria-label': '미리보기 불러오는 중' }).length, 1)
  assert.equal(renderer.root.findAllByProps({ role: 'alert' }).length, 0)
}

function assertReady(renderer, expected) {
  assert.equal(renderer.root.findAllByProps({ role: 'status' }).length, 0)
  assert.equal(renderer.root.findAllByProps({ role: 'alert' }).length, 0)
  assert.ok(visibleText(renderer).includes(expected), visibleText(renderer))
}

function assertError(renderer, detail) {
  assert.equal(renderer.root.findAllByProps({ role: 'status' }).length, 0)
  assert.equal(renderer.root.findAllByProps({ role: 'alert' }).length, 1)
  assert.ok(visibleText(renderer).includes('미리보기를 불러올 수 없습니다.'), visibleText(renderer))
  if (detail) assert.ok(visibleText(renderer).includes(detail), visibleText(renderer))
}

for (const extension of formats) {
  test(`${extension} preview renders the downloaded content and ends loading`, async (t) => {
    const request = deferred()
    const reads = []
    const app = loadApplication({ readPreview: (name, folder) => { reads.push([name, folder]); return request.promise } })
    const view = await mount(t, app, { name: `document.${extension}` })
    assertLoading(view.renderer)
    await act(async () => request.resolve(binary('downloaded preview content')))
    assertReady(view.renderer, 'downloaded preview content')
    assert.deepEqual(reads, [[`document.${extension}`, 'reports']])
  })

  for (const phase of ['request', 'binary read']) {
    test(`${extension} preview exposes ${phase} failures and ends loading`, async (t) => {
      const operation = deferred()
      const app = loadApplication({
        readPreview: phase === 'request' ? () => operation.promise : async () => ({ read: () => operation.promise }),
      })
      const view = await mount(t, app, { name: `document.${extension}` })
      assertLoading(view.renderer)
      await act(async () => operation.reject(new Error('preview read failed')))
      assertError(view.renderer)
    })
  }

  test(`${extension} file changes clear old content while the next file loads`, async (t) => {
    const next = deferred()
    const app = loadApplication({ readPreview: (name) => name.startsWith('first') ? Promise.resolve(binary('previous preview body')) : next.promise })
    const view = await mount(t, app, { name: `first.${extension}` })
    assertReady(view.renderer, 'previous preview body')
    await view.update({ name: `second.${extension}` })
    assertLoading(view.renderer)
    assert.ok(!visibleText(view.renderer).includes('previous preview body'))
    await act(async () => next.resolve(binary('next preview body')))
    assertReady(view.renderer, 'next preview body')
  })

  for (const completion of ['success', 'failure']) {
    test(`${extension} ignores an earlier file's late ${completion}`, async (t) => {
      const previous = deferred()
      const app = loadApplication({ readPreview: (name) => name.startsWith('first') ? previous.promise : Promise.resolve(binary('current preview body')) })
      const view = await mount(t, app, { name: `first.${extension}` })
      await view.update({ name: `second.${extension}` })
      assertReady(view.renderer, 'current preview body')
      await act(async () => completion === 'success' ? previous.resolve(binary('obsolete preview body')) : previous.reject(new Error('obsolete preview failure')))
      assertReady(view.renderer, 'current preview body')
      assert.ok(!visibleText(view.renderer).includes('obsolete preview'))
    })
  }

  test(`${extension} file changes recover after the previous file failed`, async (t) => {
    const next = deferred()
    const app = loadApplication({ readPreview: (name) => name.startsWith('first') ? Promise.reject(new Error('previous file failed')) : next.promise })
    const view = await mount(t, app, { name: `first.${extension}` })
    assertError(view.renderer)
    await view.update({ name: `second.${extension}` })
    assertLoading(view.renderer)
    await act(async () => next.resolve(binary('recovered preview body')))
    assertReady(view.renderer, 'recovered preview body')
  })

  for (const completion of ['success', 'failure']) {
    test(`${extension} can close while reading and ignore late ${completion}`, async (t) => {
      const reading = deferred()
      const app = loadApplication({ readPreview: async () => ({ read: () => reading.promise }) })
      const view = await mount(t, app, { name: `document.${extension}` })
      assertLoading(view.renderer)
      await view.close()
      assert.equal(app.document.body.style.overflow, '')
      assert.equal(app.document.listenerCount(), 0)
      assert.equal(app.window.listenerCount(), 0)
      await act(async () => completion === 'success' ? reading.resolve(bytes('closed preview content')) : reading.reject(new Error('closed preview failure')))
      assert.equal(view.renderer.toJSON(), null)
    })
  }
}

test('changing folders reloads a file with the same name', async (t) => {
  const next = deferred()
  const app = loadApplication({ readPreview: (_name, folder) => folder === 'reports' ? Promise.resolve(binary('first folder content')) : next.promise })
  const view = await mount(t, app)
  assertReady(view.renderer, 'first folder content')
  await view.update({ folder: 'archive' })
  assertLoading(view.renderer)
  assert.ok(!visibleText(view.renderer).includes('first folder content'))
  await act(async () => next.resolve(binary('second folder content')))
  assertReady(view.renderer, 'second folder content')
})

test('an XLSX workbook without sheets shows an error instead of loading forever', async (t) => {
  const app = loadApplication({ imports: { xlsx: { read: () => ({ SheetNames: [], Sheets: {} }), utils: { sheet_to_html: () => '' } } } })
  const view = await mount(t, app, { name: 'empty.xlsx' })
  assertError(view.renderer, '표시할 시트가 없습니다.')
})

for (const extension of ['xlsx', 'docx']) {
  test(`${extension} parser failures produce a visible error`, async (t) => {
    const fail = () => { throw new Error('document parser failed') }
    const imports = extension === 'xlsx' ? { xlsx: { read: fail } } : { mammoth: { convertToHtml: fail } }
    const view = await mount(t, loadApplication({ imports }), { name: `document.${extension}` })
    assertError(view.renderer)
  })

  test(`${extension} module loading failures produce a visible error`, async (t) => {
    const imports = { [extension === 'xlsx' ? 'xlsx' : 'mammoth']: new Error('preview module unavailable') }
    const view = await mount(t, loadApplication({ imports }), { name: `document.${extension}` })
    assertError(view.renderer)
  })
}

test('XLSX sheet selection renders the selected sheet and resets for a new workbook', async (t) => {
  const app = loadApplication({
    imports: {
      xlsx: {
        read: () => ({ SheetNames: ['First sheet', 'Second sheet'], Sheets: { 'First sheet': 'first sheet content', 'Second sheet': 'second sheet content' } }),
        utils: { sheet_to_html: (value) => `<p>${value}</p>` },
      },
    },
  })
  const view = await mount(t, app, { name: 'first.xlsx' })
  assertReady(view.renderer, 'first sheet content')
  await act(async () => view.renderer.root.findAllByType('button').find((button) => button.children.includes('Second sheet')).props.onClick())
  assertReady(view.renderer, 'second sheet content')
  await view.update({ name: 'second.xlsx' })
  assertReady(view.renderer, 'first sheet content')
})

for (const [extension, element] of [['png', 'img'], ['mp4', 'video']]) {
  test(`${extension} media failures show a visible error and recover when the file changes`, async (t) => {
    const view = await mount(t, loadApplication(), { name: `first.${extension}` })
    const media = view.renderer.root.findByType(element)
    await act(async () => media.props.onError())
    assertError(view.renderer)
    await view.update({ name: `second.${extension}` })
    assert.equal(view.renderer.root.findAllByProps({ role: 'alert' }).length, 0)
    assert.equal(view.renderer.root.findByType(element).props.src, `preview:reports/second.${extension}`)
  })

  test(`${extension} stalled media ends loading after its timeout`, async (t) => {
    const app = loadApplication()
    const view = await mount(t, app, { name: `document.${extension}` })
    assertLoading(view.renderer)
    await act(async () => app.window.fireTimers(29_999))
    assertLoading(view.renderer)
    await act(async () => app.window.fireTimers(30_000))
    assertError(view.renderer)
    assert.equal(app.window.timerCount(), 0)
  })

  test(`${extension} loaded media clears its timeout and stays visible`, async (t) => {
    const app = loadApplication()
    const view = await mount(t, app, { name: `document.${extension}` })
    assertLoading(view.renderer)
    await act(async () => view.renderer.root.findByType(element).props[element === 'img' ? 'onLoad' : 'onLoadedData']())
    assertReady(view.renderer, `document.${extension}`)
    assert.equal(view.renderer.root.findByType(element).props.style.visibility, 'visible')
    assert.equal(app.window.timerCount(), 0)
    await act(async () => app.window.fireTimers(30_000))
    assertReady(view.renderer, `document.${extension}`)
  })

  test(`${extension} media errors and closing the preview clear their timeouts`, async (t) => {
    const app = loadApplication()
    const view = await mount(t, app, { name: `first.${extension}` })
    assert.equal(app.window.timerCount(), 1)
    await act(async () => view.renderer.root.findByType(element).props.onError())
    assert.equal(app.window.timerCount(), 0)
    await view.update({ name: `second.${extension}` })
    assert.equal(app.window.timerCount(), 1)
    await view.close()
    assert.equal(app.window.timerCount(), 0)
    await act(async () => app.window.fireTimers(30_000))
    assert.equal(view.renderer.toJSON(), null)
  })
}

function pdfMock({ load, getPage, render, pages = 1 } = {}) {
  const calls = { loads: [], loadingDestroyed: 0, pdfDestroyed: 0, renders: 0, renderCancelled: 0 }
  const pdf = {
    numPages: pages,
    destroy: async () => { calls.pdfDestroyed++ },
    getPage: getPage ?? (async () => ({
      getViewport: ({ scale }) => ({ width: 600 * scale, height: 800 * scale }),
      render: () => {
        calls.renders++
        return { promise: render ?? Promise.resolve(), cancel: () => { calls.renderCancelled++ } }
      },
    })),
  }
  const library = {
    version: '4.4.168',
    GlobalWorkerOptions: {},
    getDocument: (options) => {
      calls.loads.push(options)
      return { promise: load ?? Promise.resolve(pdf), destroy: async () => { calls.loadingDestroyed++ } }
    },
  }
  return { calls, pdf, library }
}

test('PDF document load failures show an error and end loading', async (t) => {
  const loading = deferred()
  const mock = pdfMock({ load: loading.promise })
  const view = await mount(t, loadApplication({ imports: { 'pdfjs-dist': mock.library } }), { name: 'document.pdf' })
  assertLoading(view.renderer)
  await act(async () => loading.reject(new Error('PDF document unavailable')))
  assertError(view.renderer)
})

test('PDF module loading failures show an error and end loading', async (t) => {
  const view = await mount(t, loadApplication({ imports: { 'pdfjs-dist': new Error('PDF module unavailable') } }), { name: 'document.pdf' })
  assertError(view.renderer)
})

test('PDF page rendering failures show an error', async (t) => {
  const rendering = deferred()
  const mock = pdfMock({ render: rendering.promise })
  const view = await mount(t, loadApplication({ imports: { 'pdfjs-dist': mock.library } }), { name: 'document.pdf' })
  assert.equal(mock.calls.renders, 1)
  await act(async () => rendering.reject(new Error('PDF canvas rendering failed')))
  assertError(view.renderer)
})

test('PDF page loading failures show an error', async (t) => {
  const mock = pdfMock({ getPage: async () => { throw new Error('PDF page unavailable') } })
  const view = await mount(t, loadApplication({ imports: { 'pdfjs-dist': mock.library } }), { name: 'document.pdf' })
  assertError(view.renderer)
})

test('PDF loading timeout ends loading and ignores a document that finishes later', async (t) => {
  const loading = deferred()
  const mock = pdfMock({ load: loading.promise })
  const app = loadApplication({ imports: { 'pdfjs-dist': mock.library } })
  const view = await mount(t, app, { name: 'document.pdf' })
  assertLoading(view.renderer)
  await act(async () => app.window.fireTimers(29_999))
  assertLoading(view.renderer)
  await act(async () => app.window.fireTimers(30_000))
  assertError(view.renderer, '파일을 불러오는 시간이 초과되었습니다.')
  assert.equal(mock.calls.loadingDestroyed, 1)
  await act(async () => loading.resolve(mock.pdf))
  assertError(view.renderer)
  assert.equal(mock.calls.renders, 0)
  assert.equal(app.window.timerCount(), 0)
})

test('a PDF without pages shows an error', async (t) => {
  const mock = pdfMock({ pages: 0 })
  const view = await mount(t, loadApplication({ imports: { 'pdfjs-dist': mock.library } }), { name: 'empty.pdf' })
  assertError(view.renderer, '표시할 PDF 페이지가 없습니다.')
})

test('a PDF without a canvas rendering context shows an error', async (t) => {
  const mock = pdfMock()
  const view = await mount(t, loadApplication({ imports: { 'pdfjs-dist': mock.library }, canvasContext: false }), { name: 'document.pdf' })
  assertError(view.renderer, '이 브라우저에서 PDF를 표시할 수 없습니다.')
  assert.equal(mock.calls.renders, 0)
})

test('a successfully rendered PDF clears its load timer and supports page navigation', async (t) => {
  const mock = pdfMock({ pages: 2 })
  const app = loadApplication({ imports: { 'pdfjs-dist': mock.library } })
  const view = await mount(t, app, { name: 'document.pdf' })
  assertReady(view.renderer, '1 / 2')
  assert.equal(app.window.timerCount(), 0)
  assert.equal(mock.calls.renders, 1)
  await act(async () => view.renderer.root.findAllByType('button').find((button) => button.children.includes('다음 →')).props.onClick())
  assertReady(view.renderer, '2 / 2')
  assert.equal(mock.calls.renders, 2)
})

test('switching away from a multipage PDF restores keyboard file navigation', async (t) => {
  const mock = pdfMock({ pages: 2 })
  const app = loadApplication({ imports: { 'pdfjs-dist': mock.library } })
  const navigated = []
  const view = await mount(t, app, { name: 'document.pdf', fileList: ['document.pdf', 'image.png', 'notes.txt'], onNavigate: (name) => navigated.push(name) })
  assertReady(view.renderer, '1 / 2')
  await view.update({ name: 'image.png' })
  await act(async () => app.window.dispatch('keydown', { key: 'ArrowRight', preventDefault() {}, stopPropagation() {} }))
  assert.deepEqual(navigated, ['notes.txt'])
})

test('closing a PDF destroys its loading task and ignores a late document', async (t) => {
  const loading = deferred()
  const mock = pdfMock({ load: loading.promise })
  const view = await mount(t, loadApplication({ imports: { 'pdfjs-dist': mock.library } }), { name: 'document.pdf' })
  assertLoading(view.renderer)
  await view.close()
  assert.equal(mock.calls.loadingDestroyed, 1)
  await act(async () => loading.resolve(mock.pdf))
  assert.equal(view.renderer.toJSON(), null)
  assert.equal(mock.calls.renders, 0)
  assert.equal(mock.calls.loadingDestroyed, 1)
})

test('closing a PDF while a page loads ignores the late page', async (t) => {
  const page = deferred()
  const mock = pdfMock({ getPage: () => page.promise })
  const app = loadApplication({ imports: { 'pdfjs-dist': mock.library } })
  const view = await mount(t, app, { name: 'document.pdf' })
  await view.close()
  let rendered = 0
  await act(async () => page.resolve({
    getViewport: ({ scale }) => ({ width: 600 * scale, height: 800 * scale }),
    render: () => { rendered++; return { promise: Promise.resolve(), cancel() {} } },
  }))
  assert.equal(rendered, 0)
  assert.equal(view.renderer.toJSON(), null)
  assert.equal(app.window.timerCount(), 0)
})

test('closing a rendered PDF destroys the document and cancels its pending render', async (t) => {
  const rendering = deferred()
  const mock = pdfMock({ render: rendering.promise })
  const view = await mount(t, loadApplication({ imports: { 'pdfjs-dist': mock.library } }), { name: 'document.pdf' })
  assert.equal(mock.calls.renders, 1)
  await view.close()
  assert.equal(mock.calls.renderCancelled, 1)
  assert.ok(mock.calls.pdfDestroyed + mock.calls.loadingDestroyed >= 1)
  await act(async () => rendering.reject(Object.assign(new Error('cancelled'), { name: 'RenderingCancelledException' })))
  assert.equal(view.renderer.toJSON(), null)
})

test('PPTX conversion failures show the server detail and retain a download link', async (t) => {
  const conversion = deferred()
  const view = await mount(t, loadApplication({ convertPreview: () => conversion.promise }), { name: 'slides.pptx' })
  await act(async () => conversion.reject(new Error('서버에서 PDF 변환 시간이 초과되었습니다.')))
  assert.ok(visibleText(view.renderer).includes('서버에서 PDF 변환 시간이 초과되었습니다.'))
  assert.ok(view.renderer.root.findAllByType('a').some((link) => link.props.href === 'download:reports/slides.pptx'))
})

test('PPTX converted object URLs close when the preview closes', async (t) => {
  let closed = 0
  const mock = pdfMock()
  const view = await mount(t, loadApplication({
    convertPreview: async () => ({ createObjectUrl: () => ({ url: 'blob:converted-slides', close: () => { closed++ } }) }),
    imports: { 'pdfjs-dist': mock.library },
  }), { name: 'slides.pptx' })
  assert.equal(mock.calls.loads[0].url, 'blob:converted-slides')
  await view.close()
  assert.equal(closed, 1)
})
