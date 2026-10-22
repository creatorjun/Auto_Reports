// frontend/tests/frontendRenderPerformance.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')

function sourceLoader(overrides = {}) {
  const modules = new Map()
  function load(relative) {
    relative = relative.replaceAll('\\', '/')
    if (Object.hasOwn(overrides, relative)) return overrides[relative]
    const base = path.join(sourceRoot, relative)
    const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
    assert.ok(filename, `Missing source: ${relative}`)
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    if (filename.endsWith('.json')) {
      const data = JSON.parse(fs.readFileSync(filename, 'utf8'))
      module.exports = { ...data, default: data }
      return module.exports
    }
    const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX }, fileName: filename,
    }).outputText
    new Function('require', 'module', 'exports', compiled)((dependency) => {
      if (dependency.startsWith('@/')) return load(dependency.slice(2))
      if (dependency.startsWith('.')) return load(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)))
      return require(dependency)
    }, module, module.exports)
    return module.exports
  }
  return load
}

const load = sourceLoader()
const sorting = load('presentation/utils/issueTableSorting')

function news(index = 0) {
  return { id: String(index), source_id: 'cisco', kind: 'advisory', title: `Original ${index}`, title_ko: null, summary: 'Original summary', summary_ko: `한국어 요약 ${index}`, url: 'https://nvd.nist.gov/', published_at: '2026-10-20T15:00:00Z', updated_at: null, cve_ids: [], severity: 'high', cvss_score: 8.1, cvss_version: '3.1', known_exploited: false, vendor: '', product: '', due_date: null }
}

function textOf(view) { return JSON.stringify(view.toJSON()) }

function render(t, component, props) {
  let view
  act(() => { view = TestRenderer.create(React.createElement(component, props)) })
  t.after(() => act(() => view.unmount()))
  return view
}

test('table sorting prepares each value once while preserving missing-last and stable natural order', () => {
  const input = Object.freeze(Array.from({ length: 1001 }, (_, index) => Object.freeze({ key: index, value: index % 23 === 0 ? null : `TAC-${(index * 31) % 97}` })))
  const collator = new Intl.Collator('ko', { numeric: true, sensitivity: 'base' })
  for (const direction of ['asc', 'desc']) {
    let reads = 0
    const columns = [{ header: 'value', sortValue: (row) => { reads += 1; return row.value } }]
    const actual = sorting.sortIssueTableRows(input, columns, { column: 'value', direction })
    const expected = [...input].sort((a, b) => a.value === null ? b.value === null ? 0 : 1 : b.value === null ? -1 : collator.compare(a.value, b.value) * (direction === 'asc' ? 1 : -1))
    assert.deepEqual(actual, expected)
    assert.equal(reads, input.length)
    assert.notEqual(actual, input)
  }
  assert.equal(sorting.sortIssueTableRows(input, [], null), input)
  assert.equal(sorting.sortIssueTableRows(input, [], { column: 'unknown', direction: 'asc' }), input)
})

test('annual detail pagination reuses sorted rows and invalidates on filters, dates and fresh data', (t) => {
  let sorts = 0
  const instance = sourceLoader({
    'presentation/utils/issueTableSorting': { ...sorting, sortIssueTableRows(...args) { sorts += 1; return sorting.sortIssueTableRows(...args) } },
    'presentation/components/common/IssueTableModal': { default: (props) => React.createElement('modal', props, props.headerSlot) },
  })
  const Modal = instance('presentation/components/annual/AnnualIssueDetailsModal').default
  const issues = Array.from({ length: 45 }, (_, index) => ({ key: `TAC-${45 - index}`, summary: index % 2 ? '검색 대상' : '다른 대상', type: '개선', created: `2026-10-${String(index % 20 + 1).padStart(2, '0')}`, resolved: `2026-11-${String(index % 20 + 1).padStart(2, '0')}` }))
  const props = { title: '상세', total: issues.length, issues, dateField: 'created', onClose() {} }
  const view = render(t, Modal, props)
  const modal = () => view.root.findByType('modal').props
  const next = () => view.root.findAllByType('button').find((button) => button.children.join('') === '다음')
  act(() => modal().onSortChange({ column: '티켓', direction: 'asc' }))
  assert.equal(sorts, 2)
  act(() => next().props.onClick())
  assert.equal(sorts, 2)
  assert.equal(modal().data[0].key, 'TAC-21')
  act(() => view.root.findByType('input').props.onChange({ target: { value: '검색' } }))
  assert.equal(sorts, 3)
  assert.equal(modal().data[0].key, 'TAC-2')
  act(() => view.update(React.createElement(Modal, { ...props, dateField: 'resolved' })))
  assert.equal(sorts, 4)
  assert.ok(modal().columns.some((column) => column.header === '해결일시'))
  act(() => view.update(React.createElement(Modal, { ...props, dateField: 'resolved', issues: [...issues, { key: 'TAC-0', summary: '검색 새 항목', type: '개선' }] })))
  assert.equal(sorts, 5)
  assert.equal(modal().data[0].key, 'TAC-0')
})

