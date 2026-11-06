// frontend/tests/softwareCves.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import { createRequire } from 'node:module'
import { sourceLoader } from './helpers/loadCveSource.mjs'

const { QueryClient, QueryClientProvider } = createRequire(import.meta.url)('@tanstack/react-query')

const catalog = {
  openjdk: [{ version: '17.0.11', major: 17, label: '17.0.11' }, { version: '8u402', major: 8, label: '8u402' }],
  zulu: [{ version: '11.58.23', major: 11, label: 'Zulu 11.58.23 · Java 11.0.16.1 · PSU' }, { version: '17.70.111', major: 17, label: 'Zulu 17.70.111 · CPU' }],
  mariadb: [{ version:'10.11.5',series:'10.11',label:'10.11.5' }, { version:'10.6.20',series:'10.6',label:'10.6.20' }],
  mysql: [{ version:'8.0.35',series:'8.0',label:'8.0.35' }, { version:'8.4.1',series:'8.4',label:'8.4.1' }],
  postgresql: [{ version:'15.3',series:'15',label:'15.3' }, { version:'16.2',series:'16',label:'16.2' }],
}
const severity_counts = { critical: 0, high: 1, medium: 0, low: 0, unknown: 0 }
const coverage = { status: 'ready', refreshing: false, coverage_note: null, sources: [{ id: 'vendor', label: '공식 권고', url: 'https://example.test/advisories', status: 'ready', refreshed_at: '2026-11-01T01:00:00Z', note: null }] }
const fix = { advisory_id: 'JDK Advisory', advisory_url: 'https://example.test/advisory', fixed_version: null, affected_through: '17.0.11', component: 'HotSpot', cvss_score: 7.5, issued_at: '2026-10-20', title: 'Security update' }
const result = { ...coverage, total: 1, page: 1, page_size: 25, severity_counts, items: [{ cve_id: 'CVE-2026-1234', summary: '영향 확인', severity: 'high', fixes: [fix] }] }
const screen = (view) => JSON.stringify(view.toJSON())
const click = (node) => act(() => node.props.onClick())
const change = (node, value) => act(() => node.props.onChange({ target: { value } }))
const selectWith = (v, value) => v.root.findAllByType('select').find((s) => s.findAllByType('option').some((o) => o.props.value === value))
const byText = (v, text) => v.root.findAllByType('button').find((b) => b.children.includes(text))
async function until(predicate) {
  const deadline = Date.now() + 3000
  while (!predicate()) {
    assert(Date.now() < deadline, 'Timed out waiting for Java data')
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 5)) })
  }
}

async function render(t, getFindings = () => result, scope = 'java') {
  const calls = []
  const prefix = `/${scope}-cves`
  const labels = scope === 'java' ? { openjdk:'OpenJDK',zulu:'Azul Zulu' } : { mariadb:'MariaDB',mysql:'MySQL',postgresql:'PostgreSQL' }
  const gateway = { async get(pathname, { params, signal }) {
    assert.ok(signal)
    calls.push({ path: pathname, params })
    if (pathname === prefix + '/targets') return { data: { targets: Object.entries(labels).map(([id,label]) => ({ id,label,coverage:label+' 공식 자료',available:true })) } }
    if (pathname === prefix + '/releases') return { data: { ...coverage, versions: catalog[params.target] } }
    assert.equal(pathname, prefix)
    return { data: await getFindings(params) }
  } }
  const load = sourceLoader({ 'infrastructure/api/client': { default: gateway, __esModule: true } })
  const { ApplicationServicesProvider } = load('presentation/context/ApplicationServicesContext')
  const api = scope === 'java' ? load('infrastructure/api/javaCveApi').javaCveApi : load('infrastructure/api/dbCveApi').dbCveApi
  const Page = load('presentation/pages/SoftwareCvePage').default
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  let view
  act(() => {view = TestRenderer.create(React.createElement(QueryClientProvider,{client},
    React.createElement(ApplicationServicesProvider,{services:{[scope+'Cves']:api}}, React.createElement(Page,{scope}))))})
  t.after(() => {act(() => view.unmount());client.clear()})
  await until(() => selectWith(view, scope === 'java' ? '8u402' : '10.11.5'))
  return { view, calls, client, last: () => calls.filter((c) => c.path === prefix).at(-1)?.params }
}

test('switches target without reusing its version and keeps vendor evidence and real fixed releases distinct', async (t) => {
  const { view, last } = await render(t, (q) => q.target === 'openjdk' ? result : {
    ...result, items: [{ ...result.items[0], cve_id: 'CVE-2026-6789', fixes: [{ ...fix, advisory_id:'Azul advisory', affected_through:null, affected_version:'11.58.23', fixed_version:'11.60.19', channel:'PSU' }] }],
  })
  assert.equal(last(), undefined)
  change(selectWith(view, '17'), '17')
  assert.equal(selectWith(view,'8u402'), undefined)
  change(selectWith(view,'17.0.11'),'17.0.11')
  await until(() => screen(view).includes('JDK Advisory'))
  assert.deepEqual(last(),{target:'openjdk',version:'17.0.11',severity:'all',search:'',page:1,page_size:25})
  assert.match(screen(view),/영향 범위/)
  assert.match(screen(view),/수정 버전 미제공/)
  assert.match(screen(view),/HotSpot · CVSS 7.5/)
  const edit = byText(view, '환경 변경')
  assert.equal(edit.props['aria-expanded'],false)
  click(edit)
  click(byText(view,'Azul Zulu'))
  await until(() => selectWith(view,'11.58.23'))
  assert.doesNotMatch(screen(view),/JDK Advisory|CVE-2026-1234/)
  change(selectWith(view,'custom'),'custom')
  assert.match(screen(view),/Zulu11.58\+23-CA/)
  change(view.root.findByProps({'aria-label':'설치된 Zulu 빌드 직접 입력'}),'Zulu11.58+23-CA')
  act(() => view.root.findByType('form').props.onSubmit({preventDefault(){}}))
  await until(() => screen(view).includes('Azul advisory'))
  assert.equal(last().target,'zulu')
  assert.equal(last().version,'Zulu11.58+23-CA')
  assert.match(screen(view),/11\.60\.19/)
  assert.match(screen(view),/영향 버전/)
  assert.match(screen(view),/PSU/)
  assert.doesNotMatch(screen(view),/CVE-2026-1234/)
})

