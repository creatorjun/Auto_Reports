// frontend/tests/dashboardIssueTypeFilters.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import ts from 'typescript'

const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')
const require = createRequire(import.meta.url)
const modules = new Map()

function loadSource(relativePath) {
  const base = path.join(sourceRoot, relativePath)
  const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
  assert.ok(filename, `Missing source module: ${relativePath}`)
  if (modules.has(filename)) return modules.get(filename).exports
  const module = { exports: {} }
  modules.set(filename, module)
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
    fileName: filename,
  }).outputText
  new Function('require', 'module', 'exports', compiled)(
    (dependency) => dependency.startsWith('@/') ? loadSource(dependency.slice(2)) : require(dependency),
    module,
    module.exports,
  )
  return module.exports
}

const { buildDashboardData } = loadSource('presentation/hooks/useDashboardData.ts')
const { default: IssueTypeFilter } = loadSource('presentation/components/common/IssueTypeFilter.tsx')
const { isDashboardExcludedIssueType, isDashboardIssueTypeFilterOption } = loadSource('domain/DashboardIssueTypePolicy.ts')
const VISIBLE_TYPES = ['서비스 요청', '개선']
const HIDDEN_TYPES = ['승인된 서비스 요청', '케이스']
const ALL_TYPES = [...VISIBLE_TYPES, ...HIDDEN_TYPES, '라이선스', '기타']

function widget(data, total = 0) {
  return { name: '검증 지표', total, jql: '', data }
}

function fixtureReport(scope = 'standard') {
  const byType = { '서비스 요청': 10, '개선': 20, '승인된 서비스 요청': 3, '케이스': 5, '라이선스': 99 }
  const slaByType = {
    '서비스 요청': { met: 9, total: 10 },
    '개선': { met: 10, total: 20 },
    '승인된 서비스 요청': { met: 2, total: 3 },
    '케이스': { met: 4, total: 5 },
    '라이선스': { met: 99, total: 99 },
  }
  const issues = ALL_TYPES.flatMap((type, index) => ['02', '08'].map((month) => ({
    key: `TEST-${index}-${month}`,
    summary: `${type} ${month}월 검증`,
    type,
    status: '자료 요청',
    stage_index: 1,
    created: `2026-${month}-15T09:00:00`,
    elapsed_days: 1,
    reporter: '보고자',
    tac_team: '담당자',
  })))
  const monthly = Array.from({ length: 12 }, (_, index) => ({
    month: `${index + 1}월`, year: 2026, month_num: index + 1,
    count: 144, by_type: { ...byType }, always_included: 7,
  }))
  const slaMonthly = monthly.map(({ month, year, month_num }) => ({
    month, year, month_num, rate: 90, met: 130, total: 144,
    by_type: structuredClone(slaByType), always_included: { met: 6, total: 7 },
  }))
  const resolutionByType = Object.fromEntries(ALL_TYPES.map((type) => [type, { avg_days: 2, avg_hours: 48, count: 2 }]))
  return {
    id: 1, scope, report_year: scope === 'annual' ? 2026 : null,
    week_start: '2026-01-01', week_end: '2026-12-31', report_date: '2026-12-31',
    created_at: '2026-12-31T09:00:00', sentiment: null, ai_analysis: null,
    widgets: {
      w1: widget({ issue_types: [...VISIBLE_TYPES, ...HIDDEN_TYPES, '라이선스'], by_type: { ...byType }, always_included: 7 }, 144),
      w2: widget({ by_type: { ...byType }, always_included: 7 }, 144),
      w3: widget({ created: issues.length, resolved: issues.length, created_details: issues, resolved_details: issues.map((issue) => ({ ...issue, resolved: issue.created })) }),
      w4: widget({ issue_details: issues }),
      w5: widget({ issue_details: issues }),
      w6: widget({ issue_details: issues }),
      w7: widget({ issue_details: issues }),
      w8: widget({ monthly }),
      w9: widget({ monthly: structuredClone(monthly) }),
      w10: widget({ monthly: slaMonthly }),
      w11: widget({ monthly: structuredClone(slaMonthly) }),
      w12: widget({ violation_distribution: [{ stage: '해결 시간 SLA', count: issues.length, rate: 100, issue_details: issues }] }),
      w13: widget({ by_status_details: { '자료 요청': issues } }),
      w14: widget({ by_type: resolutionByType, by_semester: { h1: resolutionByType, h2: resolutionByType } }),
    },
  }
}

function assertHiddenIssuesIncluded(data, expectedTypes, expectedIssueCount) {
  for (const issues of [
    data.weekly.weeklyCreated,
    data.weekly.weeklyResolved,
    data.recentAndIncomplete.recentIssues,
    data.statusIssues.reviewIssues,
    data.statusIssues.dataRequestIssues,
    data.statusIssues.resultPendingIssues,
    data.slaDonut.w12Distribution[0].issue_details,
    data.slaDelay.w13ByStatusDetails['자료 요청'],
  ]) {
    assert.equal(issues.length, expectedIssueCount)
    assert.deepEqual([...new Set(issues.map((issue) => issue.type))].sort(), [...expectedTypes].sort())
  }
  assert.deepEqual(Object.keys(data.resolutionByType).sort(), [...expectedTypes].sort())
}

