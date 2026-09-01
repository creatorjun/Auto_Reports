// frontend/src/infrastructure/api/reportApi.ts
import client, { getAccessToken } from './client'
import type {
  JobStreamCallbacks,
  JobStreamSubscription,
  ReportGateway,
} from '@/application/ports/ApplicationServices'
import type { ReportDetail, ReportSummary } from '@/domain/Report'
import type { TriggerAccepted, JobStatus, TriggerParams } from '@/domain/Job'
import type { AppConfig } from '@/domain/Config'

export type { TriggerAccepted, JobStatus, TriggerParams, AppConfig }

const BACKOFF_BASE_MS = 1_000
const BACKOFF_MAX_MS = 16_000
const BACKOFF_JITTER = 0.2
const JOB_TIMEOUT_MS = 300_000

function nextDelay(attempt: number): number {
  const base = Math.min(BACKOFF_BASE_MS * 2 ** attempt, BACKOFF_MAX_MS)
  const jitter = base * BACKOFF_JITTER * (Math.random() * 2 - 1)
  return Math.round(base + jitter)
}

async function getJobStatus(jobId: string): Promise<JobStatus> {
  const response = await client.get<JobStatus>(`/trigger/${jobId}/status`)
  return response.data
}

function getJobStreamUrl(jobId: string): string {
  const path = `/api/v1/trigger/${jobId}/stream`
  const token = getAccessToken()
  return token ? `${path}?token=${encodeURIComponent(token)}` : path
}

function watchJob(
  jobId: string,
  callbacks: JobStreamCallbacks,
  timeoutMs = JOB_TIMEOUT_MS,
): JobStreamSubscription {
  let source: EventSource | null = null
  let timer: ReturnType<typeof setTimeout> | null = null
  let deadlineTimer: ReturnType<typeof setTimeout> | null = null
  let attempt = 0
  let elapsed = 0
  let active = true

  const close = () => {
    active = false
    source?.close()
    source = null
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
    if (deadlineTimer !== null) {
      clearTimeout(deadlineTimer)
      deadlineTimer = null
    }
  }

  const startPolling = () => {
    const tick = async () => {
      if (!active) return
      if (elapsed >= timeoutMs) {
        close()
        callbacks.onTimeout()
        return
      }
      try {
        const status = await getJobStatus(jobId)
        callbacks.onStatus?.(status)
        if (status.status === 'done') {
          close()
          callbacks.onComplete(status.report_id)
          return
        }
        if (status.status === 'error') {
          close()
          callbacks.onError(status.error ?? '알 수 없는 오류')
          return
        }
        const serverHint = (status as JobStatus & { retry_after?: number }).retry_after
        const delay = serverHint ? serverHint * 1000 : nextDelay(attempt)
        attempt += 1
        elapsed += delay
        timer = setTimeout(tick, delay)
      } catch (error) {
        close()
        if (callbacks.onTransportError) {
          callbacks.onTransportError(error)
        } else {
          callbacks.onError('상태 확인 중 오류가 발생했습니다.')
        }
      }
    }
    void tick()
  }

  const startStream = () => {
    if (typeof EventSource === 'undefined') {
      startPolling()
      return
    }
    const eventSource = new EventSource(getJobStreamUrl(jobId))
    source = eventSource
    eventSource.addEventListener('status', (event: MessageEvent) => {
      if (!active) return
      try {
        callbacks.onStatus?.(JSON.parse(event.data) as JobStatus)
      } catch {
      }
    })
    eventSource.addEventListener('done', (event: MessageEvent) => {
      if (!active) return
      try {
        const status = JSON.parse(event.data) as JobStatus
        close()
        if (status.status === 'error') {
          callbacks.onError(status.error ?? '알 수 없는 오류')
        } else {
          callbacks.onComplete(status.report_id)
        }
      } catch {
        close()
        callbacks.onError('스트림 데이터 파싱 오류')
      }
    })
    eventSource.addEventListener('timeout', () => {
      if (!active) return
      close()
      callbacks.onTimeout()
    })
    eventSource.addEventListener('error', () => {
      if (!active) return
      eventSource.close()
      source = null
      startPolling()
    })
  }

  startStream()
  deadlineTimer = setTimeout(() => {
    if (!active) return
    close()
    callbacks.onTimeout()
  }, timeoutMs)
  return { close }
}

export const reportApi: ReportGateway = {
  getLatest: async (): Promise<ReportDetail | null> => {
    const res = await client.get<ReportDetail>('/reports/latest')
    return res.data
  },
  getAnnual: async (year: number): Promise<ReportDetail> => {
    const res = await client.get<ReportDetail>(`/reports/annual/${year}`)
    return res.data
  },
  getById: async (id: number): Promise<ReportDetail> => {
    const res = await client.get<ReportDetail>(`/reports/${id}`)
    return res.data
  },
  getAll: async (limit = 20, offset = 0): Promise<ReportSummary[]> => {
    const res = await client.get<ReportSummary[]>('/reports/', { params: { limit, offset } })
    return res.data
  },
  trigger: async (params?: TriggerParams): Promise<TriggerAccepted> => {
    const res = await client.post<TriggerAccepted>('/trigger/', params ?? {})
    return res.data
  },
  watchJob,
  delete: async (id: number): Promise<void> => {
    await client.delete(`/reports/${id}`)
  },
  getConfig: async (): Promise<AppConfig> => {
    const res = await client.get<AppConfig>('/config')
    return res.data
  },
}
