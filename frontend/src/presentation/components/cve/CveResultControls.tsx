// frontend/src/presentation/components/cve/CveResultControls.tsx
import { ChevronLeft, ChevronRight } from 'lucide-react'

export const cveAction = 'inline-flex items-center justify-center gap-1.5 rounded-lg border border-apple-divider bg-apple-surface px-3 py-2 text-control font-medium text-apple-dark hover:bg-apple-gray focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:opacity-40'

interface CountFilterProps {
  label: string
  count: number | null
  selected: boolean
  indicator: string
  controls: string
  onClick: () => void
}

export function CveCountFilter({ label, count, selected, indicator, controls, onClick }: CountFilterProps) {
  return <button type="button" aria-controls={controls} aria-pressed={selected} onClick={onClick}
    className={`min-w-0 rounded-xl border px-3 py-3 text-left transition-colors focus-visible:outline-brand-500 md:px-4 ${selected ? 'border-brand-500 bg-brand-50' : 'border-apple-divider bg-apple-surface hover:bg-apple-gray'}`}>
    <span className="flex items-center gap-2 text-caption font-medium text-apple-mid">
      <span className={`h-2 w-2 shrink-0 rounded-full ${indicator}`} aria-hidden="true" />{label}
    </span>
    <strong className="mt-1 block text-section-title font-semibold tabular-nums text-apple-dark">{count?.toLocaleString('ko-KR') ?? '—'}</strong>
  </button>
}

interface PaginationProps {
  label: string
  page: number
  pageSize: number
  pageCount: number
  onPage: (page: number) => void
  onPageSize: (size: number) => void
}

export function CvePagination({ label, page, pageCount, pageSize, onPage, onPageSize }: PaginationProps) {
  return <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-apple-divider px-4 py-3 text-caption text-apple-mid md:px-5">
    <label>페이지당 <select aria-label="페이지당 표시 건수" value={pageSize} onChange={(event) => onPageSize(Number(event.target.value))}
      className="rounded-lg border border-apple-divider bg-apple-surface px-2 py-1.5 text-control">
      {[25, 50, 100].map((size) => <option value={size} key={size}>{size}건</option>)}
    </select></label>
    <nav aria-label={label} className="flex items-center gap-3">
      <button type="button" className={cveAction} aria-label="이전 페이지" disabled={page <= 1} onClick={() => onPage(page - 1)}><ChevronLeft size={16} /></button>
      <span className="tabular-nums">{page} / {pageCount}</span>
      <button type="button" className={cveAction} aria-label="다음 페이지" disabled={page >= pageCount} onClick={() => onPage(page + 1)}><ChevronRight size={16} /></button>
    </nav>
  </footer>
}
