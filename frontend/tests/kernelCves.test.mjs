// frontend/tests/kernelCves.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import { createRequire } from 'node:module'
import { sourceLoader } from './helpers/loadCveSource.mjs'

const { QueryClient, QueryClientProvider } = createRequire(import.meta.url)('@tanstack/react-query')

const targets = [
  { id: 'ol8', label: 'Oracle Linux 8', packages: ['kernel', 'kernel-uek'], architectures: ['x86_64', 'aarch64'], available: true, coverage: 'Oracle 보안 권고' },
  { id: 'centos7', label: 'CentOS 7.9', packages: ['kernel'], architectures: ['x86_64'], available: true, coverage: '지원 종료' },
  { id: 'rocky7', label: 'Rocky Linux 7', packages: [], architectures: [], available: false, coverage: '출시되지 않았습니다.' },
  ...[8, 9].map((major) => ({ id: `rocky${major}`, label: `Rocky Linux ${major}`, packages: ['kernel'], architectures: ['x86_64'], available: true, coverage: 'Rocky Linux 권고' })),
]
const initial = { target: 'ol8', package: 'kernel', architecture: 'x86_64', version: '' }
const buildA = '4.18.0-477.el8'
const buildB = '4.18.0-513.el8'
const custom = '5.15.0-111.el8uek.x86_64'
const coverage = { status: 'ready', refreshing: false, coverage_note: null, sources: [{ id: 'vendor', label: '배포판 공식 자료', url: 'https://example.test/oval', status: 'ready', refreshed_at: '2026-11-01T18:00:00Z', note: null }] }
const fix = { advisory_id: 'ELSA-1', advisory_url: 'https://example.test/ELSA-1', issued_at: '2026-11-01', fixed_version: buildB, package: 'kernel', architecture: 'x86_64', title: '공식 커널 보안 업데이트' }
const finding = { cve_id: 'CVE-2026-12345', severity: 'high', summary: null, fixes: [fix] }
const result = { ...coverage, total: 31, page: 1, page_size: 25, severity_counts: { critical: 0, high: 31, medium: 0, low: 0, unknown: 0 }, items: [finding] }
const labels = (view) => JSON.stringify(view.toJSON())
const change = (node, value) => act(() => node.props.onChange({ target: { value } }))
const click = (node) => act(() => node.props.onClick())
const submit = (form) => act(() => form.props.onSubmit({ preventDefault() {} }))
const selectByValue = (view, value) => view.root.findAllByType('select').find((node) => node.findAllByType('option').some((option) => option.props.value === value))

async function until(predicate) {
  const deadline = Date.now() + 3000
  while (!predicate()) {
    assert(Date.now() < deadline, 'Timed out waiting for result')
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 8)) })
  }
}

async function page(t, response = () => result, versions = () => [buildB, buildA], upstream = () => { throw Error('Unexpected upstream lookup') }) {
  const calls = []
  const gateway = { async get(url, config) {
    assert.ok(config.signal)
    calls.push([url, config.params])
    if (url === '/kernel-cves/targets') return { data: { targets } }
    if (url === '/kernel-cves/releases') return { data: { ...coverage, versions: versions(config.params) } }
    if (url === '/kernel-cves/upstream') return { data: upstream(config.params) }
    assert.equal(url, '/kernel-cves')
    return { data: await response(config.params) }
  } }
  const load = sourceLoader({ 'infrastructure/api/client': { default: gateway, __esModule: true } })
  const { ApplicationServicesProvider } = load('presentation/context/ApplicationServicesContext')
  const { kernelCveApi } = load('infrastructure/api/kernelCveApi')
  const Page = load('presentation/pages/KernelCvePage').default
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  let view
  act(() => {
    view = TestRenderer.create(React.createElement(QueryClientProvider, { client },
      React.createElement(ApplicationServicesProvider, { services: { kernelCves: kernelCveApi } }, React.createElement(Page))))
  })
  t.after(() => { act(() => view.unmount()); client.clear() })
  await until(() => selectByValue(view, buildA))
  return { view, calls, client, lastRequest: () => calls.filter(([url]) => url === '/kernel-cves').at(-1)?.[1] }
}

test('changing an OS, package or architecture never carries over a version from another build', () => {
  const { resolveKernelSelection } = sourceLoader()('application/services/kernelSelection')
  for (const invalid of [null, false, 'damaged', { target: 'removed', version: custom }, { target: 'rocky7', version: buildA }]) {
    assert.deepEqual(resolveKernelSelection(targets, invalid), initial)
  }
  assert.deepEqual(resolveKernelSelection(targets, { ...initial, architecture: 'removed', version: buildA }), initial)
  assert.deepEqual(resolveKernelSelection(targets, { ...initial, package: 'removed', version: buildA }), initial)
  assert.deepEqual(resolveKernelSelection(targets, { ...initial, version: '  ' + buildA + '  ' }), { ...initial, version: buildA })
  assert.equal(resolveKernelSelection([], initial), null)
})

