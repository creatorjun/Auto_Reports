// frontend/tests/solutionPackages.test.mjs
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import test from 'node:test'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import { sourceLoader } from './helpers/loadCveSource.mjs'

const { QueryClient, QueryClientProvider } = createRequire(import.meta.url)('@tanstack/react-query')
const packages = Array.from({ length: 26 }, (_, i) => ({
  id: `LIB-${i}`, name: `lib.sample:component-${String(i + 1).padStart(2, '0')}`,
  version: '1.0.0', category: 'Java 라이브러리와 JDBC 드라이버', evidence: 'JAR 내부 pom.properties',
  cve_ids: [],
}))

async function until(predicate) {
  const deadline = Date.now() + 3000
  while (!predicate()) {
    assert.ok(Date.now() < deadline, 'Timed out waiting for package inventory')
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 5)) })
  }
}

function renderInventory(t, inventory) {
  const calls = []
  const transport = {
    async get(url, { params, signal }) {
      assert.equal(url, '/solution-packages')
      assert.ok(signal)
      calls.push(params)
      const hasInventory = params.product === 'eyeCloudXoar' && params.version === '4.0_R2'
      return { data: { packages: hasInventory ? inventory : [] } }
    },
  }
  const load = sourceLoader({ 'infrastructure/api/client': { default: transport, __esModule: true } })
  const services = { solutionPackages: load('infrastructure/api/solutionPackagesApi').solutionPackagesApi }
  const { ApplicationServicesProvider } = load('presentation/context/ApplicationServicesContext')
  const Page = load('presentation/pages/SolutionPackagesPage').default
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  let view
  act(() => {
    view = TestRenderer.create(React.createElement(QueryClientProvider, { client },
      React.createElement(ApplicationServicesProvider, { services }, React.createElement(Page))))
  })
  t.after(() => { act(() => view.unmount()); client.clear() })
  return { view, calls }
}

test('solution selection scopes the inventory, clears stale rows and queries AI without a version', async (t) => {
  const { view, calls } = renderInventory(t, packages)
  const screen = () => JSON.stringify(view.toJSON())
  const product = (name) => view.root.findAllByType('button').find((b) => b.children.includes(name))
  const select = () => view.root.findByProps({ 'aria-label': '제품 버전' })
  const versions = () => select().findAllByType('option').map((option) => option.props.value)
  const change = (element, value) => act(() => element.props.onChange({ target: { value } }))
  const click = (element) => act(() => element.props.onClick())

  await until(() => screen().includes(packages[0].name))
  assert.deepEqual(calls[0], { product: 'eyeCloudXoar', version: '4.0_R2' })
  assert.deepEqual(versions(), ['4.0_R1', '4.0_R2', '4.0_R3'])
  assert.ok(!screen().includes(packages[25].name))
  click(view.root.findByProps({ 'aria-label': '다음 페이지' }))
  assert.ok(screen().includes(packages[25].name))
  change(view.root.findByProps({ type: 'search' }), 'COMPONENT-01')
  assert.ok(screen().includes(packages[0].name))
  assert.ok(!screen().includes(packages[25].name))

  for (const version of ['4.0_R1', '4.0_R3']) {
    change(select(), version)
    assert.ok(!screen().includes(packages[0].name))
    await until(() => screen().includes('등록'))
    assert.deepEqual(calls.at(-1), { product: 'eyeCloudXoar', version })
  }
  click(product('eyeCloudSIM'))
  assert.deepEqual(versions(), ['3.1.0', '3.1.03'])
  await until(() => screen().includes('등록'))
  change(select(), '3.1.03')
  await until(() => screen().includes('등록'))
  assert.deepEqual(calls.at(-1), { product: 'eyeCloudSIM', version: '3.1.03' })
  click(product('eyeCloudAI'))
  await until(() => screen().includes('등록'))
  assert.deepEqual(calls.at(-1), { product: 'eyeCloudAI' })
  assert.equal(view.root.findAllByProps({ 'aria-label': '제품 버전' }).length, 0)
  assert.ok(!screen().includes(packages[0].name))
})

test('CVE counts disclose the IDs for the exact package version and distinguish limited coverage from zero matches', async (t) => {
  const name = 'org.example.fixture:sample-codec'
  const sharedIds = ['CVE-2099-0001', 'CVE-2099-0002', 'CVE-2099-0003']
  const onlyInFirst = 'CVE-2099-0004'
  const { view } = renderInventory(t, [
    { ...packages[0], name, version: '99.1.0', cve_ids: [onlyInFirst, ...sharedIds] },
    { ...packages[1], name, version: '99.2.0', cve_ids: sharedIds },
    packages[2],
    { ...packages[3], cve_ids: null },
  ])
  const screen = () => JSON.stringify(view.toJSON())
  const disclosure = (version, count) => view.root.findByProps({ 'aria-label': `${name} ${version} CVE ${count}건` })
  const toggle = (version, count) => act(() => disclosure(version, count).props.onClick())
  await until(() => screen().includes(name))
  assert.equal(disclosure('99.1.0', 4).props['aria-expanded'], false)
  const packageRow = (name) => view.root.findAllByType('tr').find((row) =>
    row.findAllByType('span').some((span) => span.children.includes(name)))
  assert.equal(packageRow(packages[2].name).findAllByType('td').at(-1).children.join(''), '0건')
  assert.equal(packageRow(packages[3].name).findAllByType('td').at(-1).children.join(''), '대조 제한')
  assert.ok(!screen().includes(sharedIds[0]))

  toggle('99.2.0', 3)
  assert.equal(disclosure('99.2.0', 3).props['aria-expanded'], true)
  assert.ok(sharedIds.every((id) => screen().includes(id)))
  assert.ok(!screen().includes(onlyInFirst))
  toggle('99.2.0', 3)
  assert.ok(!screen().includes(sharedIds[0]))

  toggle('99.1.0', 4)
  assert.ok(screen().includes(onlyInFirst))
  act(() => view.root.findByProps({ 'aria-label': '제품 버전' }).props.onChange({ target: { value: '4.0_R3' } }))
  assert.ok(!screen().includes(onlyInFirst))
})
