// frontend/src/presentation/components/site/detail/SiteDetailShared.tsx
import { useState } from 'react'

export const STATUS_LABEL: Record<string, string> = {
  installing: '구축중',
  active: '운영 중',
  inactive: '비활성',
  expired: '만료',
  maintenance: '유지보수',
}

export const STATUS_COLOR: Record<string, string> = {
  installing: 'bg-blue-100 text-blue-700',
  active: 'bg-green-100 text-green-700',
  inactive: 'bg-gray-100 text-gray-500',
  expired: 'bg-red-100 text-red-600',
  maintenance: 'bg-yellow-100 text-yellow-700',
}

export const inputCls =
  'w-full min-w-0 border border-apple-divider rounded-xl px-3 py-2 text-sm text-apple-dark bg-white outline-none focus:ring-2 focus:ring-blue-500/30 transition'

export function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      className={`transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
    >
      <path
        d="M4 6l4 4 4-4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function Section({
  title,
  badge,
  defaultOpen = true,
  children,
}: {
  title: string
  badge?: string | number
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="overflow-hidden rounded-2xl border border-apple-divider 3xl:rounded-3xl">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between bg-white px-4 py-3.5 transition-colors hover:bg-apple-gray focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500/30 sm:px-5 3xl:px-6 3xl:py-4"
      >
        <span className="flex items-center gap-2">
          <span className="text-sm font-semibold text-apple-dark">{title}</span>
          {badge !== undefined && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">
              {badge}
            </span>
          )}
        </span>
        <span className="text-apple-light">
          <ChevronIcon open={open} />
        </span>
      </button>
      <div
        className={`transition-all duration-200 overflow-hidden ${
          open ? 'max-h-[6000px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="border-t border-apple-divider bg-white px-4 py-4 sm:px-5 3xl:px-6 3xl:py-5">{children}</div>
      </div>
    </div>
  )
}

export function Row({ label, value }: { label: string; value?: string | number | null }) {
  if (value === undefined || value === null || value === '') return null
  return (
    <div className="flex min-w-0 flex-col gap-1 border-b border-apple-divider/50 py-2 last:border-0 sm:flex-row sm:gap-3 sm:py-1.5">
      <span className="w-full flex-shrink-0 text-xs text-apple-light sm:w-36">{label}</span>
      <span className="min-w-0 break-words text-sm text-apple-dark">{String(value)}</span>
    </div>
  )
}

function EyeIcon({ open }: { open: boolean }) {
  return open ? (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
      <path
        d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.4" />
      <path d="M2 2l12 12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  ) : (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
      <path
        d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  )
}

export function CredRow({
  label,
  cred,
}: {
  label: string
  cred?: { username: string; password: string; ip?: string; port?: string } | null
}) {
  const [show, setShow] = useState(false)
  if (!cred) return null
  return (
    <div className="flex min-w-0 flex-col items-start gap-1 border-b border-apple-divider/50 py-2 last:border-0 sm:flex-row sm:gap-3 sm:py-1.5">
      <span className="w-full flex-shrink-0 pt-0.5 text-xs text-apple-light sm:w-36">{label}</span>
      <div className="flex min-w-0 flex-col gap-0.5 text-sm text-apple-dark">
        <span className="break-all">{cred.username}</span>
        <span className="flex min-w-0 items-center gap-1.5">
          <span className="break-all font-mono text-xs">
            {show ? cred.password : '•'.repeat(Math.min(cred.password.length, 10))}
          </span>
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            className="text-apple-light hover:text-apple-dark transition-colors"
          >
            <EyeIcon open={show} />
          </button>
        </span>
        {cred.ip && (
          <span className="break-all text-xs text-apple-light">
            IP(URL): {cred.ip}{cred.port ? `:${cred.port}` : ''}
          </span>
        )}
      </div>
    </div>
  )
}

export function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 11)
  if (digits.length < 4) return digits
  if (digits.length < 7) return `${digits.slice(0, 3)}-${digits.slice(3)}`
  if (digits.length < 11)
    return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`
  return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`
}

export function AddBtn({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-blue-600 px-3.5 py-2 text-xs font-medium text-white transition-colors hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30 sm:w-auto sm:py-1.5"
    >
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
        <path d="M6 1v10M1 6h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
      {label}
    </button>
  )
}

export function CardActions({
  onEdit,
  onDelete,
}: {
  onEdit: () => void
  onDelete: () => void
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      <button
        type="button"
        onClick={onEdit}
        className="text-xs px-2.5 py-1 rounded-lg border border-apple-divider text-apple-light hover:text-blue-600 hover:border-blue-300 transition-colors"
      >
        수정
      </button>
      <button
        type="button"
        onClick={onDelete}
        className="text-xs px-2.5 py-1 rounded-lg border border-apple-divider text-apple-light hover:text-red-500 hover:border-red-300 transition-colors"
      >
        삭제
      </button>
    </div>
  )
}
