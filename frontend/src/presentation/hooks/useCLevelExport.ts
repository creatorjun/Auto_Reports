// frontend/src/presentation/hooks/useCLevelExport.ts
import { useEffect, useRef, useState } from 'react'
import type { DashboardPdfDocument } from '@/domain/DashboardExport'
import type { BinaryObjectUrl } from '@/application/ports/ApplicationServices'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'

export function useCLevelExport() {
  const { dashboardExport } = useApplicationServices()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const active = useRef(true)
  const busy = useRef(false)
  const urls = useRef<Set<BinaryObjectUrl>>(new Set())
  const timers = useRef<Set<ReturnType<typeof setTimeout>>>(new Set())
  useEffect(() => {
    active.current = true
    return () => {
      active.current = false
      for (const timer of timers.current) clearTimeout(timer)
      for (const url of urls.current) url.close()
      timers.current.clear()
      urls.current.clear()
    }
  }, [])
  const download = async (document: DashboardPdfDocument, format: 'pdf' | 'xlsx', fileName: string) => {
    if (busy.current) return
    busy.current = true
    setPending(true)
    setError('')
    try {
      const content = await (format === 'pdf' ? dashboardExport.renderPdf(document) : dashboardExport.renderExcel(document))
      if (!active.current) return
      const url = content.createObjectUrl()
      urls.current.add(url)
      const link = window.document.createElement('a')
      try {
        link.href = url.url
        link.download = `${fileName}.${format}`
        window.document.body.appendChild(link)
        link.click()
      } finally {
        link.remove()
        const timer = setTimeout(() => { url.close(); urls.current.delete(url); timers.current.delete(timer) }, 30_000)
        timers.current.add(timer)
      }
    } catch {
      if (active.current) setError('파일을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.')
    } finally {
      busy.current = false
      if (active.current) setPending(false)
    }
  }
  return { download, pending, error }
}