test('real gateway and page request server filters and pages for the selected build and display advisory evidence', async (t) => {
  const { view, lastRequest } = await page(t, (request) => request.search ? { ...result, total: 1 } : result)
  assert.equal(lastRequest(), undefined)
  assert.equal(selectByValue(view, 'rocky7'), undefined)
  assert.doesNotMatch(labels(view), /Rocky Linux 7/)
  assert.ok(selectByValue(view, 'rocky8') && selectByValue(view, 'rocky9'))
  change(selectByValue(view, buildA), buildA)
  await until(() => labels(view).includes('ELSA-1'))
  assert.deepEqual(lastRequest(), { ...initial, version: buildA, severity: 'all', search: '', page: 1, page_size: 25 })
  assert.match(labels(view), /공식 커널 보안 업데이트/)
  assert.match(labels(view), /권고 제목/)
  assert.ok(view.root.findByProps({ href: fix.advisory_url }))
  click(view.root.findByProps({ 'aria-label': '다음 페이지' }))
  await until(() => lastRequest().page === 2 && labels(view).includes('ELSA-1'))
  click(view.root.findByProps({ 'aria-label': '검색 조건별 위험도 필터' }).findAllByType('button')[2])
  await until(() => lastRequest().severity === 'high')
  assert.equal(lastRequest().page, 1)
  change(view.root.findByProps({ 'aria-label': 'CVE 번호 검색' }), 'CVE-2026')
  submit(view.root.findByType('form'))
  await until(() => lastRequest().search === 'CVE-2026')
  change(selectByValue(view, 'kernel-uek'), 'kernel-uek')
  assert.doesNotMatch(labels(view), /ELSA-1/)
  change(selectByValue(view, 'custom'), 'custom')
  change(view.root.findByProps({ 'aria-label': '커널 버전 직접 입력' }), custom)
  submit(view.root.findByType('form'))
  await until(() => lastRequest().version === custom)
  assert.deepEqual(lastRequest(), { ...initial, version: custom, package: 'kernel-uek', severity: 'all', search: '', page: 1, page_size: 25 })
  change(selectByValue(view, 'centos7'), 'centos7')
  assert.match(labels(view), /지원 종료/)
  assert.doesNotMatch(labels(view), /ELSA-1|5\.15\.0-111/)
})

test('missing source data never looks like a successful zero-CVE result', async (t) => {
  const { view } = await page(t, () => ({ ...result, total: null, items: [], status: 'error', severity_counts: { critical: 0, high: 0, medium: 0, low: 0, unknown: 0 } }))
  change(selectByValue(view, buildA), buildA)
  await until(() => labels(view).includes('수집 실패'))
  assert.match(labels(view), /결과 미확인/)
  assert.doesNotMatch(labels(view), /조건에 해당하는 CVE가 없습니다|0건/)
  assert.equal(view.root.findByProps({ 'aria-label': '검색 조건별 위험도 필터' }).findAllByType('strong').filter((el) => el.children.join('') === '—').length, 6)
})

test('confirmed build collapses into an editable mobile summary while desktop selectors and first-time setup remain open', async (t) => {
  const { view } = await page(t)
  const toggle = () => view.root.findAllByType('button').find((b) => b.children.includes('환경 변경') || b.children.includes('설정 닫기'))
  assert.equal(toggle(), undefined)
  change(selectByValue(view, buildA), buildA)
  await until(() => labels(view).includes('ELSA-1'))
  const editor = () => view.root.findByProps({ id: toggle().props['aria-controls'] })
  assert.equal(view.root.findByProps({ id: 'kernel-findings-title' }).findByType('span').children.join(''), '31건')
  assert.equal(toggle().props['aria-expanded'], false)
  assert.match(editor().props.className, /hidden sm:block/)
  assert.ok(toggle().parent.parent.findAllByType('p').some((el) => el.children.includes(buildA)))
  click(toggle())
  assert.equal(toggle().props['aria-expanded'], true)
  assert.equal(editor().props.className, undefined)
  assert.match(labels(view), /ELSA-1/)
  change(selectByValue(view, buildB), buildB)
  assert.equal(toggle().props['aria-expanded'], false)
  click(toggle())
  change(selectByValue(view, 'kernel-uek'), 'kernel-uek')
  assert.equal(toggle(), undefined)
  assert.doesNotMatch(labels(view), /ELSA-1/)
})