test('server filters and pagination retain the vendor and exact installed build', async (t) => {
  const { view, last } = await render(t, () => ({ ...result, total: 55, severity_counts:{...severity_counts, high:55} }))
  change(selectWith(view, '8u402'), '8u402')
  await until(() => byText(view,'환경 변경') && screen(view).includes('JDK Advisory'))
  click(view.root.findByProps({'aria-label':'다음 페이지'}))
  await until(() => last().page === 2 && screen(view).includes('JDK Advisory'))
  click(view.root.findByProps({'aria-label':'검색 조건별 위험도 필터'}).findAllByType('button')[2])
  await until(() => last().severity === 'high')
  assert.equal(last().page,1)
  change(view.root.findByProps({'aria-label':'CVE 번호 검색'}),'CVE-2026')
  act(() => view.root.findByType('form').props.onSubmit({preventDefault(){}}))
  await until(() => last().search === 'CVE-2026')
  assert.deepEqual(last(),{target:'openjdk',version:'8u402',severity:'high',search:'CVE-2026',page:1,page_size:25})
})

test('polling and failed replacement keep the same Java selection visible and never borrow results for another version', async (t) => {
  let response = result
  const { view, client } = await render(t, () => response)
  change(selectWith(view,'17.0.11'),'17.0.11')
  await until(() => screen(view).includes('JDK Advisory'))
  response = { ...result, status:'pending', refreshing:true, total:null, sources:[], items:[] }
  await act(async () => { await client.refetchQueries({predicate:q=>q.queryKey[0]==='java-cves' && q.queryKey[2]==='findings'}) })
  await until(() => screen(view).includes('새 자료 수집 중, 이전 결과 표시'))
  assert.match(screen(view),/JDK Advisory/)
  response = { ...response, status:'partial', refreshing:false, coverage_note:'새 공식 자료에서 해당 버전을 대조할 수 없습니다.' }
  await act(async () => { await client.refetchQueries({predicate:q=>q.queryKey[0]==='java-cves' && q.queryKey[2]==='findings'}) })
  await until(() => screen(view).includes('새 공식 자료에서'))
  assert.doesNotMatch(screen(view),/JDK Advisory/)
  change(selectWith(view,'8u402'),'8u402')
  await until(() => screen(view).includes('결과 미확인'))
  assert.doesNotMatch(screen(view),/JDK Advisory/)
  assert.equal(view.root.findByProps({'aria-label':'검색 조건별 위험도 필터'}).findAllByType('strong')[0].children.join(''),'—')
})

test('each database has its own series, request and official bounds, and an unknown build has no numerical total', async (t) => {
  const response = (request) => request.version === '999.1' ? { ...result, status:'partial', total:null, items:[], coverage_note:'입력한 계열을 확인할 수 없습니다.' } : { ...result,items:[{ ...result.items[0], fixes:[{
    ...fix,advisory_id:request.target+' 권고',component:'Server',series:'8.0',
    affected_from:'8.0.25',affected_from_inclusive:true,affected_through:'8.0.37',affected_through_inclusive:false,fixed_version:'8.0.37',
  }]}] }
  const { view, last } = await render(t, response, 'db')
  change(selectWith(view,'10.11'),'10.11')
  assert.equal(selectWith(view,'10.6.20'),undefined)
  change(selectWith(view,'10.11.5'),'10.11.5')
  await until(() => screen(view).includes('mariadb 권고'))
  click(byText(view,'환경 변경'))
  click(byText(view,'MySQL'))
  await until(() => selectWith(view,'8.0.35'))
  assert.doesNotMatch(screen(view),/mariadb 권고|10\.11\.5/)
  change(selectWith(view,'8.0.35'),'8.0.35')
  await until(() => screen(view).includes('mysql 권고'))
  assert.match(screen(view),/8\.0\.25 이상 ~ 8\.0\.37 미만/)
  assert.match(screen(view),/수정 버전 · /)
  assert.equal(last().target,'mysql')
  click(byText(view,'환경 변경'))
  click(byText(view,'PostgreSQL'))
  await until(() => selectWith(view,'15.3'))
  change(selectWith(view,'custom'),'custom')
  assert.match(screen(view),/SHOW server_version/)
  change(view.root.findByProps({'aria-label':'설치된 PostgreSQL 버전 직접 입력'}),'999.1')
  act(() => view.root.findByType('form').props.onSubmit({preventDefault(){}}))
  await until(() => screen(view).includes('입력한 계열'))
  assert.equal(last().target,'postgresql')
  assert.match(screen(view),/결과 미확인/)
  assert.doesNotMatch(screen(view),/mysql 권고/)
})
