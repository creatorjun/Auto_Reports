// frontend/src/presentation/components/charts/ResolutionTimeChart.tsx
import { useState, useRef, useCallback, useMemo } from 'react'
import { useConfig } from '@/infrastructure/hooks/useConfig'
import { STATUS_STYLE, STATUS_LEGEND, STAGE_TOTAL } from '@/shared/ui'
import { TABLE_PAGE_SIZE, TABLE_MIN_COL_FRAC, DEFAULT_JIRA_BASE_URL } from '@/shared/constants'
import type { RecentIssue } from '@/presentation/pages/DashboardPage'

const COLS = ['key', 'summary', 'status', 'reporter', 'tac', 'elapsed'] as const
type ColKey = typeof COLS[number]
type SortDir = 'asc' | 'desc'

const DEFAULT_FRACS: Record<ColKey, number> = {
  key:      0.10,
  summary:  0.40,
  status:   0.15,
  reporter: 0.15,
  tac:      0.10,
  elapsed:  0.10,
}

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

function SortIcon({ dir }: { dir: SortDir | null }) {
  if (!dir) return <span className="ml-1 opacity-30 text-[10px]">⇅</span>
  return <span className="ml-1 text-brand-500 text-[10px]">{dir === 'asc' ? '↑' : '↓'}</span>
}

function ResizeHandle({
  onDrag,
  tableWidth,
}: {
  onDrag: (frac: number) => void
  tableWidth: React.RefObject<number>
}) {
  const dragging = useRef(false)
  const lastX    = useRef(0)

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault()
    e.stopPropagation()
    dragging.current = true
    lastX.current    = e.clientX
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  }, [])

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragging.current) return
    const dx = e.clientX - lastX.current
    lastX.current = e.clientX
    const tw = tableWidth.current || 1
    onDrag(dx / tw)
  }, [onDrag, tableWidth])

  const onPointerUp = useCallback(() => { dragging.current = false }, [])

  return (
    <span
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      className="absolute right-0 top-0 h-full w-[6px] cursor-col-resize select-none
                 flex items-center justify-center group z-10"
      title="드래그하여 너비 조절"
    >
      <span className="w-[2px] h-4 rounded bg-apple-divider group-hover:bg-brand-500 transition-colors" />
    </span>
  )
}

function sortIssues(items: RecentIssue[], key: ColKey, dir: SortDir): RecentIssue[] {
  return [...items].sort((a, b) => {
    let av: string | number = ''
    let bv: string | number = ''
    switch (key) {
      case 'key':      av = a.key;          bv = b.key;          break
      case 'summary':  av = a.summary;      bv = b.summary;      break
      case 'status':   av = a.stage_index;  bv = b.stage_index;  break
      case 'reporter': av = a.reporter;     bv = b.reporter;     break
      case 'tac':      av = a.tac_team;     bv = b.tac_team;     break
      case 'elapsed':  av = a.elapsed_days; bv = b.elapsed_days; break
    }
    if (av < bv) return dir === 'asc' ? -1 : 1
    if (av > bv) return dir === 'asc' ?  1 : -1
    return 0
  })
}

export default function ResolutionTimeChart({ details }: Props) {
  const { data: config } = useConfig()
  const jiraBaseUrl = config?.jira_base_url ?? DEFAULT_JIRA_BASE_URL
  const [page, setPage]       = useState(1)
  const [fracs, setFracs]     = useState({ ...DEFAULT_FRACS })
  const [sortKey, setSortKey] = useState<ColKey | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const tableRef              = useRef<HTMLTableElement>(null)
  const tableWidthRef         = useRef<number>(0)

  const handleSort = useCallback((col: ColKey) => {
    setSortKey((prev) => {
      if (prev === col) {
        setSortDir((d) => d === 'asc' ? 'desc' : 'asc')
        return col
      }
      setSortDir('asc')
      return col
    })
    setPage(1)
  }, [])

  const resize = useCallback((leftCol: ColKey, rightCol: ColKey, df: number) => {
    setFracs((prev) => {
      const newLeft  = Math.max(TABLE_MIN_COL_FRAC, prev[leftCol]  + df)
      const newRight = Math.max(TABLE_MIN_COL_FRAC, prev[rightCol] - df)
      if (newLeft + newRight !== prev[leftCol] + prev[rightCol]) return prev
      return { ...prev, [leftCol]: newLeft, [rightCol]: newRight }
    })
  }, [])

  const getTableWidth = useCallback(() => {
    tableWidthRef.current = tableRef.current?.offsetWidth ?? tableWidthRef.current
    return tableWidthRef
  }, [])

  const sortedDetails = useMemo(
    () => sortKey ? sortIssues(details, sortKey, sortDir) : details,
    [details, sortKey, sortDir],
  )

  if (!details || details.length === 0) {
    return (
      <div className="card flex items-center justify-center h-48 text-apple-light text-ui-base">
        최근 이슈 데이터가 없습니다.
      </div>
    )
  }

  const totalPages = Math.ceil(sortedDetails.length / TABLE_PAGE_SIZE)
  const pageItems  = sortedDetails.slice((page - 1) * TABLE_PAGE_SIZE, page * TABLE_PAGE_SIZE)

  const headers: { key: ColKey; label: string; rightCol?: ColKey; alignRight?: boolean }[] = [
    { key: 'key',      label: '이슈',          rightCol: 'summary'  },
    { key: 'summary',  label: '제목',          rightCol: 'status'   },
    { key: 'status',   label: '진행 상태',     rightCol: 'reporter' },
    { key: 'reporter', label: '보고자',        rightCol: 'tac'      },
    { key: 'tac',      label: '담당자',        rightCol: 'elapsed'  },
    { key: 'elapsed',  label: '생성일 (경과)', alignRight: true },
  ]

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
        <table
          ref={tableRef}
          className="w-full text-ui-base border-collapse"
          style={{ tableLayout: 'fixed' }}
        >
          <colgroup>
            {COLS.map((col) => (
              <col key={col} style={{ width: `${(fracs[col] * 100).toFixed(2)}%` }} />
            ))}
          </colgroup>
          <thead>
            <tr className="border-b border-apple-divider text-ui-sm text-apple-light">
              {headers.map(({ key, label, rightCol, alignRight }) => (
                <th
                  key={key}
                  onClick={() => handleSort(key)}
                  className={[
                    'pb-1.5 font-medium whitespace-nowrap relative pr-5 select-none cursor-pointer',
                    'hover:text-apple-primary transition-colors',
                    alignRight ? 'text-right' : 'text-left',
                    sortKey === key ? 'text-apple-primary' : '',
                  ].join(' ')}
                >
                  {label}
                  <SortIcon dir={sortKey === key ? sortDir : null} />
                  {rightCol && (
                    <ResizeHandle
                      tableWidth={getTableWidth()}
                      onDrag={(df) => resize(key, rightCol, df)}
                    />
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageItems.map((issue) => {
              const style   = getStatusStyle(issue.status)
              const jiraUrl = `${jiraBaseUrl}/browse/${issue.key}`
              const createdDate = issue.created ? issue.created.slice(0, 10) : '-'
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
                    <span className="tabular-nums">{createdDate}</span>
                    <span className="text-ui-xs text-apple-divider mx-1">·</span>
                    <span className="tabular-nums">{issue.elapsed_days}일</span>
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
            {(page - 1) * TABLE_PAGE_SIZE + 1}–{Math.min(page * TABLE_PAGE_SIZE, sortedDetails.length)} / {sortedDetails.length}건
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
