// frontend/src/infrastructure/export/dashboardExcelWorkbook.ts
import { utils, type CellObject, type WorkBook, type WorkSheet } from 'xlsx'
import type { DashboardExportTableData, DashboardPdfDocument } from '@/domain/DashboardExport'

type Value = string | number | null

function numericValue(value: string): Value {
  const trimmed = value.trim()
  if (!/^-?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$/.test(trimmed)) return value
  if (/^-?0\d/.test(trimmed)) return value
  const number = Number(trimmed.replace(/,/g, ''))
  return Number.isFinite(number) && Math.abs(number) < 1e15 ? number : value
}

function sheetName(title: string, used: Set<string>): string {
  const base = title.replace(/[\\/?:*\[\]'\u0000-\u001f]/g, ' ').trim() || '데이터'
  let suffix = ''
  let index = 1
  let name = base.slice(0, 31)
  while (used.has(name.toLocaleLowerCase())) {
    suffix = ` (${++index})`
    name = `${base.slice(0, 31 - suffix.length)}${suffix}`
  }
  used.add(name.toLocaleLowerCase())
  return name
}

function worksheet(rows: Value[][], filter = true): WorkSheet {
  const sheet = utils.aoa_to_sheet(rows)
  const widths: number[] = []
  for (const row of rows) {
    row.forEach((value, index) => {
      const width = String(value ?? '').split('\n').reduce((maximum, line) => Math.max(maximum,
        Array.from(line).reduce((sum, character) => sum + (character.charCodeAt(0) > 255 ? 2 : 1), 0)), 0)
      widths[index] = Math.min(60, Math.max(widths[index] ?? 14, width))
    })
  }
  sheet['!cols'] = widths.map((wch) => ({ wch }))
  if (filter && sheet['!ref'] && rows.length > 1) sheet['!autofilter'] = { ref: sheet['!ref'] }
  return sheet
}

export function buildDashboardExcelWorkbook(document: DashboardPdfDocument): WorkBook {
  const workbook = utils.book_new()
  const used = new Set<string>()
  const metadata: Value[][] = [
    ['항목', '내용'], ['보고서', document.title], ['기간', document.period], ['내보낸 시각', document.generatedAt],
    ...document.filters.map((filter) => ['적용 필터', filter]),
    [], ['시트', '대시보드 구역', '설명'],
  ]
  const metadataName = sheetName('내보내기 정보', used)
  utils.book_append_sheet(workbook, worksheet(metadata, false), metadataName)

  const append = (title: string, section: string, data: DashboardExportTableData, description = '') => {
    const name = sheetName(title || section, used)
    const rows: Value[][] = [data.headers.length ? data.headers : ['내용'], ...data.rows]
    const sheet = worksheet(rows)
    utils.book_append_sheet(workbook, sheet, name)
    metadata.push([name, section, description || (data.rows.length ? title : `${title} · 데이터가 없습니다.`)])
    return sheet
  }

  for (const section of document.sections) {
    for (const block of section.blocks) {
      if (block.kind === 'metrics') {
        append(section.title, section.title, { headers: ['지표', '값'], rows: block.items.map((item) => [item.label, numericValue(item.value)]) })
      } else if (block.kind === 'table') {
        const emptyMessage = block.rows.length === 1 && block.rows[0].length === 1 && /^(?:최근 이슈 )?데이터가 없습니다\.?$/.test(block.rows[0][0].text)
        const rows = emptyMessage ? [] : block.rows
        const sheet = append(block.title || section.title, section.title, {
          headers: block.headers,
          rows: rows.map((row) => row.map((cell) => cell.text)),
        })
        rows.forEach((row, rowIndex) => row.forEach((cell, columnIndex) => {
          if (!cell.link || !/^https?:\/\//i.test(cell.link)) return
          const address = utils.encode_cell({ r: rowIndex + 1, c: columnIndex })
          const target = sheet[address] as CellObject | undefined
          if (target) target.l = { Target: cell.link }
        }))
      } else if (block.data) {
        append(block.title || section.title, section.title, block.data, block.kind === 'chart' ? block.subtitle : block.paragraphs.join('\n'))
      } else if (block.kind === 'text') {
        append(block.title || section.title, section.title, { headers: ['내용'], rows: block.paragraphs.map((paragraph) => [paragraph]) })
      } else {
        append(block.title, section.title, { headers: ['내용'], rows: [[block.subtitle || '차트 수치 데이터가 없습니다.']] })
      }
    }
  }
  workbook.Sheets[metadataName] = worksheet(metadata, false)
  workbook.Props = { Title: document.title, Subject: document.period, Author: 'Auto Reports' }
  return workbook
}
