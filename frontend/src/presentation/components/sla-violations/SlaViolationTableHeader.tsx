// frontend/src/presentation/components/sla-violations/SlaViolationTableHeader.tsx
import { useRef } from 'react'
import type { KeyboardEvent, PointerEvent, RefObject } from 'react'
import type { SlaViolationSort, SlaViolationSortKey } from '@/domain/SlaViolationSort'

export const SLA_TICKET_COLUMNS: { key: SlaViolationSortKey; label: string }[] = [
  { key: 'key', label: '번호' },
  { key: 'summary', label: '제목' },
  { key: 'issue_type', label: '유형' },
  { key: 'violation', label: '위반 항목' },
  { key: 'created_at', label: '생성일' },
  { key: 'elapsed_days', label: '경과일' },
]

export type SlaColumnWidths = Record<SlaViolationSortKey, number>

export const DEFAULT_SLA_COLUMN_WIDTHS: SlaColumnWidths = {
  key: 0.14, summary: 0.32, issue_type: 0.11, violation: 0.19, created_at: 0.14, elapsed_days: 0.10,
}

export const MIN_SLA_COLUMN_WIDTHS: SlaColumnWidths = {
  key: 0.08, summary: 0.18, issue_type: 0.08, violation: 0.10, created_at: 0.08, elapsed_days: 0.07,
}

export function resizeSlaColumnWidths(widths: SlaColumnWidths, left: SlaViolationSortKey, right: SlaViolationSortKey, delta: number): SlaColumnWidths {
  if (!Number.isFinite(delta)) return widths
  const total = widths[left] + widths[right]
  const nextLeft = Math.max(MIN_SLA_COLUMN_WIDTHS[left], Math.min(total - MIN_SLA_COLUMN_WIDTHS[right], widths[left] + delta))
  if (nextLeft === widths[left]) return widths
  return { ...widths, [left]: nextLeft, [right]: total - nextLeft }
}

interface ResizeHandleProps {
  label: string
  left: SlaViolationSortKey
  right: SlaViolationSortKey
  widths: SlaColumnWidths
  gridRef: RefObject<HTMLDivElement>
  onResize: (left: SlaViolationSortKey, right: SlaViolationSortKey, delta: number) => void
}

function ResizeHandle({ label, left, right, widths, gridRef, onResize }: ResizeHandleProps) {
  const drag = useRef<{ pointerId: number; lastX: number; trackWidth: number } | null>(null)
  const stopDrag = (event: PointerEvent<HTMLSpanElement>) => {
    if (drag.current?.pointerId !== event.pointerId) return
    drag.current = null
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const startDrag = (event: PointerEvent<HTMLSpanElement>) => {
    if (event.button !== 0 || !gridRef.current) return
    event.preventDefault()
    event.stopPropagation()
    const gridStyle = window.getComputedStyle(gridRef.current)
    const trackWidth = gridRef.current.getBoundingClientRect().width - parseFloat(gridStyle.paddingLeft) - parseFloat(gridStyle.paddingRight) - parseFloat(gridStyle.columnGap) * (SLA_TICKET_COLUMNS.length - 1)
    if (trackWidth <= 0) return
    drag.current = { pointerId: event.pointerId, lastX: event.clientX, trackWidth }
    event.currentTarget.focus()
    event.currentTarget.setPointerCapture(event.pointerId)
  }
  const moveDrag = (event: PointerEvent<HTMLSpanElement>) => {
    const current = drag.current
    if (!current || current.pointerId !== event.pointerId) return
    event.preventDefault()
    const delta = (event.clientX - current.lastX) / current.trackWidth
    current.lastX = event.clientX
    onResize(left, right, delta)
  }
  const resizeByKey = (event: KeyboardEvent<HTMLSpanElement>) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    event.preventDefault()
    event.stopPropagation()
    onResize(left, right, (event.key === 'ArrowLeft' ? -1 : 1) * (event.shiftKey ? 0.05 : 0.01))
  }
  return (
    <span role="separator" tabIndex={0} aria-orientation="vertical" aria-label={`${label} 열 너비 조절`}
      aria-valuenow={Math.round(widths[left] * 100)} aria-valuemin={Math.round(MIN_SLA_COLUMN_WIDTHS[left] * 100)}
      aria-valuemax={Math.round((widths[left] + widths[right] - MIN_SLA_COLUMN_WIDTHS[right]) * 100)}
      aria-valuetext={`${Math.round(widths[left] * 100)}%`}
      title="드래그하거나 좌우 방향키로 너비 조절"
      onPointerDown={startDrag} onPointerMove={moveDrag} onPointerUp={stopDrag} onPointerCancel={stopDrag}
      onLostPointerCapture={() => { drag.current = null }} onKeyDown={resizeByKey}
      onClick={(event) => { event.preventDefault(); event.stopPropagation() }}
      className="group absolute -right-3 top-0 z-10 flex h-full w-2 touch-none cursor-col-resize select-none items-center justify-center rounded focus-visible:outline-brand-400">
      <span aria-hidden="true" className="h-5 w-0.5 rounded bg-apple-mid/50 transition-colors group-hover:bg-brand-500 group-focus-visible:bg-brand-500" />
    </span>
  )
}

