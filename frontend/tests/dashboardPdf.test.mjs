// frontend/tests/dashboardPdf.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'
import pdfMake from 'pdfmake'
import { getDocument, OPS } from 'pdfjs-dist/legacy/build/pdf.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const source = fs.readFileSync(path.join(root, 'src/infrastructure/export/dashboardPdfDefinition.ts'), 'utf8')
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText
const { buildDashboardPdfDefinition } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)
const regularFont = path.join(root, 'src/assets/fonts/NanumGothic-Regular.ttf')
const boldFont = path.join(root, 'src/assets/fonts/NanumGothic-Bold.ttf')
pdfMake.setUrlAccessPolicy(() => false)
pdfMake.setLocalAccessPolicy((file) => [regularFont, boldFont].includes(path.resolve(file)))
pdfMake.addFonts({ NanumGothic: { normal: regularFont, bold: boldFont, italics: regularFont, bolditalics: boldFont } })

function chart(title, width = 530, height = 360) {
  return {
    kind: 'chart',
    title,
    subtitle: '상반기 · 서비스 요청',
    svg: `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><path d="M30 250 L130 75 L240 160 L400 30" fill="none" stroke="#12A677" stroke-width="4"/><text x="40" y="300" font-size="18" font-family="NanumGothic">벡터차트검증</text></svg>`,
    width,
    height,
    legend: [{ label: '등록 건수', color: '#12A677' }, { label: '해결 건수', color: '#365C83' }],
  }
}

function fixtureDocument() {
  return {
    title: '2026 연간 보고서 검증',
    period: '2026-01-01 ~ 2026-09-08',
    generatedAt: '2026. 9. 8. 14:30:00',
    filters: ['상반기', '서비스 요청'],
    sections: [
      { title: '주요 지표', blocks: [{ kind: 'metrics', items: Array.from({ length: 8 }, (_, index) => ({ label: `검증 지표 ${index + 1}`, value: `${index * 17}` })) }] },
      { title: 'AI 종합 분석', blocks: [{ kind: 'text', title: 'AI 종합 분석', paragraphs: ['한글 분석 문장이 검색 가능한 텍스트로 보존됩니다.', '검증용 권고사항을 확인합니다.'] }] },
      { title: '월별 이슈 현황', blocks: [chart('월별 등록 건수'), chart('월별 해결 건수')] },
      {
        title: '최근 이슈 현황',
        blocks: [{
          kind: 'table',
          headers: ['티켓', '제목', '진행 상태', '보고자', '담당자', '생성일'],
          rows: Array.from({ length: 73 }, (_, index) => [
            { text: `TAC-${String(index + 1).padStart(4, '0')}`, link: `https://example.invalid/browse/TAC-${index + 1}` },
            { text: `긴 한글 제목 보존 확인 ${index + 1} — ${'서비스 요청 상세 내용 '.repeat(4)}` },
            { text: '이슈 리뷰 중' },
            { text: '홍길동' },
            { text: '기술 지원팀' },
            { text: '2026-09-08' },
          ]),
        }],
      },
      {
        title: '재배포 품질 지표',
        blocks: [{
          kind: 'table',
          title: '최근 완료 재배포 이슈',
          headers: ['티켓', '제목', '재배포 원인'],
          rows: Array.from({ length: 7 }, (_, index) => [
            { text: `REDEPLOY-${index + 1}` },
            { text: `재배포 전체 목록 ${index + 1}` },
            { text: '설정 변경', fillColor: '#D5E4F2' },
          ]),
        }],
      },
    ],
  }
}

function nodes(value) {
  if (Array.isArray(value)) return value.flatMap(nodes)
  if (!value || typeof value !== 'object') return []
  return [value, ...Object.values(value).flatMap(nodes)]
}

function compact(value) {
  return value.replace(/\s/g, '')
}

async function renderAndRead(document) {
  const buffer = await pdfMake.createPdf(buildDashboardPdfDefinition(document)).getBuffer()
  const loadingTask = getDocument({ data: new Uint8Array(buffer), useSystemFonts: false, isEvalSupported: false })
  const pdf = await loadingTask.promise
  const pages = []
  try {
    for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber++) {
      const page = await pdf.getPage(pageNumber)
      const text = await page.getTextContent()
      const operators = await page.getOperatorList()
      pages.push({
        text: text.items.filter((item) => 'str' in item).map((item) => item.str).join(' '),
        operators: operators.fnArray,
        view: page.view,
        annotations: await page.getAnnotations(),
      })
      page.cleanup()
    }
  } finally {
    await loadingTask.destroy()
  }
  return { buffer, pages, text: pages.map((page) => page.text).join('\n') }
}

test('PDF definition preserves chart aspect ratios, legends and every supplied row without mutating input', () => {
  const document = fixtureDocument()
  const before = structuredClone(document)
  const definition = buildDashboardPdfDefinition(document)
  const allNodes = nodes(definition.content)
  const charts = allNodes.filter((node) => typeof node.svg === 'string')
  assert.equal(charts.length, 2)
  for (const output of charts) assert.ok(Math.abs(output.width / output.height - 530 / 360) < 0.00001)
  const tables = allNodes.filter((node) => node.table?.headerRows)
  assert.equal(tables.length, 2)
  assert.equal(tables[0].table.body.length - tables[0].table.headerRows, 73)
  assert.equal(tables[1].table.body.length - tables[1].table.headerRows, 7)
  assert.ok(tables[0].table.widths[1] > tables[0].table.widths[0])
  assert.ok(allNodes.some((node) => node.text === '■ ' && node.color === '#12A677'))
  assert.deepEqual(document, before)
})

