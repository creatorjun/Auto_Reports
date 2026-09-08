// frontend/src/infrastructure/export/dashboardPdfExporter.ts
import type { DashboardExportGateway } from '@/application/ports/ApplicationServices'
import { createBinaryContent } from '@/infrastructure/api/binaryContent'

export const dashboardPdfExporter: DashboardExportGateway = {
  async renderPdf(document) {
    const [{ default: pdfMake }, { buildDashboardPdfDefinition }, regular, bold] = await Promise.all([
      import('pdfmake/build/pdfmake'),
      import('./dashboardPdfDefinition'),
      import('@/assets/fonts/NanumGothic-Regular.ttf?url'),
      import('@/assets/fonts/NanumGothic-Bold.ttf?url'),
    ])
    const regularUrl = new URL(regular.default, window.location.href).href
    const boldUrl = new URL(bold.default, window.location.href).href
    pdfMake.addFonts({
      NanumGothic: {
        normal: regularUrl,
        bold: boldUrl,
        italics: regularUrl,
        bolditalics: boldUrl,
      },
    })
    const blob = await pdfMake.createPdf(buildDashboardPdfDefinition(document)).getBlob()
    return createBinaryContent(blob)
  },
}
