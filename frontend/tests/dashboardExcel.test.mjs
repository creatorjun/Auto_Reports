// frontend/tests/dashboardExcel.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import ts from 'typescript'
import { read, write, utils } from 'xlsx'

const require = createRequire(import.meta.url)
const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')

function loader(overrides = {}) {
  const modules = new Map()
  function load(relative) {
    const base = path.join(sourceRoot, relative)
    const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
    assert.ok(filename, `Missing module ${relative}`)
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
      fileName: filename,
    }).outputText
    new Function('require', 'module', 'exports', compiled)((dependency) => {
      if (dependency in overrides) return overrides[dependency]
      if (dependency.startsWith('@/')) return load(dependency.slice(2))
      if (dependency.startsWith('.')) return load(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)))
      return require(dependency)
    }, module, module.exports)
    return module.exports
  }
  return load
}

const load = loader()
const { buildDashboardExcelWorkbook } = load('infrastructure/export/dashboardExcelWorkbook')

function fixture() {
  return {
    title: 'TAC 대시보드', period: '2026-01-01 ~ 2026-10-06', generatedAt: '2026. 10. 6. 15:00',
    filters: ['하반기', '인시던트', '처리 중', '최근 이슈: 경과일 20일 이상', '최근 이슈 제목: 서울'],
    sections: [
      { title: '주요 지표', blocks: [{ kind: 'metrics', items: [{ label: '등록', value: '1,234' }, { label: '준수율', value: '98.5%' }] }] },
      { title: 'AI 종합 분석', blocks: [{ kind: 'text', title: '분석', paragraphs: ['한글과 줄바꿈\n전체 보존'] }] },
      { title: '월별 이슈', blocks: [{ kind: 'chart', title: '월별 등록', subtitle: '하반기', svg: '<svg/>', legend: [], width: 1, height: 1,
        data: { headers: ['월', '건수'], rows: [['7월', 12], ['8월', 0], ['9월', null]] } }] },
      { title: '최근 이슈 현황', blocks: [{ kind: 'table', headers: ['티켓', '제목', '생성일'], rows: Array.from({ length: 73 }, (_, index) => [
        { text: `TAC-${index + 1}`, link: `https://jira.example.test/browse/TAC-${index + 1}` },
        { text: index === 0 ? '=HYPERLINK("https://example.test")' : `[서울] 전체 제목 ${index + 1}\n두 번째 줄` },
        { text: '2026-10-06' },
      ]) }] },
    ],
  }
}

function roundTrip(document) {
  const buffer = write(buildDashboardExcelWorkbook(document), { type: 'buffer', bookType: 'xlsx', compression: true })
  assert.equal(buffer.subarray(0, 2).toString(), 'PK')
  return read(buffer, { type: 'buffer', cellFormula: true, cellStyles: true })
}

test('Excel gateway creates a readable binary workbook using the installed xlsx library', async () => {
  const { dashboardExcelExporter } = load('infrastructure/export/dashboardExcelExporter')
  const content = await dashboardExcelExporter.renderExcel(fixture())
  const workbook = read(new Uint8Array(await content.read()), { type: 'array' })
  assert.equal(workbook.Sheets['최근 이슈 현황'].A74.v, 'TAC-73')
})

test('real xlsx preserves Korean filters, all 73 rows, hyperlinks and numeric chart values', () => {
  const document = fixture()
  const before = structuredClone(document)
  const workbook = roundTrip(document)
  const metadata = utils.sheet_to_json(workbook.Sheets['내보내기 정보'], { header: 1 }).flat()
  for (const filter of document.filters) assert.ok(metadata.includes(filter))
  const issues = workbook.Sheets['최근 이슈 현황']
  const rows = utils.sheet_to_json(issues, { header: 1 })
  assert.equal(rows.length, 74)
  assert.equal(rows[73][0], 'TAC-73')
  assert.equal(rows[73][1], '[서울] 전체 제목 73\n두 번째 줄')
  assert.equal(issues.A74.l.Target, 'https://jira.example.test/browse/TAC-73')
  assert.equal(issues.B2.t, 's')
  assert.equal(issues.B2.f, undefined)
  assert.equal(issues.C2.t, 's')
  assert.equal(issues['!autofilter'].ref, 'A1:C74')
  assert.equal(workbook.Sheets['주요 지표'].B2.v, 1234)
  assert.equal(workbook.Sheets['주요 지표'].B3.v, '98.5%')
  assert.equal(workbook.Sheets['월별 등록'].B2.t, 'n')
  assert.equal(workbook.Sheets['월별 등록'].B3.v, 0)
  assert.equal(workbook.Sheets['월별 등록'].B4, undefined)
  assert.equal(workbook.Sheets['분석'].A2.v, '한글과 줄바꿈\n전체 보존')
  assert.deepEqual(document, before)
})

