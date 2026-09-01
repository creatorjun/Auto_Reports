// frontend/src/presentation/components/partner/PartnerSearchInput.tsx
import { Search, X } from 'lucide-react'

export default function PartnerSearchInput({
  value,
  onChange,
  placeholder,
  ariaLabel,
  disabled = false,
}: {
  value: string
  onChange: (value: string) => void
  placeholder: string
  ariaLabel: string
  disabled?: boolean
}) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-apple-divider bg-apple-surface px-3 py-2 transition focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-500/20">
      <Search size={16} className="flex-shrink-0 text-apple-light" aria-hidden="true" />
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel}
        disabled={disabled}
        className="min-w-0 flex-1 appearance-none bg-transparent text-xs text-apple-dark outline-none placeholder:text-apple-light disabled:cursor-not-allowed disabled:opacity-60 [&::-webkit-search-cancel-button]:appearance-none"
      />
      {value && !disabled && (
        <button
          type="button"
          onClick={() => onChange('')}
          aria-label={`${ariaLabel} 지우기`}
          className="rounded-full p-0.5 text-apple-light transition-colors hover:bg-apple-gray hover:text-apple-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30"
        >
          <X size={15} aria-hidden="true" />
        </button>
      )}
    </div>
  )
}