test('news rows skip unchanged parent ticks but update display, source and summarized content', (t) => {
  let renders = 0
  const service = load('application/services/securityNews')
  const instance = sourceLoader({ 'application/services/securityNews': { ...service, securityNewsDisplayText(...args) { renders += 1; return service.securityNewsDisplayText(...args) } } })
  const NewsList = instance('presentation/components/security/SecurityNewsList').default
  const items = Array.from({ length: 20 }, (_, index) => news(index))
  function List({ tick, language = 'ko', rows = items, source = 'Cisco' }) {
    return React.createElement('section', { 'data-tick': tick }, React.createElement(NewsList, { items: rows, language, sources: new Map([['cisco', source]]) }))
  }
  const view = render(t, List, { tick: 0 })
  assert.equal(renders, 20)
  const content = view.root.findByType('tbody').findAllByType('tr').map((row) => row.props)
  for (let tick = 1; tick <= 10; tick += 1) act(() => view.update(React.createElement(List, { tick })))
  assert.equal(renders, 20)
  assert.deepEqual(view.root.findByType('tbody').findAllByType('tr').map((row) => row.props), content)
  act(() => view.update(React.createElement(List, { tick: 11, language: 'original' })))
  assert.equal(renders, 40)
  assert.match(textOf(view), /Original 0/)
  act(() => view.update(React.createElement(List, { tick: 12, language: 'original', source: '새 출처' })))
  assert.equal(renders, 60)
  assert.match(textOf(view), /새 출처/)
  const rows = [...items]
  rows[0] = { ...rows[0], title: '최신 원문', title_ko: '최신 번역' }
  act(() => view.update(React.createElement(List, { tick: 13, language: 'original', source: '새 출처', rows })))
  assert.equal(renders, 61)
  assert.match(textOf(view), /최신 원문/)
  act(() => view.update(React.createElement(List, { tick: 14, source: '새 출처', rows })))
  assert.equal(renders, 81)
  rows[1] = { ...rows[1], summary_ko: '갱신된 한 줄 요약' }
  act(() => view.update(React.createElement(List, { tick: 15, source: '새 출처', rows })))
  assert.equal(renders, 82)
  assert.match(textOf(view), /갱신된 한 줄 요약/)
})

test('news date formatters retain exact Korean KST output across date boundaries and missing values', () => {
  const { securityDateLabel } = load('presentation/components/security/securityNewsFormatting')
  const inputs = [null, '', 'invalid', '2026-10-20', '2026-10-20T14:59:59Z', '2026-10-20T15:00:00Z', '2025-12-31T15:00:00Z', '2024-02-29T15:00:00Z', '2026-10-21T00:00:00+09:00']
  for (const value of inputs) for (const includeTime of [false, true]) {
    const expected = !value || !Number.isFinite(Date.parse(value)) ? '날짜 미제공' : new Date(value).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', ...(includeTime ? { hour: '2-digit', minute: '2-digit', hour12: false } : {}) })
    assert.equal(securityDateLabel(value, includeTime), expected)
  }
})

test('SLA column resizing and sorting reuse ticket rows while details and Jira context stay current', (t) => {
  const JiraContext = React.createContext({ jiraBrowse: 'https://jira.example/browse' })
  let rowRenders = 0
  const instance = sourceLoader({
    'presentation/context/JiraContext': { useJira() { rowRenders += 1; return React.useContext(JiraContext) } },
    'presentation/hooks/useTablePreferences': { useTablePreferences(_key, defaults) { const [sort, setSort] = React.useState(null); const [widths, setWidths] = React.useState(defaults); return { sort, setSort, widths, setWidths } } },
    'presentation/components/sla-violations/SlaViolationTableHeader': {
      default: (props) => React.createElement('header-control', props), DEFAULT_SLA_COLUMN_WIDTHS: { key: 1, summary: 2 }, MIN_SLA_COLUMN_WIDTHS: 0.1,
      SLA_TICKET_COLUMNS: [{ key: 'key' }, { key: 'summary' }], resizeSlaColumnWidths: (current, left, right, delta) => ({ ...current, [left]: current[left] + delta, [right]: current[right] - delta }),
    },
  })
  const List = instance('presentation/components/sla-violations/SlaViolationList').default
  const tickets = Array.from({ length: 40 }, (_, index) => ({ key: `TAC-${40 - index}`, summary: `제목 ${index}`, issue_type: '서비스 요청', created_at: '2026-10-01T00:00:00Z', elapsed_days: index, partners: [], breaches: [{ metric: 'resolution', breached_at: null, status: '진행 중' }], warnings: [] }))
  const initialContext = { jiraBrowse: 'https://jira.example/browse' }
  function Page({ context = initialContext, rows = tickets }) { return React.createElement(JiraContext.Provider, { value: context }, React.createElement(List, { tickets: rows })) }
  const view = render(t, Page, {})
  assert.equal(rowRenders, tickets.length)
  const header = () => view.root.findByType('header-control').props
  for (let index = 0; index < 10; index += 1) act(() => header().onResize('key', 'summary', 0.01))
  assert.equal(rowRenders, tickets.length)
  act(() => header().onSort({ key: 'key', direction: 'asc' }))
  assert.equal(rowRenders, tickets.length)
  assert.match(view.root.findAllByType('a')[0].props.href, /TAC-1$/)
  act(() => view.root.findByProps({ 'aria-label': 'TAC-1 상세 펼치기' }).props.onClick())
  assert.equal(rowRenders, tickets.length + 1)
  assert.equal(view.root.findByProps({ 'aria-label': 'TAC-1 상세 접기' }).props['aria-expanded'], true)
  const context = { jiraBrowse: 'https://new.example/browse' }
  act(() => view.update(React.createElement(Page, { context })))
  assert.equal(rowRenders, tickets.length * 2 + 1)
  assert.ok(view.root.findAllByType('a').every((link) => link.props.href.startsWith('https://new.example/')))
  const rows = tickets.map((ticket) => ticket.key === 'TAC-1' ? { ...ticket, summary: '갱신된 제목' } : ticket)
  act(() => view.update(React.createElement(Page, { context, rows })))
  assert.equal(rowRenders, tickets.length * 2 + 2)
  assert.match(textOf(view), /갱신된 제목/)
  assert.equal(view.root.findByProps({ 'aria-label': 'TAC-1 상세 접기' }).props['aria-expanded'], true)
})

