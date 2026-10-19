// frontend/src/presentation/components/common/IssueTableModal.tsx
import { Fragment, useMemo, useState } from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import { useJira } from '@/presentation/context/JiraContext'
import { MODAL_CLS } from '@/presentation/config/ui'
import { TABLE_PAGE_SIZE } from '@/presentation/config/constants'
import IssueModalShell from '@/presentation/components/common/IssueModalShell'
import type { ModalSize } from '@/presentation/config/ui'
import type { KeyboardEvent, ReactNode } from 'react'
import { sortIssueTableRows, type IssueTableSort, type SortableIssueColumn } from '@/presentation/utils/issueTableSorting'

export interface ColumnDef<T> extends SortableIssueColumn<T> {
  width?: 'wide' | 'date'
  renderCell: (row: T) => ReactNode
  mobile: {
    slot: 'primary' | 'secondary' | 'summary' | 'detail' | 'hidden'
    render?: (row: T) => ReactNode
  }
}

interface Props<T extends { key: string }> {
  title: string
  subtitle: string
  size?: ModalSize
  data: T[]
  columns: ColumnDef<T>[]
  paginate?: boolean
  headerSlot?: ReactNode
  sort?: IssueTableSort | null
  onSortChange?: (sort: IssueTableSort | null) => void
  onClose: () => void
}