test('xlsx sanitizes and deduplicates long sheet names case-insensitively', () => {
  const title = '동일 제목 / 매우 긴 제목 [중복] '.repeat(3)
  const document = { ...fixture(), sections: ['내보내기 정보', title, title, 'Data', 'data', " 'quoted' "].map((title) => ({ title,
    blocks: [{ kind: 'metrics', items: [{ label: '값', value: '0' }] }],
  })) }
  const workbook = roundTrip(document)
  assert.equal(workbook.SheetNames.length, 7)
  assert.equal(new Set(workbook.SheetNames.map((name) => name.toLowerCase())).size, 7)
  for (const name of workbook.SheetNames) {
    assert.ok(name.length <= 31)
    assert.doesNotMatch(name, /[\\/?:*\[\]]/)
    assert.doesNotMatch(name, /^'|'$/)
  }
})

test('capture keeps zero-valued chart data even when there is no rendered SVG', () => {
  const { captureDashboardPdf } = load('presentation/utils/dashboardPdfCapture')
  const data = { headers: ['월', '건수'], rows: [['10월', 0]] }
  const attributes = { 'data-pdf-kind': 'chart', 'data-pdf-title': '월별 등록', 'data-export-table': JSON.stringify(data) }
  let section
  const chart = { getAttribute: (name) => attributes[name] ?? null, querySelector: () => null, querySelectorAll: () => [],
    textContent: '데이터가 없습니다', closest: () => section }
  section = { getAttribute: () => '월별 이슈', hasAttribute: () => false, querySelectorAll: () => [chart] }
  const document = captureDashboardPdf({ querySelectorAll: () => [section] }, fixture())
  assert.deepEqual(document.sections[0].blocks[0].data, data)
  assert.equal(roundTrip(document).Sheets['월별 등록'].B2.v, 0)
})

for (const scenario of ['failure', 'unmount']) {
  test(`Excel ${scenario} avoids a stale download and reports failure only while mounted`, async () => {
    let resolveRender
    let rejectRender
    const pending = new Promise((resolve, reject) => { resolveRender = resolve; rejectRender = reject })
    const errors = []
    let urlCreated = false
    const service = { renderExcel: () => pending }
    const stageLoad = loader({
      '@/presentation/context/ApplicationServicesContext': { useApplicationServices: () => ({ dashboardExport: service }) },
      '@/presentation/utils/dashboardPdfCapture': { waitForDashboardPdf: async () => {}, captureDashboardPdf: fixture },
    })
    const Stage = stageLoad('presentation/components/export/DashboardPdfExportStage').default
    let view
    try {
      await act(async () => { view = TestRenderer.create(React.createElement(Stage, { format: 'xlsx', fileName: 'report.xlsx', metadata: fixture(),
        onComplete: () => assert.fail('Unexpected completion'), onError: (message) => errors.push(message),
      }), { createNodeMock: () => ({}) }) })
      if (scenario === 'failure') {
        await act(async () => { rejectRender(new Error('write failed')) })
        assert.equal(errors.length, 1)
        assert.match(errors[0], /Excel/)
      } else {
        act(() => view.unmount())
        view = null
        await act(async () => { resolveRender({ createObjectUrl: () => { urlCreated = true; assert.fail('Unexpected URL') } }) })
        assert.deepEqual(errors, [])
      }
      assert.equal(urlCreated, false)
    } finally {
      if (view) act(() => view.unmount())
    }
  })
}

test('empty charts retain zero and null values, and empty issues have headers without a fabricated row', () => {
  const workbook = roundTrip({ ...fixture(), sections: [
    { title: '빈 표', blocks: [{ kind: 'table', headers: ['티켓', '제목'], rows: [[{ text: '데이터가 없습니다.' }]] }] },
    { title: '최근 이슈 현황', blocks: [{ kind: 'table', headers: ['티켓', '제목'], rows: [[{ text: '최근 이슈 데이터가 없습니다.' }]] }] },
    { title: '데이터 없음', blocks: [{ kind: 'text', title: '월별 SLA', paragraphs: ['SLA 데이터가 없습니다'],
      data: { headers: ['월', '대상', '준수율 (%)'], rows: [['10월', 0, null]] } }] },
  ] })
  assert.deepEqual(utils.sheet_to_json(workbook.Sheets['빈 표'], { header: 1 }), [['티켓', '제목']])
  assert.deepEqual(utils.sheet_to_json(workbook.Sheets['최근 이슈 현황'], { header: 1 }), [['티켓', '제목']])
  assert.equal(workbook.Sheets['월별 SLA'].B2.v, 0)
  assert.equal(workbook.Sheets['월별 SLA'].C2, undefined)
})

