// frontend/src/presentation/context/ReportGenerationContext.tsx
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import type { PeriodReportRequest } from '@/domain/ReportPeriod'
import type { TriggerParams } from '@/domain/Job'
import { QUERY_KEYS } from '@/presentation/config/queryKeys'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useTrigger } from '@/presentation/hooks/useTrigger'
import { useUiStore } from '@/presentation/state/uiStore'
import { useAuthStore } from '@/presentation/state/authStore'

interface ReportGenerationValue {
  generate: (request: TriggerParams) => void
  pending: boolean
  error: string | null
  lastRequest: PeriodReportRequest | null
}

const ReportGenerationContext = createContext<ReportGenerationValue | null>(null)

export function ReportGenerationProvider({ children }: { children: ReactNode }) {
  const { reports } = useApplicationServices()
  const client = useQueryClient()
  const navigate = useNavigate()
  const location = useLocation()
  const pathRef = useRef(location.pathname)
  pathRef.current = location.pathname
  const activeRef = useRef(false)
  const mountedRef = useRef(true)
  const { isTriggerLoading, setTriggerLoading, setTriggerMessage } = useUiStore()
  const [error, setError] = useState<string | null>(null)
  const [lastRequest, setLastRequest] = useState<PeriodReportRequest | null>(null)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      setTriggerLoading(false)
    }
  }, [setTriggerLoading])

  const finish = () => {
    activeRef.current = false
    setTriggerLoading(false)
  }
  const fail = (message: string) => {
    finish()
    setError(message)
    setTriggerMessage(message)
  }
  const completed = async (reportId: number | null) => {
    const sessionVersion = useAuthStore.getState().sessionVersion
    const current = () => mountedRef.current && sessionVersion === useAuthStore.getState().sessionVersion
    if (reportId === null) {
      fail('생성된 보고서 번호를 확인하지 못했습니다. 히스토리에서 확인해 주세요.')
      return
    }
    try {
      const report = await reports.getById(reportId)
      if (!current()) return
      client.setQueryData(QUERY_KEYS.reportById(reportId), report)
      if (report.scope === 'annual' && report.report_year !== null) {
        await client.cancelQueries({ queryKey: QUERY_KEYS.annualReport(report.report_year) })
        if (!current()) return
        client.setQueryData(QUERY_KEYS.annualReport(report.report_year), report)
      } else {
        await client.cancelQueries({ queryKey: QUERY_KEYS.latestReport() })
        if (!current()) return
        client.setQueryData(QUERY_KEYS.latestReport(), report)
      }
      finish()
      if (report.scope === 'standard' && (pathRef.current === '/' || /^\/reports\/\d+$/.test(pathRef.current))) navigate(`/reports/${reportId}`)
    } catch {
      if (current()) fail('보고서는 생성되었지만 화면을 불러오지 못했습니다. 히스토리에서 확인해 주세요.')
    }
  }
  const { mutate } = useTrigger({
    onComplete: (reportId) => { void completed(reportId) },
    onError: (message) => fail(`보고서 생성 실패: ${message}`),
    onTimeout: () => fail('보고서 생성 상태 확인이 시간 초과되었습니다. 히스토리에서 완료 여부를 확인해 주세요.'),
  })

  const generate = (request: TriggerParams) => {
    if (activeRef.current) return
    activeRef.current = true
    setError(null)
    if ('period' in request) setLastRequest(request)
    setTriggerLoading(true)
    setTriggerMessage(null)
    mutate(request)
  }

  return <ReportGenerationContext.Provider value={{ generate, pending: isTriggerLoading, error, lastRequest }}>{children}</ReportGenerationContext.Provider>
}

export function useReportGeneration(): ReportGenerationValue {
  const context = useContext(ReportGenerationContext)
  if (context === null) throw new Error('Report generation is not configured')
  return context
}
