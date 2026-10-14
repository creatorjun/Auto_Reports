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
    <div className="flex items-center justify-between px-4 py-3 border-b border-apple-divider">
      <span className="text-section-title font-semibold text-apple-dark">{title}</span>
      {loading
        ? <span className="text-caption text-apple-light animate-pulse">로딩 중...</span>
        : count !== undefined && <span className="text-caption text-apple-light">{count}개</span>
      }
    </div>
  )
}
