// frontend/tests/solutionPackages.test.mjs
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import test from 'node:test'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import { sourceLoader } from './helpers/loadCveSource.mjs'

const { QueryClient, QueryClientProvider } = createRequire(import.meta.url)('@tanstack/react-query')
const packages = Array.from({ length: 101 }, (_, i) => ({
  id: `LIB-${i}`, name: `lib.sample:component-${String(i + 1).padStart(3, '0')}`,
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

function renderInventory(t, inventory, read = () => ({ packages: inventory })) {
  const calls = []
  const transport = {
    async get(url, { params, signal }) {
      assert.equal(url, '/solution-packages')
      assert.ok(signal)
      calls.push(params)
      const hasInventory = params.product === 'eyeCloudXoar' && params.version === '4.0_R2'
      return { data: hasInventory ? read() : { packages: [] } }
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
  return { view, calls, client }
}

const change = (element, value) => act(() => element.props.onChange({ target: { value } }))
const click = (element) => act(() => element.props.onClick())
const labeled = (view, label) => view.root.findByProps({ 'aria-label': label })
const listRows = (view) => labeled(view, '패키지 목록').findAllByType('li', { deep: false })
const rowLabel = (item) => `${item.name} ${item.version}`

test('solution coverage distinguishes the initial inventory from official matches and polls only while collecting', async (t) => {
  const rows = [packages[0], { ...packages[1], cve_ids: null }]
  const source = { id: 'fixture', label: '테스트 권고', url: 'https://example.test/advisories', note: null }
  const coverage = (status, refreshing, refreshed_at = null) => ({
    status, refreshing, coverage_note: null, sources: [{ ...source, status, refreshed_at }],
  })
  let data = { packages: rows, coverage: coverage('pending', true) }
  const { view, client, calls } = renderInventory(t, rows, () => data)
  const screen = () => JSON.stringify(view.toJSON())
  const row = (index) => labeled(view, rowLabel(rows[index]))
  const rowContains = (index, text) => row(index).findAll((node) => node.children.includes(text)).length > 0
  const retryRead = () => click(view.root.findAllByType('button').find((button) => button.children.includes('다시 조회')))
  const pollInterval = () => {
    const query = client.getQueryCache().find({ queryKey: ['solution-packages'], exact: false })
    return query.options.refetchInterval(query)
  }
  const success = '2099-01-01T23:00:00Z'
  await until(() => screen().includes(rows[0].name))
  assert.ok(screen().includes('매일 08:00 KST 공식 권고 자동 수집'))
  assert.ok(rowContains(0, '초기 인벤토리'))
  assert.equal(pollInterval(), 3000)

  const collected = [{ ...rows[0], cve_basis: 'advisory', cve_ids: ['CVE-2099-0001'] }, rows[1]]
  data = { packages: collected, coverage: coverage('partial', false, success) }
  retryRead()
  await until(() => rowContains(0, '공식 권고'))
  assert.ok(rowContains(0, '공식 권고'))
  assert.ok(rowContains(1, '초기 인벤토리'))
  assert.ok(labeled(view, `${rowLabel(rows[0])} CVE 1건`))

  data = { packages: [{ ...collected[0], cve_ids: [] }, rows[1]], coverage: coverage('ready', false, '2099-01-02T23:00:00Z') }
  retryRead()
  await until(() => rowContains(0, '0건'))
  assert.ok(rowContains(0, '공식 권고'))
  assert.equal(pollInterval(), false)
  assert.equal(view.root.findAllByProps({ 'aria-label': '공식 자료 수집 상태' }).length, 0)
  assert.ok(!screen().includes('패키지 버전과 CVE 대조 기준'))
  for (const params of calls) assert.deepEqual(params, { product: 'eyeCloudXoar', version: '4.0_R2' })
})

test('solution selection scopes the inventory, clears stale rows and queries AI without a version', async (t) => {
  const { view, calls } = renderInventory(t, packages)
  const screen = () => JSON.stringify(view.toJSON())
  const product = (name) => view.root.findAllByType('button').find((b) => b.children.includes(name))
  const select = () => view.root.findByProps({ 'aria-label': '제품 버전' })
  const versions = () => select().findAllByType('option').map((option) => option.props.value)

  await until(() => screen().includes(packages[0].name))
  assert.deepEqual(calls[0], { product: 'eyeCloudXoar', version: '4.0_R2' })
  assert.deepEqual(versions(), ['4.0_R1', '4.0_R2', '4.0_R3'])
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

test('package list pages contain 25, 50 or 100 results and reset when the size changes', async (t) => {
  const { view } = renderInventory(t, packages)
  await until(() => view.root.findAllByProps({ 'aria-label': '패키지 목록' }).length > 0)
  const size = () => labeled(view, '페이지당 표시 건수')
  const labels = () => listRows(view).map((row) => row.props['aria-label'])
  const expected = (start, end) => packages.slice(start, end).map(rowLabel)
  assert.deepEqual(size().findAllByType('option').map((option) => Number(option.props.value)), [25, 50, 100])
  assert.deepEqual(labels(), expected(0, 25))
  click(labeled(view, '다음 페이지'))
  assert.deepEqual(labels(), expected(25, 50))
  change(size(), '50')
  assert.deepEqual(labels(), expected(0, 50))
  click(labeled(view, '다음 페이지'))
  assert.deepEqual(labels(), expected(50, 100))
  change(size(), '100')
  assert.deepEqual(labels(), expected(0, 100))
  click(labeled(view, '다음 페이지'))
  assert.deepEqual(labels(), expected(100, 101))
  assert.equal(labeled(view, '다음 페이지').props.disabled, true)
  click(labeled(view, '이전 페이지'))
  assert.deepEqual(labels(), expected(0, 100))
})

test('status cards filter package versions together with category and search', async (t) => {
  const rows = [
    { ...packages[0], name: 'fixture-codec', version: '99.1', category: 'Java', cve_ids: ['CVE-2099-0001'] },
    { ...packages[1], name: 'fixture-codec', version: '99.2', category: '웹', cve_ids: ['CVE-2099-0002'] },
    { ...packages[2], name: 'fixture-driver', version: '99.1', category: 'Java', cve_ids: ['CVE-2099-0003'] },
    { ...packages[3], name: 'fixture-codec', version: '99.3', category: 'Java', cve_ids: [] },
    { ...packages[4], name: 'fixture-codec', version: '99.4', category: 'Java', cve_ids: null },
  ]
  const { view } = renderInventory(t, rows)
  await until(() => view.root.findAllByProps({ 'aria-label': '패키지 목록' }).length > 0)
  function statusCard(label) {
    const buttons = labeled(view, '패키지 CVE 대조 상태').findAllByType('button')
    const card = buttons.find((b) => b.props['aria-label'] === label || b.findAll((el) => el.children.includes(label)).length > 0)
    assert.ok(card, label)
    return card
  }
  function expectRows(...indices) {
    const visible = listRows(view).map((row) => row.props['aria-label']).sort()
    assert.deepEqual(visible, indices.map((i) => rowLabel(rows[i])).sort())
  }
  for (const [label, count] of [['전체', 5], ['CVE 매칭', 3], ['미매칭', 1], ['대조 제한', 1]]) {
    assert.equal(statusCard(label).findByType('strong').children.join(''), String(count))
    assert.equal(statusCard(label).props['aria-pressed'], label === '전체')
  }
  expectRows(0, 1, 2, 3, 4)
  click(statusCard('CVE 매칭'))
  assert.equal(statusCard('CVE 매칭').props['aria-pressed'], true)
  expectRows(0, 1, 2)
  change(labeled(view, '패키지 분류'), 'Java')
  expectRows(0, 2)
  change(view.root.findByProps({ type: 'search' }), 'CODEC')
  expectRows(0)
  click(statusCard('미매칭'))
  expectRows(3)
  click(statusCard('대조 제한'))
  expectRows(4)
  click(statusCard('전체'))
  expectRows(0, 3, 4)
  change(view.root.findByProps({ type: 'search' }), '99.3')
  expectRows(3)
  click(statusCard('CVE 매칭'))
  assert.equal(view.root.findAllByProps({ 'aria-label': '패키지 목록' }).length, 0)
  assert.ok(JSON.stringify(view.toJSON()).includes('검색 조건에 맞는 패키지가 없습니다.'))
  change(view.root.findByProps({ type: 'search' }), '')
  change(labeled(view, '패키지 분류'), '')
  expectRows(0, 1, 2)
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
  for (const [item, label] of [[packages[2], '0건'], [packages[3], '대조 제한']]) {
    const row = labeled(view, rowLabel(item))
    assert.equal(row.type, 'li')
    assert.ok(row.findAll((node) => node.children.includes(label)).length > 0)
  }
  assert.ok(!screen().includes(sharedIds[0]))

  toggle('99.2.0', 3)
  assert.equal(disclosure('99.2.0', 3).props['aria-expanded'], true)
  const links = labeled(view, `${name} 99.2.0 매칭된 CVE`).findAllByType('a')
  assert.deepEqual(links.map((link) => link.children.join('')), sharedIds)
  for (const [index, link] of links.entries()) {
    assert.equal(link.props.href, `https://nvd.nist.gov/vuln/detail/${sharedIds[index]}`)
    assert.equal(link.props.target, '_blank')
    assert.ok(link.props.rel.split(' ').includes('noreferrer'))
  }
  assert.ok(!screen().includes(onlyInFirst))
  toggle('99.2.0', 3)
  assert.ok(!screen().includes(sharedIds[0]))

  toggle('99.1.0', 4)
  assert.ok(screen().includes(onlyInFirst))
  act(() => view.root.findByProps({ 'aria-label': '제품 버전' }).props.onChange({ target: { value: '4.0_R3' } }))
  assert.ok(!screen().includes(onlyInFirst))
})
