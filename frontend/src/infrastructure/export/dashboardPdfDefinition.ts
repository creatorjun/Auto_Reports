// frontend/src/infrastructure/export/dashboardPdfDefinition.ts
import type {
  Content,
  ContentColumns,
  ContentStack,
  ContentTable,
  TableCell,
  TDocumentDefinitions,
} from 'pdfmake/interfaces'
import type {
  DashboardPdfCell,
  DashboardPdfChartBlock,
  DashboardPdfDocument,
  DashboardPdfMetricsBlock,
  DashboardPdfSection,
  DashboardPdfTableBlock,
  DashboardPdfTextBlock,
} from '@/domain/DashboardExport'

const PAGE_WIDTH = 841.89
const PAGE_HEIGHT = 595.28
const PAGE_MARGIN = 32
const CONTENT_WIDTH = PAGE_WIDTH - PAGE_MARGIN * 2
const COLUMN_GAP = 14
const CHART_WIDTH = (CONTENT_WIDTH - COLUMN_GAP) / 2
const INK = '#172033'
const MUTED = '#64748B'
const ACCENT = '#365C83'
const BORDER = '#DDE5EE'
const SURFACE = '#F5F8FC'

function card(stack: Content[], fillColor = SURFACE): ContentTable {
  return {
    table: {
      widths: ['*'],
      body: [[{ stack, fillColor }]],
      dontBreakRows: true,
    },
    layout: {
      hLineWidth: () => 0.6,
      vLineWidth: () => 0.6,
      hLineColor: () => BORDER,
      vLineColor: () => BORDER,
      paddingLeft: () => 12,
      paddingRight: () => 12,
      paddingTop: () => 11,
      paddingBottom: () => 11,
    },
  }
}

function metricRows(block: DashboardPdfMetricsBlock): Content[] {
  const rows: Content[] = []
  const width = (CONTENT_WIDTH - COLUMN_GAP * 3) / 4
  for (let offset = 0; offset < block.items.length; offset += 4) {
    const columns: ContentColumns['columns'] = block.items.slice(offset, offset + 4).map((item) => ({
      ...card([
        { text: item.label, fontSize: 9, color: MUTED, margin: [0, 0, 0, 7] },
        { text: item.value, fontSize: 21, bold: true, color: ACCENT },
      ]),
      width,
    }))
    while (columns.length < 4) columns.push({ text: '', width })
    rows.push({ columns, columnGap: COLUMN_GAP, margin: [0, 0, 0, 10] })
  }
  return rows
}

function textBlock(block: DashboardPdfTextBlock): Content[] {
  const content: Content[] = []
  if (block.title) {
    content.push({ text: block.title, style: 'blockTitle', headlineLevel: 2, margin: [0, 1, 0, 6] })
  }
  for (const paragraph of block.paragraphs) {
    content.push({ text: paragraph, lineHeight: 1.35, margin: [0, 0, 0, 7] })
  }
  return content
}

function chartCard(block: DashboardPdfChartBlock): ContentTable {
  const availableWidth = CHART_WIDTH - 26
  const sourceWidth = Number.isFinite(block.width) && block.width > 0 ? block.width : availableWidth
  const sourceHeight = Number.isFinite(block.height) && block.height > 0 ? block.height : 228
  const scale = Math.min(availableWidth / sourceWidth, 228 / sourceHeight)
  const stack: Content[] = [
    { text: block.title, style: 'blockTitle', margin: [0, 0, 0, 5] },
  ]
  if (block.subtitle) stack.push({ text: block.subtitle, fontSize: 8, color: MUTED, margin: [0, 0, 0, 7] })
  stack.push({
    svg: block.svg,
    width: sourceWidth * scale,
    height: sourceHeight * scale,
    alignment: 'center',
    margin: [0, 3, 0, 4],
  })
  if (block.legend.length) {
    stack.push({
      text: block.legend.flatMap((entry) => [
        { text: '■ ', color: entry.color },
        { text: `${entry.label}   `, color: MUTED },
      ]),
      fontSize: 8,
      color: MUTED,
      lineHeight: 1.25,
      alignment: 'center',
      margin: [0, 4, 0, 0],
    })
  }
  return { ...card(stack, '#FFFFFF'), unbreakable: true }
}

