// frontend/tests/frontendIoPerformance.test.mjs
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

function loadApplication() {
  const state = { organizations: [], issues: [], jiraBrowse: 'https://jira.example/browse' }
  const calls = { sorts: 0, filters: 0, rows: 0 }
  const modules = new Map()
  const dependencies = {
    '@tanstack/react-query': { useQuery: ({ queryKey }) => ({ data: queryKey[0] === 'partner-orgs' ? state.organizations : state.issues, isLoading: false }) },
    '@/presentation/context/ApplicationServicesContext': { useApplicationServices: () => ({ partners: {} }) },
    '@/presentation/context/JiraContext': { useJira: () => ({ jiraBrowse: state.jiraBrowse }) },
    '@/presentation/components/common/StatusBadge': { StatusBadge: ({ status }) => { calls.rows++; return React.createElement('span', null, status) } },
  }
  function loadSource(relative) {
    const base = path.resolve(sourceRoot, relative)
    const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate))
    assert.ok(filename, relative)
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
      fileName: filename,
    }).outputText
    const resolve = (dependency) => {
      if (dependency in dependencies) return dependencies[dependency]
      if (dependency.startsWith('@/')) return loadSource(dependency.slice(2))
      if (dependency.startsWith('.')) return loadSource(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)))
      return require(dependency)
    }
    new Function('require', 'module', 'exports', compiled)(resolve, module, module.exports)
    return module.exports
  }
  const partner = loadSource('domain/Partner')
  dependencies['@/domain/Partner'] = {
    ...partner,
    sortPartnerOrganizationsByIssueCount: (...args) => { calls.sorts++; return partner.sortPartnerOrganizationsByIssueCount(...args) },
    filterPartnerIssues: (...args) => { calls.filters++; return partner.filterPartnerIssues(...args) },
  }
  return { state, calls, loadSource }
}

async function mount(t, Component, initial) {
  let props = initial
  let renderer
  await act(async () => { renderer = TestRenderer.create(React.createElement(Component, props)) })
  t.after(async () => { await act(async () => renderer.unmount()) })
  return {
    renderer,
    async update(next = {}) {
      props = { ...props, ...next }
      await act(async () => renderer.update(React.createElement(Component, props)))
    },
  }
}

test('organization selection and search reuse sorting while new data refreshes order and selection', async (t) => {
  const app = loadApplication()
  const organizations = [
    { id: 'a', name: '가 조직', issue_count: 3 },
    { id: 'b', name: '나 조직', issue_count: 10 },
    { id: 'c', name: '가 두 번째', issue_count: 5 },
  ]
  app.state.organizations = organizations
  const selected = []
  const view = await mount(t, app.loadSource('presentation/components/partner/PartnerOrgPanel').default, {
    selectedOrgId: null, searchQuery: '', onSearchChange() {}, onSelect: (item) => selected.push(item),
  })
  assert.equal(app.calls.sorts, 1)
  await view.update({ selectedOrgId: 'b' })
  await view.update({ searchQuery: '가' })
  assert.equal(app.calls.sorts, 1)
  const organizationButtons = () => view.renderer.root.findAllByType('button').filter((button) => button.props.className?.includes('w-full text-left'))
  assert.deepEqual(organizationButtons().map((button) => button.findAllByType('span')[0].children[0]), ['가 두 번째', '가 조직'])
  await act(async () => organizationButtons()[0].props.onClick())
  assert.strictEqual(selected[0], organizations[2])
  app.state.organizations = [{ ...organizations[0], issue_count: 20 }, ...organizations.slice(1)]
  await view.update()
  assert.equal(app.calls.sorts, 2)
  assert.deepEqual(organizationButtons().map((button) => button.findAllByType('span')[0].children[0]), ['가 조직', '가 두 번째'])
  assert.deepEqual(organizations.map((item) => item.id), ['a', 'b', 'c'])
})

test('partner search reuses policy filtering and unchanged rows while data and filter changes update results', async (t) => {
  const app = loadApplication()
  const issue = (key, summary, status = '할 일') => ({ key, summary, status, type: '인시던트', created: '2026-03-10 09:00', stage_index: 0, elapsed_days: 1 })
  app.state.issues = [issue('TAC-1', 'first match'), issue('TAC-2', 'second match')]
  const view = await mount(t, app.loadSource('presentation/components/partner/PartnerIssuePanel').default, {
    orgId: '1', accountId: null, label: '조직', searchQuery: '', onSearchChange() {},
    issueTypes: ['인시던트'], selectedIssueTypes: null, selectedStatuses: null,
    selectedSemester: 'h1', reportYear: 2026, onStatusesChange() {},
  })
  assert.deepEqual(app.calls, { sorts: 0, filters: 1, rows: 2 })
  await view.update({ searchQuery: 'match', label: '변경된 조직 제목' })
  assert.deepEqual(app.calls, { sorts: 0, filters: 1, rows: 2 })
  await view.update({ searchQuery: 'second' })
  assert.equal(app.calls.filters, 1)
  assert.equal(app.calls.rows, 2)
  assert.equal(view.renderer.root.findAllByType('a')[0].props.href, 'https://jira.example/browse/TAC-2')
  app.state.issues = [app.state.issues[0], { ...app.state.issues[1], summary: 'second updated', status: '닫힘' }]
  await view.update()
  assert.equal(app.calls.filters, 2)
  assert.equal(app.calls.rows, 3)
  assert.ok(JSON.stringify(view.renderer.toJSON()).includes('second updated'))
  await view.update({ selectedStatuses: new Set(['할 일']) })
  assert.equal(app.calls.filters, 3)
  assert.equal(view.renderer.root.findAllByType('a').length, 0)
  await view.update({ selectedStatuses: null })
  app.state.jiraBrowse = 'https://changed.example/browse'
  await view.update()
  assert.equal(view.renderer.root.findAllByType('a')[0].props.href, 'https://changed.example/browse/TAC-2')
})

test('Excel width calculation caps wide columns without trimming values, rows, Unicode, multiline content or links', () => {
  const { buildDashboardExcelWorkbook } = loadApplication().loadSource('infrastructure/export/dashboardExcelWorkbook')
  const text = '긴 본문'.repeat(20_000)
  const rows = [
    [{ text: 'a\n가'.repeat(8) }, { text: '🙂'.repeat(8) }, { text, link: 'https://jira.example/browse/TAC-1' }],
    [{ text: 'short' }, { text: 'x'.repeat(65) }, { text: '다음 내용' }],
  ]
  const workbook = buildDashboardExcelWorkbook({
    title: '보고서', period: '2026', generatedAt: '2026-10-21', filters: [],
    sections: [{ title: '이슈', blocks: [{ kind: 'table', title: '전체', headers: ['줄', '문자', '본문'], rows }] }],
  })
  const sheet = workbook.Sheets['전체']
  assert.deepEqual(sheet['!cols'], [{ wch: 14 }, { wch: 60 }, { wch: 60 }])
  assert.equal(sheet.A2.v, 'a\n가'.repeat(8))
  assert.equal(sheet.B2.v, '🙂'.repeat(8))
  assert.equal(sheet.C2.v, text)
  assert.equal(sheet.C2.l.Target, 'https://jira.example/browse/TAC-1')
  assert.equal(sheet.C3.v, '다음 내용')
  assert.equal(sheet['!ref'], 'A1:C3')
  assert.equal(sheet['!autofilter'].ref, 'A1:C3')
})
