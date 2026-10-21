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
    if (filename.endsWith('.json')) {
      const data = JSON.parse(fs.readFileSync(filename, 'utf8'))
      module.exports = { ...data, default: data }
      return module.exports
    }
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
const { default: AiSummaryCard } = load('presentation/components/cards/AiSummaryCard')

function nodeText(node) {
  if (typeof node === 'string') return node
  return (node.children ?? []).map(nodeText).join('')
}

const legacyAnalysis = {
  summary: '선택 기간에 생성된 요청을 집계했습니다.',
  risks: ['처리 대기 요청이 누적되었습니다.'],
  recommendations: ['대기 요청의 우선순위를 검토하세요.'],
  sentiment: 'warning',
}

test('AI summaries preserve legacy reports without inventing bottlenecks or provider metadata', (t) => {
  let view
  act(() => { view = TestRenderer.create(React.createElement(AiSummaryCard, { ai: legacyAnalysis })) })
  t.after(() => act(() => view.unmount()))
  const rendered = nodeText(view.root)
  for (const value of [legacyAnalysis.summary, ...legacyAnalysis.risks, ...legacyAnalysis.recommendations, '요약', '문제점', '개선 제안']) {
    assert.ok(rendered.includes(value))
  }
  assert.doesNotMatch(rendered, /병목|Rovo|다음 주|KST|이전 분석 시점/)
  assert.equal(view.root.findAllByType('time').length, 0)
})

test('AI summaries omit empty bottlenecks and invalid timestamps without labeling another provider as Rovo', (t) => {
  let view
  act(() => { view = TestRenderer.create(React.createElement(AiSummaryCard, { ai: {
    ...legacyAnalysis, bottlenecks: [], provider: 'gemini', analyzed_at: 'invalid',
  } })) })
  t.after(() => act(() => view.unmount()))
  assert.doesNotMatch(nodeText(view.root), /병목|Rovo|Invalid Date|KST/)
  assert.equal(view.root.findAllByType('time').length, 0)
})

test('stale analysis stays visible with its original analysis time and clears the note only when current', (t) => {
  const ai = { ...legacyAnalysis, analyzed_at: '2026-10-21T02:03:00Z', is_stale: true }
  const original = structuredClone(ai)
  let view
  act(() => { view = TestRenderer.create(React.createElement(AiSummaryCard, { ai })) })
  t.after(() => act(() => view.unmount()))
  assert.equal(nodeText(view.root.findByProps({ role: 'status' })), '보고서 데이터가 갱신되었습니다. 이 총평은 이전 분석 시점 기준입니다.')
  assert.ok(nodeText(view.root).includes(ai.summary))
  assert.equal(view.root.findByType('time').props.dateTime, ai.analyzed_at)
  assert.deepEqual(ai, original)
  act(() => view.update(React.createElement(AiSummaryCard, { ai: { ...ai, is_stale: false } })))
  assert.equal(view.root.findAllByProps({ role: 'status' }).length, 0)
  assert.ok(nodeText(view.root).includes(ai.summary))
  assert.equal(view.root.findByType('time').props.dateTime, ai.analyzed_at)
})