function chartRows(charts: DashboardPdfChartBlock[]): Content[] {
  const rows: Content[] = []
  for (let offset = 0; offset < charts.length; offset += 2) {
    const columns: ContentColumns['columns'] = charts.slice(offset, offset + 2).map((chart) => ({
      ...chartCard(chart),
      width: CHART_WIDTH,
    }))
    if (columns.length === 1) columns.push({ text: '', width: CHART_WIDTH })
    rows.push({ columns, columnGap: COLUMN_GAP, margin: [0, 0, 0, 12] })
  }
  return rows
}

function inferredWidth(header: string): number {
  if (header.includes('제목')) return 4.2
  if (header.includes('파트너사')) return 2.4
  if (header.includes('원인')) return 1.7
  if (/생성|완료|해결|경과/.test(header)) return 1.6
  if (/보고자|담당자|진행|상태|유형/.test(header)) return 1.3
  return 1
}

function tableWidths(block: DashboardPdfTableBlock, headers: string[]): number[] {
  const hasWidths = block.widths?.length === headers.length
    && block.widths.every((width) => Number.isFinite(width) && width > 0)
  const weights = hasWidths ? block.widths! : headers.map(inferredWidth)
  const total = weights.reduce((sum, width) => sum + width, 0)
  const availableWidth = CONTENT_WIDTH - headers.length * 14
  return weights.map((width) => availableWidth * width / total)
}

function tableCell(cell: DashboardPdfCell, rowIndex: number): TableCell {
  return {
    text: cell.text,
    fillColor: cell.fillColor || (rowIndex % 2 === 0 ? '#FFFFFF' : '#F8FAFD'),
    ...(cell.link ? { link: cell.link, color: ACCENT, decoration: 'underline' as const } : {}),
    margin: [0, 2, 0, 2],
  }
}

function conservativeTextHeight(value: string, width: number, fontSize: number): number {
  if (!Number.isFinite(width) || width <= 0) return Number.POSITIVE_INFINITY
  const charactersPerLine = Math.max(1, Math.floor(width / (fontSize * 2)))
  const lines = value.replace(/\t/g, '        ').split(/\r\n|[\n\r\u2028\u2029]/)
    .reduce((total, line) => total + Math.ceil(Array.from(line).length / charactersPerLine) + 1, 0)
  return lines * fontSize * 2
}

function canKeepRowsTogether(block: DashboardPdfTableBlock, headers: string[], widths: number[], caption: string, fontSize: number): boolean {
  const captionHeight = caption ? conservativeTextHeight(caption, CONTENT_WIDTH - 14, 10.5) + 16 : 0
  const headerHeight = Math.max(...headers.map((header, index) => conservativeTextHeight(header, widths[index], fontSize))) + 16
  const availableHeight = PAGE_HEIGHT - 70 - captionHeight - headerHeight - 28
  return availableHeight > 0 && block.rows.every((row) => row.every((cell, index) => (
    conservativeTextHeight(cell.text, widths[index], fontSize) + 16 <= availableHeight
  )))
}

function tableBlock(block: DashboardPdfTableBlock, sectionTitle: string): Content {
  const columnCount = Math.max(block.headers.length, ...block.rows.map((row) => row.length), 1)
  const headers = Array.from({ length: columnCount }, (_, index) => block.headers[index] ?? '')
  const caption = [sectionTitle, block.title].filter((title, index, titles) => title && titles.indexOf(title) === index).join(' · ')
  const body: TableCell[][] = []
  if (caption) {
    body.push([
      { text: caption, colSpan: columnCount, style: 'blockTitle', fillColor: '#FFFFFF', margin: [0, 1, 0, 5] },
      ...Array.from({ length: columnCount - 1 }, () => ({})),
    ])
  }
  body.push(headers.map((header) => ({
    text: header,
    bold: true,
    color: ACCENT,
    fillColor: '#EDF2F8',
    margin: [0, 3, 0, 3],
  })))
  block.rows.forEach((row, rowIndex) => {
    body.push(headers.map((_, columnIndex) => tableCell(row[columnIndex] ?? { text: '' }, rowIndex)))
  })
  if (block.rows.length === 0) {
    body.push([
      { text: '데이터가 없습니다.', colSpan: columnCount, color: MUTED, alignment: 'center', margin: [0, 12, 0, 12] },
      ...Array.from({ length: columnCount - 1 }, () => ({})),
    ])
  }
  const headerRows = caption ? 2 : 1
  const widths = tableWidths(block, headers)
  const fontSize = columnCount > 7 ? 8 : 8.7
  return {
    table: {
      headerRows,
      widths,
      body,
      dontBreakRows: canKeepRowsTogether(block, headers, widths, caption, fontSize),
    },
    fontSize,
    lineHeight: 1.25,
    layout: {
      hLineWidth: (index) => index < headerRows ? 0 : 0.5,
      vLineWidth: () => 0,
      hLineColor: () => BORDER,
      paddingLeft: () => 7,
      paddingRight: () => 7,
      paddingTop: () => 5,
      paddingBottom: () => 5,
    },
    margin: [0, 0, 0, 13],
  }
}

