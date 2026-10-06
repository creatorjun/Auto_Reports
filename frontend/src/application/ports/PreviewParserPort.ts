// frontend/src/application/ports/PreviewParserPort.ts
export interface WorkbookPreviewSheet {
  name: string
  html: string
}

export interface PreviewParserPort {
  decodeText: (buffer: ArrayBuffer) => string
  parseCsv: (buffer: ArrayBuffer) => string[][]
  parseWorkbook: (buffer: ArrayBuffer) => Promise<WorkbookPreviewSheet[]>
  parseDocument: (buffer: ArrayBuffer) => Promise<string>
}
