// frontend/src/presentation/hooks/useReportRefreshShortcut.ts
import { useCallback, useEffect } from 'react'
import { useReportGeneration } from '@/presentation/context/ReportGenerationContext'

export function useReportRefreshShortcut(enabled = true) {
  const { generate, pending } = useReportGeneration()
  const refresh = useCallback(() => {
    if (enabled && !pending) generate({ rerun_latest: true })
  }, [enabled, generate, pending])

  useEffect(() => {
    if (!enabled) return
    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        event.defaultPrevented || event.isComposing || event.shiftKey || event.altKey
        || event.ctrlKey === event.metaKey || event.key.toLowerCase() !== 'r'
      ) return
      event.preventDefault()
      if (!event.repeat) refresh()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [enabled, refresh])

  return refresh
}
