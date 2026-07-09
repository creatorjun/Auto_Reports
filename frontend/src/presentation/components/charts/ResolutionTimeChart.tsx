// frontend/src/presentation/components/charts/ResolutionTimeChart.tsx
import { useState, useRef, useCallback } from 'react'
import { useConfig } from '@/infrastructure/hooks/useConfig'
import { STATUS_STYLE, STATUS_LEGEND, STAGE_TOTAL } from '@/shared/ui'
import type { RecentIssue } from '@/presentation/pages/DashboardPage'

const PAGE_SIZE = 50

const COL_DEFAULTS = { key: 100, summary: 360, status: 220, reporter: 100, tac: 100, elapsed: 60 }
const COL_MIN      = { key:  60, summary: 120, status: 160, reporter:  70, tac:  70, elapsed: 50 }

type ColKey = keyof typeof COL_DEFAULTS

interface Props {
  details: RecentIssue[]
}

function getStatusStyle(status: string) {
  return STATUS_STYLE[status] ?? { bg: 'bg-status-todo', text: 'text-white' }
}

function StageBar({ stageIndex }: { stageIndex: number }) {
  return (
    <div className="flex gap-[2px] items-center">
      {Array.from({ length: STAGE_TOTAL }).map((_, i) => (
        <div
          key={i}
          className={`h-[10px] w-[10px] rounded-[2px] ${
            i <= stageIndex ? 'bg-amber-400' : 'bg-gray-200'
          }`}
        />
      ))}
    </div>
  )
}

function ResizeHandle({ onDrag }: { onDrag: (dx: number) => void }) {
  const dragging = useRef(false)
  const lastX    = useRef(0)

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault()
    dragging.current = true
    lastX.current    = e.clientX
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  }, [])

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragging.current) return
    const dx = e.clientX - lastX.current
    lastX.current = e.clientX
    onDrag(dx)
  }, [onDrag])

  const onPointerUp = useCallback(() => { dragging.current = false }, [])

  return (
    <span
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      className="absolute right-0 top-0 h-full w-[5px] cursor-col-resize select-none
                 flex items-center justify-center group"
      title="드래그하여 너비 조절"
    >
      <span className="w-[2px] h-4 rounded bg-apple-divider group-hover:bg-brand-500 transition-colors" />
    </span>
  )
}

export default function ResolutionTimeChart({ details }: Props) {
  const { data: config } = useConfig()
  const jiraBaseUrl = config?.jira_base_url ?? 'https://seculayer.atlassian.net'
  const [page, setPage]   = useState(1)
  const [widths, setWidths] = useState({ ...COL_DEFAULTS })

  const resize = useCallback((col: ColKey, dx: number) => {
    setWidths((prev) => ({
      ...prev,
      [col]: Math.max(COL_MIN[col], prev[col] + dx),
    }))
  }, [])

  if (!details || details.length === 0) {
    return (
      <div className="card flex items-center justify-center h-48 text-apple-light text-ui-base">
        최근 이슈 데이터가 없습니다.
      </div>
    )
  }

  const totalPages = Math.ceil(details.length / PAGE_SIZE)
  const pageItems  = details.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const thCls = "pb-1.5 text-left font-medium whitespace-nowrap relative pr-4 select-none"

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-ui-md font-semibold text-apple-primary">
          📌 최근 이슈 현황{' '}
          <span className="text-apple-light font-normal">(최신 {details.length}건)</span>
        </h3>
        <div className="flex flex-wrap gap-x-3 gap-y-1 justify-end">
          {STATUS_LEGEND.map((l) => (
            <span key={l.label} className="flex items-center gap-1 text-ui-sm text-apple-light">
              <span className={`inline-block w-2 h-2 rounded-full ${l.color}`} />
              {l.label}
            </span>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="text-ui-base border-collapse" style={{ tableLayout: 'fixed', width: Object.values(widths).reduce((a, b) => a + b, 0) }}>
          <colgroup>
            <col style={{ width: widths.key }} />
            <col style={{ width: widths.summary }} />
            <col style={{ width: widths.status }} />
            <col style={{ width: widths.reporter }} />
            <col style={{ width: widths.tac }} />
            <col style={{ width: widths.elapsed }} />
          </colgroup>
          <thead>
            <tr className="border-b border-apple-divider text-ui-sm text-apple-light">
              <th className={thCls}>
                이슈
                <ResizeHandle onDrag={(dx) => resize('key', dx)} />
              </th>
              <th className={thCls}>
                제목
                <ResizeHandle onDrag={(dx) => resize('summary', dx)} />
              </th>
              <th className={thCls}>
                진행 상태
                <ResizeHandle onDrag={(dx) => resize('status', dx)} />
              </th>
              <th className={thCls}>
                보고자
                <ResizeHandle onDrag={(dx) => resize('reporter', dx)} />
              </th>
              <th className={thCls}>
                담당자
                <ResizeHandle onDrag={(dx) => resize('tac', dx)} />
              </th>
              <th className="pb-1.5 text-right font-medium whitespace-nowrap">경과</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.map((issue) => {
              const style  = getStatusStyle(issue.status)
              const jiraUrl = `${jiraBaseUrl}/browse/${issue.key}`
              return (
                <tr
                  key={issue.key}
                  onClick={() => window.open(jiraUrl, '_blank', 'noreferrer')}
                  className="border-b border-apple-divider last:border-0 hover:bg-gray-50 transition-colors cursor-pointer"
                >
                  <td className="py-2 pr-3 overflow-hidden">
                    <span className="font-mono text-ui-sm text-blue-500 truncate block">{issue.key}</span>
                  </td>
                  <td className="py-2 pr-3 overflow-hidden">
                    <span className="text-apple-primary truncate block" title={issue.summary}>{issue.summary}</span>
                  </td>
                  <td className="py-2 pr-3 overflow-hidden">
                    <div className="flex items-center gap-2">
                      <StageBar stageIndex={issue.stage_index} />
                      <span className={`inline-block px-2 py-0.5 rounded-full text-ui-sm font-medium ${style.bg} ${style.text} whitespace-nowrap`}>
                        {issue.status}
                      </span>
                    </div>
                  </td>
                  <td className="py-2 pr-3 overflow-hidden">
                    <span className="text-ui-sm text-apple-light truncate block">{issue.reporter}</span>
                  </td>
                  <td className="py-2 pr-3 overflow-hidden">
                    <span className="text-ui-sm text-apple-light truncate block">{issue.tac_team}</span>
                  </td>
                  <td className="py-2 text-right text-apple-light whitespace-nowrap">
                    {issue.elapsed_days}일
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-apple-divider">
          <span className="text-ui-sm text-apple-light">
            {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, details.length)} / {details.length}건
          </span>
          <div className="flex gap-1">
            {Array.from({ length: totalPages }).map((_, i) => (
              <button
                key={i}
                onClick={(e) => { e.stopPropagation(); setPage(i + 1) }}
                className={`px-3 py-1 rounded text-ui-sm font-medium transition-colors ${
                  page === i + 1
                    ? 'bg-brand-500 text-white'
                    : 'bg-gray-100 text-apple-mid hover:bg-gray-200'
                }`}
              >
                {i + 1}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