test('hidden filter choices remain eligible for dashboard statistics', () => {
  for (const type of HIDDEN_TYPES) {
    assert.equal(isDashboardIssueTypeFilterOption(type), false)
    assert.equal(isDashboardIssueTypeFilterOption(` ${type} `), false)
    assert.equal(isDashboardExcludedIssueType(type), false)
  }
  assert.equal(isDashboardIssueTypeFilterOption('서비스 요청'), true)
  assert.equal(isDashboardExcludedIssueType('라이선스'), true)
})

for (const scope of ['standard', 'annual']) {
  test(`${scope} filters omit the two choices while default statistics retain their issues`, () => {
    const report = fixtureReport(scope)
    const before = structuredClone(report)
    const data = buildDashboardData(report)
    assert.deepEqual(data.filter.issueTypes, VISIBLE_TYPES)
    assert.equal(data.filter.supportsIssueTypeFiltering, true)
    const markup = renderToStaticMarkup(createElement(IssueTypeFilter, {
      issueTypes: data.filter.issueTypes,
      selectedTypes: null,
      selectedSemester: null,
      supported: data.filter.supportsIssueTypeFiltering,
      semesterSupported: data.filter.supportsSemesterFiltering,
      onToggle() {}, onSemesterChange() {}, onReset() {},
    }))
    assert.doesNotMatch(markup, /승인된 서비스 요청|케이스|라이선스/)
    assert.match(markup, /2\/2/)
    for (const type of VISIBLE_TYPES) assert.ok(markup.includes(type))
    assert.equal(data.yearly.w1YearlyCreated, 45)
    assert.equal(data.yearly.w2YearlyResolved, 45)
    assert.equal(data.monthlyCount.w8Monthly[0].count, 45)
    assert.equal(data.slaMonthly.w10Monthly[0].total, 45)
    assertHiddenIssuesIncluded(data, [...VISIBLE_TYPES, ...HIDDEN_TYPES, '기타'], 10)
    assert.deepEqual(report, before)
  })

  test(`${scope} selecting another type keeps hidden choices and outside totals exactly once`, () => {
    const data = buildDashboardData(fixtureReport(scope), new Set(['서비스 요청']))
    assert.equal(data.yearly.w1YearlyCreated, 25)
    assert.equal(data.yearly.w2YearlyResolved, 25)
    for (const entry of [...data.monthlyCount.w8Monthly, ...data.monthlyCount.w9Monthly]) assert.equal(entry.count, 25)
    for (const entry of [...data.slaMonthly.w10Monthly, ...data.slaMonthly.w11Monthly]) {
      assert.equal(entry.total, 25)
      assert.equal(entry.met, 21)
      assert.equal(entry.rate, 84)
    }
    assertHiddenIssuesIncluded(data, ['서비스 요청', ...HIDDEN_TYPES, '기타'], 8)
  })

  test(`${scope} clearing visible choices preserves hidden types within the selected semester`, () => {
    const data = buildDashboardData(fixtureReport(scope), new Set(), 'h1')
    assert.equal(data.yearly.w1YearlyCreated, 90)
    assert.equal(data.yearly.w2YearlyResolved, 90)
    assert.equal(data.monthlyCount.w8Monthly.length, 6)
    assert.equal(data.monthlyCount.w8Monthly[0].count, 15)
    assert.equal(data.slaMonthly.w10Monthly.length, 6)
    assert.equal(data.slaMonthly.w10Monthly[0].met, 12)
    assert.equal(data.slaMonthly.w10Monthly[0].total, 15)
    assert.equal(data.slaMonthly.w10Monthly[0].rate, 80)
    assertHiddenIssuesIncluded(data, [...HIDDEN_TYPES, '기타'], 3)
    for (const issue of data.recentAndIncomplete.recentIssues) assert.ok(issue.created.startsWith('2026-02'))
  })
}

test('reports that already aggregate hidden types outside by_type do not double count them', () => {
  const report = fixtureReport()
  report.widgets.w1.data.issue_types = VISIBLE_TYPES
  for (const data of [report.widgets.w1.data, report.widgets.w2.data, ...report.widgets.w8.data.monthly, ...report.widgets.w9.data.monthly]) {
    for (const type of HIDDEN_TYPES) delete data.by_type[type]
    data.always_included = 15
  }
  for (const entry of [...report.widgets.w10.data.monthly, ...report.widgets.w11.data.monthly]) {
    for (const type of HIDDEN_TYPES) delete entry.by_type[type]
    entry.always_included = { met: 12, total: 15 }
  }
  const data = buildDashboardData(report, new Set(['서비스 요청']))
  assert.equal(data.yearly.w1YearlyCreated, 25)
  assert.equal(data.monthlyCount.w8Monthly[0].count, 25)
  assert.equal(data.slaMonthly.w10Monthly[0].total, 25)
  assert.equal(data.slaMonthly.w10Monthly[0].met, 21)
})
