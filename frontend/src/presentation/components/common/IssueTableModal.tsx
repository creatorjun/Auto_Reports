// frontend/src/presentation/components/common/IssueTableModal.tsx
import { Fragment, useState } from 'react'
import { useJira } from '@/presentation/context/JiraContext'
import { MODAL_CLS } from '@/presentation/config/ui'
import { TABLE_PAGE_SIZE } from '@/presentation/config/constants'
import IssueModalShell from '@/presentation/components/common/IssueModalShell'
import type { ModalSize } from '@/presentation/config/ui'
import type { KeyboardEvent, ReactNode } from 'react'

export interface ColumnDef<T> {
  header: string
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
  onClose,
}: Props<T>) {
  const { jiraBrowse } = useJira()
  const [page, setPage] = useState(1)

  const totalPages = paginate ? Math.ceil(data.length / TABLE_PAGE_SIZE) : 1
  const rows = paginate
    ? data.slice((page - 1) * TABLE_PAGE_SIZE, page * TABLE_PAGE_SIZE)
    : data

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

      <div className="hidden md:block overflow-x-auto">
        <table className="w-full table-fixed border-collapse">
          <thead className="bg-apple-gray/60">
            <tr className="border-b-2 border-apple-divider">
              {columns.map(col => (
                <th
                  key={col.header}
                  className={`${MODAL_CLS.thCell} ${col.width === 'wide' ? 'w-[40%]' : col.width === 'date' ? 'w-48' : ''}`}
                >
                  {col.header}
                </th>
              ))}
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

      <div className="md:hidden">
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
            <div className="flex items-center justify-center gap-3">
              {primaryColumns.map(column => (
                <div key={column.header} className="text-ui-sm font-mono font-medium text-brand-600 whitespace-nowrap">
                  {renderMobileColumn(column, row)}
                </div>
              ))}
              {secondaryColumns.map(column => (
                <div key={column.header} className="text-ui-xs text-apple-light tabular-nums whitespace-nowrap">
                  {renderMobileColumn(column, row)}
                </div>
              ))}
            </div>
            {summaryColumns.map(column => (
              <div key={column.header} className="min-w-0 truncate text-ui-sm text-apple-dark/80">
                {renderMobileColumn(column, row)}
              </div>
            ))}
            {detailColumns.length > 0 && (
              <div className="flex flex-wrap items-center justify-center gap-2 text-ui-xs text-apple-light">
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
        <div className="flex items-center justify-between pt-3 border-t border-apple-divider">
          <span className="text-ui-sm text-apple-light">
            {(page - 1) * TABLE_PAGE_SIZE + 1}–{Math.min(page * TABLE_PAGE_SIZE, data.length)} / {data.length}건
          </span>
          <div className="flex gap-1">
            {Array.from({ length: totalPages }).map((_, i) => (
              <button
                key={i}
                onClick={() => setPage(i + 1)}
                className={`px-3 py-1 rounded text-ui-sm font-medium transition-colors ${
                  page === i + 1 ? 'bg-brand-500 text-white' : 'bg-gray-100 text-apple-mid hover:bg-gray-200'
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