test('partner page preserves filter contracts and child option references through searches and selections', (t) => {
  const service = load('application/services/dashboardData')
  const monthly = Array.from({ length: 12 }, (_, index) => ({ year: 2026, month_num: index + 1, month: `${index + 1}월`, count: 1, by_status_type: { '할 일': { '개선': 1 } } }))
  const report = { id: 1, scope: 'standard', week_start: '2026-10-19', week_end: '2026-10-25', widgets: {
    w1: { total: 1, data: { issue_types: ['서비스 요청', '개선', '라이선스'], by_type: { '개선': 1 }, always_included: 0 } },
    w8: { data: { monthly } },
    w7: { data: { issue_details: [{ key: 'TAC-1', type: '개선', status: '할 일', created: '2026-10-20' }] } },
  } }
  const latest = { data: report, isLoading: false }
  let resolutions = 0
  const instance = sourceLoader({
    'application/services/dashboardData': { ...service, buildDashboardData() { assert.fail('Partner options should not build all dashboard aggregates') }, resolveDashboardFilterContract(value) { resolutions += 1; return service.resolveDashboardFilterContract(value) } },
    'presentation/hooks/useReport': { useLatestReport: () => latest },
    'presentation/components/partner/PartnerOrgPanel': { default: (props) => React.createElement('org-panel', props) },
    'presentation/components/partner/PartnerMemberPanel': { default: (props) => React.createElement('member-panel', props) },
    'presentation/components/partner/PartnerIssuePanel': { default: (props) => React.createElement('issue-panel', props) },
    'presentation/components/common/IssueTypeFilter': { default: (props) => React.createElement('filter-panel', props) },
  })
  const Page = instance('presentation/pages/PartnerManagementPage').default
  const view = render(t, Page, {})
  const issuePanel = () => view.root.findByType('issue-panel').props
  const filterPanel = () => view.root.findByType('filter-panel').props
  const originalOptions = issuePanel().issueTypes
  const originalStatuses = filterPanel().statuses
  const expected = service.buildDashboardData(report).filter
  assert.deepEqual(originalOptions, expected.issueTypes.filter((type) => type !== '라이선스'))
  assert.deepEqual(originalStatuses, expected.statusTypes)
  assert.equal(filterPanel().supported, expected.supportsIssueTypeFiltering)
  assert.equal(filterPanel().semesterSupported, expected.supportsSemesterFiltering)
  assert.equal(issuePanel().reportYear, expected.reportYear)
  act(() => view.root.findByType('org-panel').props.onSearchChange('회사'))
  act(() => view.root.findByType('member-panel').props.onSearchChange('담당자'))
  act(() => issuePanel().onSearchChange('티켓'))
  act(() => view.root.findByType('org-panel').props.onSelect({ id: '1', name: '회사', issue_count: 2 }))
  act(() => filterPanel().onToggle('개선'))
  assert.equal(issuePanel().issueTypes, originalOptions)
  assert.equal(filterPanel().statuses, originalStatuses)
  assert.equal(resolutions, 1)
  act(() => issuePanel().onStatusesChange(['추가 상태']))
  assert.equal(issuePanel().issueTypes, originalOptions)
  assert.ok(filterPanel().statuses.includes('추가 상태'))
  latest.data = { ...report, widgets: { ...report.widgets, w1: { ...report.widgets.w1, data: { ...report.widgets.w1.data, issue_types: ['서비스 요청', '개선', 'CVE'] } } } }
  act(() => view.update(React.createElement(Page)))
  assert.equal(resolutions, 2)
  assert.notEqual(issuePanel().issueTypes, originalOptions)
  assert.deepEqual(issuePanel().issueTypes, ['서비스 요청', '개선', 'CVE'])
})
