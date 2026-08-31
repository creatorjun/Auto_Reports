// frontend/src/presentation/components/partner/PartnerSearchInput.tsx
import { Search, X } from 'lucide-react'

export default function PartnerSearchInput({
  value,
  onChange,
}: {
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div className="flex items-center gap-2 rounded-2xl border border-apple-divider bg-white px-4 py-2.5 shadow-sm transition focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-500/20">
      <Search size={16} className="flex-shrink-0 text-apple-light" aria-hidden="true" />
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="파트너사 또는 직원명 검색"
        aria-label="파트너사 또는 직원명 검색"
        className="min-w-0 flex-1 appearance-none bg-transparent text-sm text-apple-dark outline-none placeholder:text-apple-light [&::-webkit-search-cancel-button]:appearance-none"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange('')}
          aria-label="검색어 지우기"
          className="rounded-full p-0.5 text-apple-light transition-colors hover:bg-apple-gray hover:text-apple-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30"
        >
          <X size={15} aria-hidden="true" />
        </button>
      )}
    </div>
  )
}