export default function IssueTableModal<T extends { key: string }>({
  title,
  subtitle,
  size = 'lg',
  data,
  columns,
  paginate = false,
  headerSlot,
  sort: controlledSort,
  onSortChange,
  onClose,
}: Props<T>) {
  const { jiraBrowse } = useJira()
  const [page, setPage] = useState(1)
  const [localSort, setLocalSort] = useState<IssueTableSort | null>(null)
  const sort = onSortChange ? controlledSort ?? null : localSort
  const sortedData = useMemo(
    () => onSortChange ? data : sortIssueTableRows(data, columns, sort),
    [data, columns, sort, onSortChange],
  )

  const totalPages = paginate ? Math.max(1, Math.ceil(data.length / TABLE_PAGE_SIZE)) : 1
  const currentPage = Math.min(page, totalPages)
  const rows = paginate
    ? sortedData.slice((currentPage - 1) * TABLE_PAGE_SIZE, currentPage * TABLE_PAGE_SIZE)
    : sortedData
  const minTableWidth = columns.reduce((width, column) => width + (column.width === 'wide' ? 320 : 192), 0)

  const changeSort = (next: IssueTableSort | null) => {
    if (onSortChange) onSortChange(next)
    else setLocalSort(next)
    setPage(1)
  }

  const toggleSort = (column: string) => {
    changeSort({ column, direction: sort?.column === column && sort.direction === 'asc' ? 'desc' : 'asc' })
  }

  const openIssue = (key: string) => {
    window.open(`${jiraBrowse}/${key}`, '_blank', 'noopener,noreferrer')
  }

  const handleIssueKeyDown = (event: KeyboardEvent, key: string) => {
    if (event.key !== 'Enter' && event.key !== ' ') return
    event.preventDefault()
    openIssue(key)
  }

  const primaryColumns = columns.filter(column => column.mobile.slot === 'primary')
  const secondaryColumns = columns.filter(column => column.mobile.slot === 'secondary')
  const summaryColumns = columns.filter(column => column.mobile.slot === 'summary')
  const detailColumns = columns.filter(column => column.mobile.slot === 'detail')

  const renderMobileColumn = (column: ColumnDef<T>, row: T) => (
    column.mobile.render ? column.mobile.render(row) : column.renderCell(row)
  )

  return (
    <IssueModalShell title={title} subtitle={subtitle} size={size} onClose={onClose}>
      {headerSlot && <div className="mb-4">{headerSlot}</div>}

      <div className="mb-4 flex flex-wrap items-center gap-2 xl:hidden">
        <label className="flex min-w-0 flex-1 items-center gap-2 text-label text-apple-mid">
          <span className="shrink-0">정렬</span>
          <select
            aria-label="이슈 정렬 기준"
            value={sort?.column ?? ''}
            onChange={(event) => changeSort(event.target.value ? { column: event.target.value, direction: 'asc' } : null)}
            className="min-w-0 flex-1 rounded-lg border border-apple-divider bg-apple-surface px-3 py-2 text-control text-apple-dark outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">기본 순서</option>
            {columns.map((column) => <option key={column.header} value={column.header}>{column.header}</option>)}
          </select>
        </label>
        {sort && (
          <button
            type="button"
            onClick={() => toggleSort(sort.column)}
            aria-label={`${sort.column} ${sort.direction === 'asc' ? '내림차순' : '오름차순'} 정렬`}
            className="inline-flex items-center gap-1 rounded-lg border border-apple-divider px-3 py-2 text-control text-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            {sort.direction === 'asc' ? <ArrowUp size={14} aria-hidden="true" /> : <ArrowDown size={14} aria-hidden="true" />}
            {sort.direction === 'asc' ? '오름차순' : '내림차순'}
          </button>
        )}
      </div>

      <div className="hidden xl:block overflow-x-auto">
        <table className="w-full table-fixed border-collapse" style={{ minWidth: minTableWidth }}>
          <thead className="bg-apple-gray/60">
            <tr className="border-b-2 border-apple-divider">
              {columns.map(col => {
                const direction = sort?.column === col.header ? sort.direction : null
                const SortIcon = direction === 'asc' ? ArrowUp : direction === 'desc' ? ArrowDown : ArrowUpDown
                return (
                  <th
                    key={col.header}
                    scope="col"
                    aria-sort={direction === 'asc' ? 'ascending' : direction === 'desc' ? 'descending' : 'none'}
                    className={`${MODAL_CLS.thCell} ${col.width === 'wide' ? '' : 'w-48'}`}
                  >
                    <button
                      type="button"
                      onClick={() => toggleSort(col.header)}
                      aria-label={`${col.header} ${direction === 'asc' ? '내림차순' : '오름차순'} 정렬`}
                      className={`inline-flex w-full items-center justify-center gap-1.5 rounded px-2 py-1 transition-colors hover:bg-apple-divider/40 hover:text-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${direction ? 'text-brand-600' : ''}`}
                    >
                      {col.header}
                      <SortIcon size={13} aria-hidden="true" className={`shrink-0 ${direction ? '' : 'opacity-50'}`} />
                    </button>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map(row => (
              <tr
                key={row.key}
                role="link"
                tabIndex={0}
                aria-label={`${row.key} Jira 티켓 새 탭으로 열기`}
                onClick={() => openIssue(row.key)}
                onKeyDown={(event) => handleIssueKeyDown(event, row.key)}
                className="cursor-pointer transition-colors duration-150 hover:bg-apple-gray/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500"
              >
                {columns.map(col => (
                  <td
                    key={col.header}
                    className={col.width === 'date'
                      ? 'w-48 min-w-48 whitespace-nowrap px-4 text-center align-middle'
                      : 'min-w-0 overflow-hidden whitespace-nowrap px-4 text-center align-middle'}
                  >
                    <div className={col.width === 'date'
                      ? 'whitespace-nowrap text-center [&>*]:pr-0'
                      : col.width === 'wide'
                      ? 'min-w-0 whitespace-normal break-words text-center [&>*]:pr-0 [&>*]:whitespace-normal'
                      : 'min-w-0 truncate text-center [&>*]:pr-0'}
                    >
                      {col.renderCell(row)}
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="xl:hidden">
        {rows.map(row => (
          <div
            key={row.key}
            role="link"
            tabIndex={0}
            aria-label={`${row.key} Jira 티켓 새 탭으로 열기`}
            onClick={() => openIssue(row.key)}
            onKeyDown={(event) => handleIssueKeyDown(event, row.key)}
            className="cursor-pointer flex flex-col gap-1 rounded-lg px-2 py-3 text-center transition-colors hover:bg-apple-gray/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500"
          >
            <div className="flex items-center justify-center gap-3 flex-wrap">
              {primaryColumns.map(column => (
                <div key={column.header} className="text-label font-mono font-medium text-brand-600 whitespace-nowrap">
                  {renderMobileColumn(column, row)}
                </div>
              ))}
              {secondaryColumns.map(column => (
                <div key={column.header} className="text-caption text-apple-light tabular-nums whitespace-nowrap">
                  {renderMobileColumn(column, row)}
                </div>
              ))}
            </div>
            {summaryColumns.map(column => (
              <div key={column.header} className="min-w-0 break-words text-label text-apple-dark/80">
                {renderMobileColumn(column, row)}
              </div>
            ))}
            {detailColumns.length > 0 && (
              <div className="flex flex-wrap items-center justify-center gap-2 text-caption text-apple-light">
                {detailColumns.map((column, index) => (
                  <Fragment key={column.header}>
                    {index > 0 && <span aria-hidden="true">·</span>}
                    {renderMobileColumn(column, row)}
                  </Fragment>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {paginate && totalPages > 1 && (
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-apple-divider">
          <span className="text-label text-apple-light">
            {(currentPage - 1) * TABLE_PAGE_SIZE + 1}–{Math.min(currentPage * TABLE_PAGE_SIZE, data.length)} / {data.length}건
          </span>
          <div className="flex flex-wrap gap-1">
            {Array.from({ length: totalPages }).map((_, i) => (
              <button
                key={i}
                  type="button"
                  aria-current={currentPage === i + 1 ? 'page' : undefined}
                onClick={() => setPage(i + 1)}
                className={`px-3 py-1 rounded text-control font-medium transition-colors ${
                  currentPage === i + 1 ? 'bg-brand-500 text-white' : 'bg-gray-100 text-apple-mid hover:bg-gray-200'
                }`}
              >
                {i + 1}
              </button>
            ))}
          </div>
        </div>
      )}
    </IssueModalShell>
  )
}
