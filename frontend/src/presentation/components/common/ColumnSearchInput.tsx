// frontend/src/presentation/components/common/ColumnSearchInput.tsx
interface Props {
  label: string
  value: string
  mobile?: boolean
  onChange: (value: string) => void
}

export default function ColumnSearchInput({ label, value, mobile = false, onChange }: Props) {
  return (
    <input
      type="text"
      value={value}
      aria-label={`${label} 컬럼 검색${mobile ? ' 모바일' : ''}`}
      placeholder="검색어"
      onClick={(event) => event.stopPropagation()}
      onKeyDown={(event) => event.stopPropagation()}
      onChange={(event) => onChange(event.target.value)}
      className="mt-2 block h-9 w-full min-w-0 rounded-lg border border-apple-divider bg-apple-surface px-2 text-ui-sm font-normal text-apple-dark placeholder:text-apple-light focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
    />
  )
}