interface Props {
  label: string
  sort: SlaViolationSort | null
  widths: SlaColumnWidths
  onSort: (sort: SlaViolationSort | null) => void
  onResize: ResizeHandleProps['onResize']
}

export default function SlaViolationTableHeader({ label, sort, widths, onSort, onResize }: Props) {
  const gridRef = useRef<HTMLDivElement>(null)
  const toggleSort = (key: SlaViolationSortKey) => onSort({ key, direction: sort?.key === key && sort.direction === 'asc' ? 'desc' : 'asc' })
  return (
    <>
      <div className="flex flex-wrap items-center gap-2 border-t border-apple-divider/70 bg-apple-gray/70 px-4 py-3 lg:hidden">
        <label className="flex items-center gap-2 text-control-label font-medium text-apple-mid">정렬
          <select value={sort?.key ?? ''} aria-label={`${label} 정렬 기준`}
            onChange={(event) => onSort(event.target.value ? { key: event.target.value as SlaViolationSortKey, direction: 'asc' } : null)}
            className="min-h-9 rounded-lg border border-apple-divider bg-apple-surface px-2 text-control text-apple-dark focus-visible:outline-brand-400">
            <option value="">기본 순서</option>
            {SLA_TICKET_COLUMNS.map((column) => <option key={column.key} value={column.key}>{column.label}</option>)}
          </select>
        </label>
        <button type="button" disabled={!sort} onClick={() => { if (sort) toggleSort(sort.key) }}
          aria-label={`${label} ${sort?.direction === 'desc' ? '내림차순 정렬 중, 오름차순' : '오름차순 정렬 중, 내림차순'} 정렬`}
          className="min-h-9 rounded-lg border border-apple-divider bg-apple-surface px-3 text-control font-medium text-apple-mid hover:bg-apple-gray focus-visible:outline-brand-400 disabled:opacity-40">
          {sort?.direction === 'desc' ? '내림차순 ↓' : '오름차순 ↑'}
        </button>
      </div>
      <div className="hidden items-center gap-1 bg-apple-gray/70 px-5 py-2 text-label font-medium text-apple-mid lg:flex">
        <div ref={gridRef} className="grid min-w-0 flex-1 grid-cols-[var(--sla-ticket-columns)] gap-x-4 px-1">
          {SLA_TICKET_COLUMNS.map((column, index) => {
            const active = sort?.key === column.key
            const nextDirection = active && sort.direction === 'asc' ? '내림차순' : '오름차순'
            const currentDirection = active ? `${sort.direction === 'asc' ? '오름차순' : '내림차순'} 정렬 중, ` : ''
            const right = SLA_TICKET_COLUMNS[index + 1]
            return (
              <div key={column.key} className="relative min-w-0">
                <button type="button" onClick={() => toggleSort(column.key)} aria-pressed={active}
                  aria-label={`${column.label} ${currentDirection}${nextDirection} 정렬`}
                  className={`flex min-h-9 w-full min-w-0 items-center gap-1 rounded-lg text-left transition-colors hover:bg-apple-gray focus-visible:outline-brand-400 ${column.key === 'elapsed_days' ? 'justify-end' : ''} ${active ? 'text-brand-600' : ''}`}>
                  <span>{column.label}</span><span aria-hidden="true" className={`shrink-0 ${active ? 'text-brand-500' : 'opacity-40'}`}>{active ? sort.direction === 'asc' ? '↑' : '↓' : '⇅'}</span>
                </button>
                {right && <ResizeHandle label={column.label} left={column.key} right={right.key} widths={widths} gridRef={gridRef} onResize={onResize} />}
              </div>
            )
          })}
        </div>
        <span className="w-12 shrink-0 text-center">상세</span>
      </div>
    </>
  )
}
