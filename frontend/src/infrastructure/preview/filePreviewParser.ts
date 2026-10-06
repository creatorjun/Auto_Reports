// frontend/src/infrastructure/preview/filePreviewParser.ts
import type { PreviewParserPort, WorkbookPreviewSheet } from '@/application/ports/PreviewParserPort'

function decodeText(buffer: ArrayBuffer): string {
  const decode = (encoding: string) => new TextDecoder(encoding, { fatal: true }).decode(buffer)
  try { return decode('utf-8') }
  catch {
    try { return decode('euc-kr') }
    catch { return new TextDecoder('utf-8').decode(buffer) }
  }
}

function parseCsv(buffer: ArrayBuffer): string[][] {
  return decodeText(buffer).trim().split('\n').map(line => line.split(','))
}

async function parseWorkbook(buffer: ArrayBuffer): Promise<WorkbookPreviewSheet[]> {
  const XLSX = await import('xlsx')
  const workbook = XLSX.read(buffer, { type: 'array', codepage: 949, cellStyles: true })
  if (workbook.SheetNames.length === 0) throw new Error('표시할 시트가 없습니다.')
  return workbook.SheetNames.map(name => ({
    name,
    html: XLSX.utils.sheet_to_html(workbook.Sheets[name], { header: '', footer: '' }),
  }))
}

async function parseDocument(buffer: ArrayBuffer): Promise<string> {
  const mammoth = await import('mammoth')
  return (await mammoth.convertToHtml({ arrayBuffer: buffer })).value
}

export const filePreviewParser: PreviewParserPort = {
  decodeText,
  parseCsv,
  parseWorkbook,
  parseDocument,
}