test('Rovo summaries include bottlenecks and KST provenance in the shared PDF and Excel export capture', (t) => {
  const ai = { ...legacyAnalysis, bottlenecks: ['자료 요청 단계에 대기가 집중되었습니다.'], provider: 'rovo_automation', analyzed_at: '2026-10-21T02:03:00Z', is_stale: true }
  let view
  act(() => { view = TestRenderer.create(React.createElement(AiSummaryCard, { ai })) })
  t.after(() => act(() => view.unmount()))
  assert.match(nodeText(view.root), /Rovo/)
  assert.match(nodeText(view.root), /병목/)
  assert.equal(view.root.findByType('time').props.dateTime, ai.analyzed_at)
  assert.match(nodeText(view.root.findByType('time')), /2026.*10.*21.*11:03.*KST/)
  const card = view.root.findByProps({ 'data-pdf-kind': 'text' })
  const domNode = (node) => ({
    getAttribute: (name) => node.props[name] ?? null,
    textContent: nodeText(node),
    closest: () => null,
  })
  let section
  const block = {
    ...domNode(card),
    querySelector: () => domNode(card.findByType('h3')),
    querySelectorAll: () => card.findAll((node) => ['p', 'li'].includes(node.type) || node.props['data-pdf-paragraph']).map(domNode),
    closest: () => section,
  }
  section = { getAttribute: () => 'AI 종합 분석', hasAttribute: () => false, querySelectorAll: () => [block] }
  const { captureDashboardPdf } = load('presentation/utils/dashboardPdfCapture')
  const { buildDashboardPdfDefinition } = load('infrastructure/export/dashboardPdfDefinition')
  const document = captureDashboardPdf({ querySelectorAll: () => [section] }, fixture())
  const paragraphs = document.sections[0].blocks[0].paragraphs
  for (const value of ['분석: Rovo', '요약', ai.summary, '문제점', '병목', '개선 제안', '보고서 데이터가 갱신되었습니다. 이 총평은 이전 분석 시점 기준입니다.', ...ai.risks, ...ai.bottlenecks, ...ai.recommendations]) {
    assert.ok(paragraphs.some((paragraph) => paragraph.includes(value)), value)
  }
  assert.ok(paragraphs.some((paragraph) => /분석 시각: .*11:03.*KST/.test(paragraph)))
  const workbook = roundTrip(document)
  const excelContent = utils.sheet_to_json(workbook.Sheets['AI 종합 분석'], { header: 1 }).flat()
  const pdfContent = JSON.stringify(buildDashboardPdfDefinition(document))
  for (const paragraph of paragraphs) {
    assert.ok(excelContent.includes(paragraph), paragraph)
    assert.ok(pdfContent.includes(paragraph), paragraph)
  }
})

function fixture() {
  return {
    title: 'TAC 대시보드', period: '2026-01-01 ~ 2026-10-06', generatedAt: '2026. 10. 6. 15:00',
    filters: ['하반기', '인시던트', '처리 중', '최근 이슈: 경과일 20일 이상', '최근 이슈 제목: 서울'],
    sections: [
      { title: '주요 지표', blocks: [{ kind: 'metrics', items: [{ label: '등록', value: '1,234' }, { label: '준수율', value: '98.5%' }] }] },
      { title: 'AI 종합 분석', blocks: [{ kind: 'text', title: '분석', paragraphs: ['한글과 줄바꿈\n전체 보존'] }] },
      { title: '월별 이슈', blocks: [{ kind: 'chart', title: '월별 등록', subtitle: '하반기', svg: '<svg/>', legend: [], width: 1, height: 1,
        data: { headers: ['월', '건수'], rows: [['7월', 12], ['8월', 0], ['9월', null]] } }] },
      { title: '최근 이슈 현황', blocks: [{ kind: 'table', headers: ['티켓', '제목', '티켓 타입', '진행 상태', '보고자', '담당자', 'TAC 담당자', '생성일'], rows: Array.from({ length: 73 }, (_, index) => [
        { text: `TAC-${index + 1}`, link: `https://jira.example.test/browse/TAC-${index + 1}` },
        { text: index === 0 ? '=HYPERLINK("https://example.test")' : `[서울] 전체 제목 ${index + 1}\n두 번째 줄` },
        { text: ['서비스요청', '인시던트', '개선'][index % 3] },
        { text: '이슈 리뷰 중' },
        { text: '홍길동' },
        { text: '기술 지원팀' },
        { text: '김기술 선임' },
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
  assert.equal(issues.C1.v, '티켓 타입')
  assert.equal(issues.C2.v, '서비스요청')
  assert.equal(issues.C3.v, '인시던트')
  assert.equal(issues.C4.v, '개선')
  assert.equal(issues.H2.v, '2026-10-06')
  assert.equal(issues['!autofilter'].ref, 'A1:H74')
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
