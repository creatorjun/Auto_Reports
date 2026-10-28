// frontend/src/presentation/components/cve/CveInventoryControls.tsx
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cvePageCount } from '@/application/services/cveInventory'

export const cveFieldClass = 'w-full min-w-0 rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control text-apple-dark focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30'
export const cveButtonClass = 'inline-flex items-center justify-center gap-2 rounded-xl border border-apple-divider bg-apple-surface px-3 py-2.5 text-control font-medium text-apple-dark transition-colors hover:bg-apple-gray focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:opacity-40'

export function CvePagination({ page, total, pageSize, onPage, label, disabled = false }: {
  page: number; total: number; pageSize: number; onPage: (page: number) => void; label: string; disabled?: boolean
}) {
  const pageCount = cvePageCount(total, pageSize)
  if (pageCount <= 1) return null
  return <nav aria-label={label} className="flex flex-wrap items-center justify-center gap-3 py-2">
    <button type="button" className={cveButtonClass} disabled={disabled || page <= 1} onClick={() => onPage(page - 1)} aria-label={`${label} 이전 페이지`}><ChevronLeft size={16} aria-hidden="true" /></button>
    <label className="flex items-center gap-2 text-control text-apple-mid"><span className="sr-only">{label} 페이지 선택</span><select className={`${cveFieldClass} !w-auto`} value={page} disabled={disabled} onChange={(event) => onPage(Number(event.target.value))}>{Array.from({ length: pageCount }, (_, index) => <option key={index} value={index + 1}>{index + 1}</option>)}</select><span className="tabular-nums">/ {pageCount.toLocaleString('ko-KR')}</span></label>
    <button type="button" className={cveButtonClass} disabled={disabled || page >= pageCount} onClick={() => onPage(page + 1)} aria-label={`${label} 다음 페이지`}><ChevronRight size={16} aria-hidden="true" /></button>
  </nav>
}
