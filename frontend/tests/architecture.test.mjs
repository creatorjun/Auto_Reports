// frontend/tests/architecture.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const source = path.join(root, 'src')

function files(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name)
    if (entry.isDirectory()) return files(target)
    return /\.(ts|tsx)$/.test(entry.name) ? [target] : []
  })
}

function projectCodeFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    if (entry.isDirectory() && ['node_modules', 'dist'].includes(entry.name)) return []
    const target = path.join(directory, entry.name)
    if (entry.isDirectory()) return projectCodeFiles(target)
    return /\.(css|js|mjs|ts|tsx)$/.test(entry.name) ? [target] : []
  })
}

function imports(content) {
  return [...content.matchAll(/from\s+['"](@\/[^'"]+)['"]/g)].map((match) => match[1])
}

test('dependency rule', () => {
  const forbidden = {
    domain: ['application', 'infrastructure', 'presentation', 'app'],
    application: ['infrastructure', 'presentation', 'app'],
    infrastructure: ['presentation', 'app'],
  }
  const violations = []
  for (const file of files(source)) {
    const relative = path.relative(source, file).replaceAll('\\', '/')
    const layer = relative.split('/')[0]
    if (!(layer in forbidden)) continue
    for (const dependency of imports(fs.readFileSync(file, 'utf8'))) {
      if (forbidden[layer].some((target) => dependency.startsWith(`@/${target}/`))) {
        violations.push(`${relative}:${dependency}`)
      }
    }
  }
  assert.deepEqual(violations, [])
})

test('presentation depends on application contracts instead of infrastructure', () => {
  const violations = files(path.join(source, 'presentation')).flatMap((file) =>
    imports(fs.readFileSync(file, 'utf8'))
      .filter((dependency) => dependency.startsWith('@/infrastructure'))
      .map((dependency) => `${path.relative(source, file)}:${dependency}`),
  )
  assert.deepEqual(violations, [])
})

test('source comments follow project rule', () => {
  const violations = []
  for (const file of projectCodeFiles(root)) {
    const relative = path.relative(root, file).replaceAll('\\', '/')
    const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/)
    const expected = file.endsWith('.css')
      ? `/* frontend/${relative} */`
      : `// frontend/${relative}`
    if (lines[0] !== expected) {
      violations.push(`${relative}:missing path header`)
    }
    lines.slice(1).forEach((line, index) => {
      const isComment = file.endsWith('.css')
        ? /^\s*\/\*/.test(line)
        : /^\s*(\/\/|\/\*)/.test(line)
      if (isComment) {
        violations.push(`${relative}:${index + 2}:extra comment`)
      }
    })
  }
  assert.deepEqual(violations, [])
})
