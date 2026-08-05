// frontend/src/presentation/components/partner/PartnerElapsedBadge.tsx
export default function PartnerElapsedBadge({ days }: { days: number }) {
  const color =
    days >= 14 ? 'text-red-500' :
    days >= 7  ? 'text-orange-500' :
                 'text-apple-light'
  return <span className={`text-xs font-medium ${color}`}>{days}일</span>
}