test('real PDF embeds Korean fonts and keeps all issue pages, repeated headers, links and vector charts', { timeout: 60_000 }, async () => {
  const result = await renderAndRead(fixtureDocument())
  assert.equal(result.buffer.subarray(0, 5).toString(), '%PDF-')
  assert.match(result.buffer.toString('latin1'), /\/FontFile2\b/)
  assert.match(result.buffer.toString('latin1'), /\/ToUnicode\b/)
  assert.doesNotMatch(result.buffer.toString('latin1'), /\/Subtype\s*\/Image\b/)
  assert.ok(result.pages.length >= 4)
  assert.match(compact(result.text), /2026연간보고서검증/)
  assert.match(compact(result.text), /서비스요청/)
  assert.match(compact(result.text), /한글분석문장이검색가능한텍스트로보존됩니다/)
  assert.match(compact(result.text), /벡터차트검증/)
  assert.equal([...compact(result.text).matchAll(/AI종합분석/g)].length, 1)
  const chartHeadingPage = result.pages.find((page) => compact(page.text).includes('월별이슈현황'))
  assert.ok(chartHeadingPage)
  assert.match(compact(chartHeadingPage.text), /월별등록건수/)
  assert.match(compact(chartHeadingPage.text), /벡터차트검증/)
  for (let index = 1; index <= 73; index++) assert.ok(compact(result.text).includes(`TAC-${String(index).padStart(4, '0')}`), `missing recent issue ${index}`)
  for (let index = 1; index <= 7; index++) assert.ok(compact(result.text).includes(`REDEPLOY-${index}`), `missing redeployment issue ${index}`)
  const issuePages = result.pages.filter((page) => /TAC-\d{4}/.test(page.text))
  assert.ok(issuePages.length > 1)
  for (const page of issuePages) {
    assert.match(compact(page.text), /최근이슈현황/)
    assert.match(compact(page.text), /제목/)
    assert.ok(page.view[2] > page.view[3], 'page must be landscape')
  }
  assert.ok(result.pages.some((page) => page.annotations.some((entry) => entry.url === 'https://example.invalid/browse/TAC-73')))
  assert.ok(result.pages.some((page) => page.operators.includes(OPS.constructPath)))
  assert.ok(result.pages.every((page) => !page.operators.includes(OPS.paintImageXObject)))
})

test('a table row taller than a page retains its beginning and end across repeated table headers', { timeout: 60_000 }, async () => {
  const document = {
    title: '긴 행 검증',
    period: '2026-09-08',
    generatedAt: '2026-09-08 15:00',
    filters: [],
    sections: [{
      title: '전체 내용 보존',
      blocks: [{
        kind: 'table',
        headers: ['제목'],
        rows: [[{ text: `LONGROW-BEGIN\n${'페이지보다 긴 행의 모든 내용이 유지되어야 합니다.\n'.repeat(100)}LONGROW-END` }]],
      }],
    }],
  }
  const result = await renderAndRead(document)
  assert.ok(result.pages.length >= 3)
  assert.match(compact(result.pages[0].text), /LONGROW-BEGIN/)
  assert.match(compact(result.pages.at(-1).text), /LONGROW-END/)
  for (const page of result.pages) {
    assert.match(compact(page.text), /전체내용보존/)
    assert.match(compact(page.text), /제목/)
  }
})

test('ordinary table rows keep ticket keys and multiline date values together at page boundaries', { timeout: 60_000 }, async () => {
  const document = {
    title: '행 경계 검증',
    period: '2026-09-08',
    generatedAt: '2026-09-08 15:00',
    filters: [],
    sections: [{
      title: '최근 이슈 전체',
      blocks: [{
        kind: 'table',
        headers: ['티켓', '제목', '생성일과 경과일'],
        widths: [15, 60, 25],
        rows: Array.from({ length: 53 }, (_, index) => [
          { text: `ROW-${String(index + 1).padStart(3, '0')}` },
          { text: `줄바꿈이 필요한 이슈 상세 내용 ${'운영 환경 확인과 고객사 협의 사항을 검토합니다. '.repeat(index % 3 + 1)}` },
          { text: `2026-09-08\n${index + 1}일 경과\nEND-${String(index + 1).padStart(3, '0')}` },
        ]),
      }],
    }],
  }
  const result = await renderAndRead(document)
  assert.ok(result.pages.length >= 4)
  for (let index = 1; index <= 53; index++) {
    const suffix = String(index).padStart(3, '0')
    const rowPage = result.pages.find((page) => compact(page.text).includes(`ROW-${suffix}`))
    assert.ok(rowPage, `missing row ${suffix}`)
    assert.ok(compact(rowPage.text).includes(`END-${suffix}`), `row ${suffix} was split between pages`)
  }
})

test('empty tables and invalid optional width hints still produce a readable PDF', { timeout: 60_000 }, async () => {
  const document = {
    title: '빈 데이터 검증',
    period: '2026-09-08',
    generatedAt: '2026-09-08 15:00',
    filters: ['전체 기간'],
    sections: [{
      title: '표 검증',
      blocks: [
        { kind: 'table', title: '빈 표', headers: [], rows: [], widths: [] },
        { kind: 'table', title: '너비 기본값', headers: ['제목', '값'], rows: [[{ text: '너비 복원' }, { text: '17' }]], widths: [0, Number.NaN] },
      ],
    }],
  }
  const result = await renderAndRead(document)
  assert.match(compact(result.text), /데이터가없습니다/)
  assert.match(compact(result.text), /너비복원/)
})
