// frontend/src/presentation/components/partner/PartnerIssueRow.tsx
import type { PartnerIssue } from '@/domain/Partner'
import PartnerElapsedBadge from './PartnerElapsedBadge'

const STAGE_COLOR: Record<number, string> = {
  0: 'bg-gray-100 text-gray-500',
  1: 'bg-blue-100 text-blue-700',
  2: 'bg-yellow-100 text-yellow-700',
  3: 'bg-orange-100 text-orange-700',
  4: 'bg-green-100 text-green-700',
  5: 'bg-purple-100 text-purple-700',
}

export default function PartnerIssueRow({ issue }: { issue: PartnerIssue }) {
  const href = `https://seculayer.atlassian.net/browse/${issue.key}`
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="block px-4 py-3 border-b border-apple-divider/50 hover:bg-blue-50 transition-colors cursor-pointer"
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-xs font-mono text-blue-600 flex-shrink-0">
          {issue.key}
        </span>
        <PartnerElapsedBadge days={issue.elapsed_days} />
      </div>
      <p className="text-sm text-apple-dark leading-snug mb-1.5 line-clamp-2">
        {issue.summary}
      </p>
      <div className="flex items-center gap-2 flex-wrap">
        <span className={[
          'text-xs px-2 py-0.5 rounded-full font-medium',
          STAGE_COLOR[issue.stage_index] ?? 'bg-gray-100 text-gray-500',
        ].join(' ')}>
          {issue.status}
        </span>
        <span className="text-xs text-apple-light">{issue.type}</span>
        {issue.tac_team && issue.tac_team !== '미지정' && (
          <span className="text-xs text-apple-light">담당: {issue.tac_team}</span>
        )}
      </div>
      <p className="text-xs text-apple-light mt-1">{issue.created}</p>
    </a>
  )
}
