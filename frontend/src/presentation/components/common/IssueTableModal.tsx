// frontend/src/presentation/components/common/IssueTableModal.tsx
import { useState } from 'react'
import { useJira } from '@/presentation/context/JiraContext'
import { MODAL_CLS } from '@/presentation/config/ui'
import { TABLE_PAGE_SIZE } from '@/presentation/config/constants'
import IssueModalShell from '@/presentation/components/common/IssueModalShell'
import type { ModalSize } from '@/presentation/config/ui'
import type { ReactNode } from 'react'

export interface ColumnDef<T> {
  header: string
  renderCell: (row: T) => ReactNode
  renderMobile?: (row: T) => ReactNode
}

interface Props<T extends { key: string }> {
  title: string
  subtitle: string
  size?: ModalSize
  data: T[]
  columns: ColumnDef<T>[]
  paginate?: boolean
  headerSlot?: ReactNode
  renderMobileRow?: (row: T, jiraBrowse: string) => ReactNode
  onClose: () => void
}

export default function IssueTableModal<T extends { key: string }>({
  title,
  subtitle,
  size,
  data,
  columns,
  paginate = false,
  headerSlot,
  renderMobileRow,
  onClose,
}: Props<T>) {
  const { jiraBrowse } = useJira()
  const [page, setPage] = useState(1)

  const totalPages = paginate ? Math.ceil(data.length / TABLE_PAGE_SIZE) : 1
  const rows = paginate
    ? data.slice((page - 1) * TABLE_PAGE_SIZE, page * TABLE_PAGE_SIZE)
    : data

  return (
    <IssueModalShell title={title} subtitle={subtitle} size={size} onClose={onClose}>
      {headerSlot && <div className="mb-4">{headerSlot}</div>}

      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-apple-divider/60">
              {columns.map(col => (
                <th key={col.header} className={MODAL_CLS.thCell}>{col.header}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-apple-divider/40">
            {rows.map(row => (
              <tr
                key={row.key}
                onClick={() => window.open(`${jiraBrowse}/${row.key}`, '_blank', 'noreferrer')}
                className="hover:bg-apple-gray/50 transition-colors duration-150 cursor-pointer"
              >
                {columns.map(col => (
                  <td key={col.header}>{col.renderCell(row)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="md:hidden divide-y divide-apple-divider/40">
        {rows.map(row =>
          renderMobileRow
            ? renderMobileRow(row, jiraBrowse)
            : (
              <div
                key={row.key}
                onClick={() => window.open(`${jiraBrowse}/${row.key}`, '_blank', 'noreferrer')}
                className="py-3 flex flex-col gap-1 cursor-pointer hover:bg-apple-gray/50 rounded-lg px-2 transition-colors"
              >
                {columns[0]?.renderMobile?.(row)}
              </div>
            )
        )}
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
