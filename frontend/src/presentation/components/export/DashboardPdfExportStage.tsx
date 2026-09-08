// frontend/src/presentation/components/export/DashboardPdfExportStage.tsx
import { Component, useEffect, useRef, type ReactNode } from 'react'
import type { DashboardPdfDocument } from '@/domain/DashboardExport'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { DashboardExportProvider } from '@/presentation/context/DashboardExportContext'
import { captureDashboardPdf, waitForDashboardPdf } from '@/presentation/utils/dashboardPdfCapture'

interface Props {
  metadata: Omit<DashboardPdfDocument, 'sections'>
  fileName: string
  children: ReactNode
  onComplete: () => void
  onError: (message: string) => void
}

class ExportBoundary extends Component<{ children: ReactNode; onError: Props['onError'] }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch() {
    this.props.onError('차트를 준비하지 못했습니다. 잠시 후 다시 시도해 주세요.')
  }

  render() {
    return this.state.failed ? null : this.props.children
  }
}

function ExportStage({ metadata, fileName, children, onComplete, onError }: Props) {
  const root = useRef<HTMLDivElement>(null)
  const { dashboardExport } = useApplicationServices()

  useEffect(() => {
    let active = true
    const element = root.current
    if (!element) return
    element.inert = true

    const exportPdf = async () => {
      await waitForDashboardPdf(element, () => active)
      if (!active) return
      const document = captureDashboardPdf(element, metadata)
      const content = await dashboardExport.renderPdf(document)
      if (!active) return
      const objectUrl = content.createObjectUrl()
      const link = window.document.createElement('a')
      try {
        link.href = objectUrl.url
        link.download = fileName
        window.document.body.appendChild(link)
        link.click()
      } finally {
        link.remove()
        window.setTimeout(() => objectUrl.close(), 30_000)
      }
      onComplete()
    }

    void exportPdf().catch(() => {
      if (active) onError('PDF를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.')
    })
    return () => { active = false }
  }, [dashboardExport, fileName, metadata, onComplete, onError])

  return (
    <div ref={root} aria-hidden="true" className="dashboard-pdf-stage">
      <DashboardExportProvider>{children}</DashboardExportProvider>
    </div>
  )
}

export default function DashboardPdfExportStage(props: Props) {
  return <ExportBoundary onError={props.onError}><ExportStage {...props} /></ExportBoundary>
}