test('stale or partial data retains its warning alongside matching CVEs and unsafe URLs never render as links', async (t) => {
  const { view } = await page(t, () => ({...result, status: 'partial', coverage_note: '입력한 빌드가 공급자 목록에 없습니다.', items: [{ ...finding, fixes: [{ ...fix, advisory_url: 'javascript:alert(1)' }] }] }))
  change(selectByValue(view, buildA), buildA)
  await until(() => labels(view).includes('입력한 빌드가'))
  assert.match(labels(view), /일부 자료만 수집/)
  assert.match(labels(view), /CVE-2026-12345/)
  assert.doesNotMatch(labels(view), /javascript:alert/)
})

test('unlinked upstream records load separately on demand and never enter affected-CVE counts', async (t) => {
  const upstream = (q) => ({
    status: 'partial', refreshing: false, as_of: null, total: 21, page: q.page, page_size: 20,
    items: [{ cve_id: 'CVE-2026-88888', title: '업스트림 커널 항목', url: 'https://example.test/osv/88888', published_at: null }],
  })
  const { view, calls } = await page(t, () => result, () => [buildB, buildA], upstream)
  assert.ok(!calls.some(([url]) => url.endsWith('/upstream')))
  change(selectByValue(view, buildA), buildA)
  await until(() => labels(view).includes(fix.advisory_id))
  const upstreamButton = view.root.findByProps({ 'aria-controls': 'upstream-kernel-cves' })
  click(upstreamButton)
  await until(() => labels(view).includes('업스트림 커널 항목'))
  const lastUpstream = () => calls.filter(([url]) => url.endsWith('/upstream')).at(-1)?.[1]
  assert.deepEqual(lastUpstream(), { target: 'ol8', page: 1, search: '', page_size: 20 })
  assert.match(labels(view), /영향 여부는 미확인/)
  assert.doesNotMatch(JSON.stringify(view.root.findByProps({ id: 'kernel-cve-list' }).findAllByType('li').map((li) => li.findAllByType('a').map((a) => a.props.href))), /88888/)
  click(view.root.findByProps({ 'aria-label': '미연결 CVE 다음 페이지' }))
  await until(() => lastUpstream().page === 2)
  change(view.root.findByProps({ 'aria-label': '미연결 CVE 검색' }), '88888')
  submit(view.root.findByProps({ id: 'upstream-kernel-cves' }).findByType('form'))
  await until(() => lastUpstream().search === '88888')
  assert.equal(lastUpstream().page, 1)
  assert.equal(calls.filter(([url]) => url === '/kernel-cves').length, 1)
})

test('background collection keeps previous rows, including a known zero, and replaces them only with usable data for the same build', async (t) => {
  let respond = () => result
  const { view, client } = await page(t, () => respond())
  change(selectByValue(view, buildA), buildA)
  await until(() => labels(view).includes('ELSA-1'))
  const refetch = () => client.refetchQueries({ predicate: (q) => q.queryKey[2] === 'findings', type: 'active' })
  let release
  respond = () => new Promise((resolve) => { release = resolve })
  const started = refetch()
  await until(() => typeof release === 'function')
  assert.match(labels(view), /ELSA-1/)
  assert.match(labels(view), /최근 출처 수집 성공/)
  assert.equal(view.root.findByProps({ 'aria-label': '다음 페이지' }).props.disabled, false)
  change(view.root.findByProps({ 'aria-label': 'CVE 번호 검색' }), 'typed while refreshing')
  const pending = { ...result, status: 'pending', refreshing: true, total: null, items: [], sources: [] }
  await act(async () => { release(pending); await started })
  await until(() => labels(view).includes('새 자료 수집 중, 이전 결과 표시'))
  assert.match(labels(view), /ELSA-1/)
  respond = () => { throw Error('offline') }
  await act(async () => { await refetch() })
  await until(() => labels(view).includes('마지막 조회 결과를 표시합니다'))
  assert.match(labels(view), /ELSA-1/)
  respond = () => ({ ...result, total: 0, items: [], severity_counts: { critical: 0, high: 0, medium: 0, low: 0, unknown: 0 } })
  await act(async () => { await refetch() })
  await until(() => labels(view).includes('조건에 해당하는 CVE가 없습니다'))
  assert.equal(view.root.findByProps({ id: 'kernel-findings-title' }).findByType('span').children.join(''), '0건')
  assert.doesNotMatch(labels(view), /ELSA-1/)
  respond = () => pending
  await act(async () => { await refetch() })
  await until(() => labels(view).includes('새 자료 수집 중, 이전 결과 표시'))
  assert.equal(view.root.findByProps({ 'aria-label': '검색 조건별 위험도 필터' }).findAllByType('strong')[0].children.join(''), '0')
  change(selectByValue(view, buildB), buildB)
  await until(() => labels(view).includes('결과 미확인'))
  assert.equal(view.root.findByProps({ 'aria-label': '검색 조건별 위험도 필터' }).findAllByType('strong')[0].children.join(''), '—')
})