test('every dashboard chart exposes its displayed numbers only during export', () => {
  const charts = ['AreaChart', 'Area', 'XAxis', 'YAxis', 'CartesianGrid', 'Tooltip', 'Legend', 'ResponsiveContainer', 'PieChart', 'Pie', 'Cell', 'BarChart', 'Bar', 'ReferenceLine']
  const chartLoad = loader({ recharts: Object.fromEntries(charts.map((name) => [name, ({ children }) => React.createElement(name, null, children)])) })
  const { DashboardExportProvider } = chartLoad('presentation/context/DashboardExportContext')
  const examples = [
    ['charts/MonthlyCountChart', { title: '월별 등록', monthly: [{ month: '10월', count: 0 }], subtitle: '하반기', color: '#000000' }, [['10월', 0]]],
    ['charts/SlaMonthlyLineChart', { title: 'SLA', monthly: [{ month: '10월', met: 3, total: 4, rate: 75 }], subtitle: '하반기', color: '#000000' }, [['10월', 4, 3, 1, 75]]],
    ['charts/TypeBarChart', { byType: { '인시던트': { count: 2, avg_days: 1.5, avg_hours: 36 } } }, [['인시던트', 2, 1.5, 36]]],
    ['charts/SlaDonutChart', { total: 4, distribution: [{ stage: '최초 응답 SLA', count: 1, rate: 25 }] }, [['최초 응답 SLA', 1, 25]]],
    ['charts/ReasonPieChart', { byStatus: { '고객 확인': 5 } }, [['고객 확인', 5]]],
    ['charts/TrendLineChart', { created: 12, resolved: 8, periodLabel: '하반기' }, [['하반기', 12, 8]]],
    ['annual/AnnualMonthlyComparison', { created: [{ year: 2026, month_num: 1, month: '1월', count: 0 }], resolved: [], year: 2026, periodEnd: '2026-01-31', subtitle: '전체' }, [['1월', 0, null]]],
  ]
  for (const [relative, props, expected] of examples) {
    const Component = chartLoad(`presentation/components/${relative}`).default
    let view
    act(() => { view = TestRenderer.create(React.createElement(DashboardExportProvider, null, React.createElement(Component, props))) })
    try {
      const block = view.root.findAll((node) => node.type === 'div' && node.props['data-export-table'])[0]
      assert.ok(block, relative)
      assert.deepEqual(JSON.parse(block.props['data-export-table']).rows, expected, relative)
      act(() => view.update(React.createElement(Component, props)))
      assert.equal(view.root.findAll((node) => node.type === 'div' && node.props['data-export-table']).length, 0)
    } finally {
      act(() => view.unmount())
    }
  }
})

for (const format of ['pdf', 'xlsx']) {
  test(`${format} export routes the frozen document to its gateway and releases the download URL`, async () => {
    const rendered = []
    const downloads = []
    const released = []
    const document = fixture()
    let complete = 0
    const service = Object.fromEntries(['renderPdf', 'renderExcel'].map((method) => [method, async (value) => {
      rendered.push([method, value])
      return { createObjectUrl: () => ({ url: 'blob:test', close: () => released.push('closed') }) }
    }]))
    const stageLoad = loader({
      '@/presentation/context/ApplicationServicesContext': { useApplicationServices: () => ({ dashboardExport: service }) },
      '@/presentation/utils/dashboardPdfCapture': { waitForDashboardPdf: async () => {}, captureDashboardPdf: () => document },
    })
    const Stage = stageLoad('presentation/components/export/DashboardPdfExportStage').default
    const previous = globalThis.window
    globalThis.window = { document: { createElement: () => ({ click() { downloads.push(this.download) }, remove() {} }), body: { appendChild() {} } }, setTimeout(callback) { callback() } }
    let view
    try {
      await act(async () => { view = TestRenderer.create(React.createElement(Stage, { format, fileName: `report.${format}`, metadata: document,
        onComplete: () => complete++, onError: (message) => assert.fail(message),
      }), { createNodeMock: () => ({}) }) })
      assert.deepEqual(rendered, [[format === 'pdf' ? 'renderPdf' : 'renderExcel', document]])
      assert.deepEqual(downloads, [`report.${format}`])
      assert.deepEqual(released, ['closed'])
      assert.equal(complete, 1)
    } finally {
      if (view) act(() => view.unmount())
      globalThis.window = previous
    }
  })
}
