// frontend/tests/storagePreview.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import axios from 'axios'
import ts from 'typescript'

const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')
const require = createRequire(import.meta.url)

function loadApplication() {
  const modules = new Map()
  function loadSource(relative) {
    const filename = path.join(sourceRoot, relative.endsWith('.ts') ? relative : `${relative}.ts`)
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    const source = fs.readFileSync(filename, 'utf8').replaceAll('import.meta.env.VITE_API_BASE_URL', 'undefined')
    const compiled = ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
      fileName: filename,
    }).outputText
    const resolve = (dependency) => {
      if (dependency.startsWith('@/')) return loadSource(dependency.slice(2))
      if (dependency.startsWith('.')) return loadSource(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)))
      return require(dependency)
    }
    new Function('require', 'module', 'exports', compiled)(resolve, module, module.exports)
    return module.exports
  }
  return {
    ...loadSource('infrastructure/api/client.ts'),
    ...loadSource('infrastructure/api/storageApi.ts'),
    ...loadSource('application/errors/RequestError.ts'),
  }
}

function response(config, data, status = 200) {
  return { config, data, status, statusText: String(status), headers: {} }
}

function rejectResponse(config, data, status = 500) {
  throw new axios.AxiosError('Request failed', 'ERR_BAD_RESPONSE', config, null, response(config, data, status))
}

test('converted previews allow a longer conversion while ordinary requests retain their timeout', async () => {
  const app = loadApplication()
  const calls = []
  const pdf = new Blob(['%PDF-1.7\npreview'], { type: 'application/pdf' })
  app.default.defaults.adapter = async (config) => {
    calls.push(config)
    return response(config, config.url === '/storage/items' ? [] : pdf)
  }
  const converted = await app.storageApi.convertPreview('월간 보고서.pptx', '고객 자료')
  assert.equal(new TextDecoder().decode(await converted.read()), '%PDF-1.7\npreview')
  const objectUrl = converted.createObjectUrl()
  assert.equal(await (await fetch(objectUrl.url)).text(), '%PDF-1.7\npreview')
  objectUrl.close()
  objectUrl.close()
  await assert.rejects(fetch(objectUrl.url))
  await app.storageApi.readPreview('existing.pdf')
  await app.storageApi.list()
  assert.equal(calls[0].url, '/storage/preview-converted')
  assert.deepEqual(calls[0].params, { name: '월간 보고서.pptx', folder: '고객 자료' })
  assert.equal(calls[0].responseType, 'blob')
  assert.ok(calls[0].timeout > 120_000)
  assert.ok(calls[0].timeout <= 180_000)
  assert.deepEqual(calls.slice(1).map(({ timeout }) => timeout), [30_000, 30_000])
})

for (const mediaType of ['application/json', 'application/problem+json']) {
  test(`converted preview preserves a ${mediaType} Blob error detail`, async () => {
    const app = loadApplication()
    app.default.defaults.adapter = async (config) => rejectResponse(
      config,
      new Blob([JSON.stringify({ detail: '서버에서 PDF 변환 시간이 초과되었습니다.' })], { type: mediaType }),
      504,
    )
    await assert.rejects(app.storageApi.convertPreview('slow.pptx'), (error) => {
      assert.ok(error instanceof app.RequestError)
      assert.equal(error.status, 504)
      assert.equal(error.detail, '서버에서 PDF 변환 시간이 초과되었습니다.')
      assert.equal(error.message, error.detail)
      return true
    })
  })
}

test('ordinary JSON errors retain their status and detail', async () => {
  const app = loadApplication()
  app.default.defaults.adapter = async (config) => rejectResponse(config, { detail: '파일을 찾을 수 없습니다.' }, 404)
  await assert.rejects(app.storageApi.list(), { name: 'RequestError', status: 404, message: '파일을 찾을 수 없습니다.' })
})

test('malformed JSON and non-JSON Blob errors retain a safe fallback and their HTTP status', async () => {
  for (const data of [
    new Blob(['invalid json'], { type: 'application/json' }),
    new Blob(['<html>Bad Gateway</html>'], { type: 'text/html' }),
  ]) {
    const app = loadApplication()
    app.default.defaults.adapter = async (config) => rejectResponse(config, data, 502)
    await assert.rejects(app.storageApi.convertPreview('broken.pptx'), { name: 'RequestError', status: 502, message: 'Request failed' })
  }
})

test('network timeouts remain RequestError objects without an HTTP status', async () => {
  const app = loadApplication()
  app.default.defaults.adapter = async (config) => {
    throw new axios.AxiosError('timeout', 'ECONNABORTED', config)
  }
  await assert.rejects(app.storageApi.convertPreview('slow.pptx'), (error) => {
    assert.ok(error instanceof app.RequestError)
    assert.equal(error.status, null)
    assert.equal(error.message, 'Request failed')
    return true
  })
})

test('concurrent expired preview requests share refresh and retry with the new Bearer token', async () => {
  const app = loadApplication()
  let token = 'expired-test-token'
  let refreshes = 0
  let redirects = 0
  const retries = []
  app.configureHttpClient({
    getAccessToken: () => token,
    getUsername: () => 'test-user',
    setAuth: (nextToken) => { token = nextToken },
    clearAuth: () => { token = null },
    redirectToLogin: () => { redirects++ },
  })
  app.default.defaults.adapter = async (config) => {
    if (config.url === '/auth/refresh') {
      refreshes++
      return response(config, { access_token: 'refreshed-test-token' })
    }
    if (config.headers.Authorization !== 'Bearer refreshed-test-token') {
      return rejectResponse(config, new Blob(['{"detail":"인증 만료"}'], { type: 'application/json' }), 401)
    }
    retries.push(config)
    return response(config, new Blob(['%PDF-1.7'], { type: 'application/pdf' }))
  }
  const results = await Promise.all([
    app.storageApi.convertPreview('first.pptx'),
    app.storageApi.convertPreview('second.pptx'),
  ])
  assert.equal(refreshes, 1)
  assert.equal(redirects, 0)
  assert.equal(results.length, 2)
  assert.equal(retries.length, 2)
  assert.ok(retries.every(({ timeout, responseType }) => timeout > 120_000 && responseType === 'blob'))
})

test('refresh failure clears authentication once and rejects with the server detail', async () => {
  const app = loadApplication()
  let clears = 0
  let redirects = 0
  let refreshes = 0
  app.configureHttpClient({
    getAccessToken: () => 'expired-test-token',
    getUsername: () => 'test-user',
    setAuth: () => {},
    clearAuth: () => { clears++ },
    redirectToLogin: () => { redirects++ },
  })
  app.default.defaults.adapter = async (config) => {
    if (config.url === '/auth/refresh') {
      refreshes++
      return rejectResponse(config, { detail: '다시 로그인해 주세요.' }, 401)
    }
    return rejectResponse(config, new Blob(['{"detail":"인증 만료"}'], { type: 'application/json' }), 401)
  }
  await assert.rejects(app.storageApi.convertPreview('first.pptx'), { name: 'RequestError', status: 401, message: '다시 로그인해 주세요.' })
  await assert.rejects(app.storageApi.convertPreview('second.pptx'), { name: 'RequestError', status: 401, message: '인증 만료' })
  assert.deepEqual([refreshes, clears, redirects], [1, 1, 1])
})

test('an existing RequestError preserves its identity', async () => {
  const app = loadApplication()
  const existing = new app.RequestError(503, '잠시 후 다시 시도해 주세요.')
  app.default.defaults.adapter = async () => { throw existing }
  await assert.rejects(app.storageApi.convertPreview('retry.pptx'), (error) => error === existing)
})
