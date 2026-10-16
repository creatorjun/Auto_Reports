// frontend/src/presentation/components/partner/PartnerPanelHeader.tsx
export default function PartnerPanelHeader({
  title,
  count,
  loading,
}: {
  title: string
  count?: number
  loading?: boolean
}) {
  return (
    <div className="flex shrink-0 items-center justify-between gap-2 border-b border-apple-divider px-4 py-3">
      <span className="min-w-0 break-words text-section-title font-semibold text-apple-dark">{title}</span>
      {loading
        ? <span className="shrink-0 text-caption text-apple-light animate-pulse">로딩 중...</span>
        : count !== undefined && <span className="shrink-0 text-caption text-apple-light">{count}개</span>
      }
    </div>
  )
}