function sectionContent(section: DashboardPdfSection): Content[] {
  const content: Content[] = []
  const onlyTable = section.blocks.length === 1 && section.blocks[0].kind === 'table'
  if (section.title && !onlyTable) {
    content.push({
      text: section.title,
      style: 'sectionTitle',
      headlineLevel: 1,
      margin: [0, 9, 0, 9],
    })
  }
  let charts: DashboardPdfChartBlock[] = []
  const flushCharts = () => {
    if (charts.length) content.push(...chartRows(charts))
    charts = []
  }
  for (const block of section.blocks) {
    if (block.kind === 'chart') {
      charts.push(block)
      continue
    }
    flushCharts()
    if (block.kind === 'metrics') content.push(...metricRows(block))
    else if (block.kind === 'text') content.push(...textBlock({ ...block, title: block.title === section.title ? undefined : block.title }))
    else content.push(tableBlock(block, section.title))
  }
  flushCharts()
  if (section.title && !onlyTable && content.length > 1 && ['metrics', 'chart'].includes(section.blocks[0]?.kind)) {
    const firstRow = content.splice(0, 2)
    content.unshift({ stack: firstRow, unbreakable: true })
  }
  return content
}

export function buildDashboardPdfDefinition(document: DashboardPdfDocument): TDocumentDefinitions {
  const introduction: ContentStack = {
    stack: [
      { text: document.title, fontSize: 22, bold: true, color: INK, margin: [0, 0, 0, 7] },
      { text: document.period, fontSize: 10, color: MUTED, margin: [0, 0, 0, 5] },
      ...(document.filters.length ? [{ text: document.filters.join('   ·   '), fontSize: 9, color: ACCENT, margin: [0, 0, 0, 5] } as Content] : []),
      { text: `내보낸 시각 ${document.generatedAt}`, fontSize: 8, color: MUTED, margin: [0, 0, 0, 12] },
      { canvas: [{ type: 'line', x1: 0, y1: 0, x2: CONTENT_WIDTH, y2: 0, lineWidth: 1.2, lineColor: BORDER }] },
    ],
    margin: [0, 0, 0, 8],
  }
  return {
    pageSize: 'A4',
    pageOrientation: 'landscape',
    pageMargins: [PAGE_MARGIN, 35, PAGE_MARGIN, 35],
    info: { title: document.title, subject: document.period, creator: 'Auto Reports' },
    defaultStyle: { font: 'NanumGothic', fontSize: 9.5, color: INK, lineHeight: 1.2 },
    styles: {
      sectionTitle: { fontSize: 13, bold: true, color: INK },
      blockTitle: { fontSize: 10.5, bold: true, color: INK },
    },
    header: (currentPage) => currentPage === 1 ? null : {
      columns: [
        { text: document.title, bold: true, color: ACCENT },
        { text: document.period, alignment: 'right', color: MUTED },
      ],
      fontSize: 8,
      margin: [PAGE_MARGIN, 15, PAGE_MARGIN, 0],
    },
    footer: (currentPage, pageCount) => ({
      columns: [
        { text: 'Auto Reports', color: MUTED },
        { text: `${currentPage} / ${pageCount}`, alignment: 'right', color: MUTED },
      ],
      fontSize: 8,
      margin: [PAGE_MARGIN, 12, PAGE_MARGIN, 0],
    }),
    content: [introduction, ...document.sections.flatMap(sectionContent)],
    pageBreakBefore: (currentNode, nodeQueries) => Boolean(currentNode.headlineLevel && nodeQueries.getFollowingNodesOnPage().length === 0),
  }
}
