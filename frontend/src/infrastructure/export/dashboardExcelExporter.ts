// frontend/src/infrastructure/export/dashboardExcelExporter.ts
import type { DashboardExportGateway } from '@/application/ports/ApplicationServices'
import { createBinaryContent } from '@/infrastructure/api/binaryContent'

export const dashboardExcelExporter: Pick<DashboardExportGateway, 'renderExcel'> = {
  async renderExcel(document) {
    const [{ write }, { buildDashboardExcelWorkbook }] = await Promise.all([
      import('xlsx'),
      import('./dashboardExcelWorkbook'),
    ])
    const data = write(buildDashboardExcelWorkbook(document), { type: 'array', bookType: 'xlsx', compression: true })
    return createBinaryContent(new Blob([data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }))
  },
}
