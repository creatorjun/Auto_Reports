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

export default function PartnerIssueRow({
  issue,
  jiraBrowse,
}: {
  issue: PartnerIssue
  jiraBrowse: string
}) {
  return (
    <a
      href={`${jiraBrowse}/${issue.key}`}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${issue.key} Jira 티켓 새 탭으로 열기`}
      className="flex cursor-pointer items-start gap-3 border-b border-apple-divider/50 px-4 py-3 transition-colors hover:bg-apple-gray"
    >
      <span className={`mt-0.5 inline-flex flex-shrink-0 items-center rounded px-1.5 py-0.5 text-[10px] font-semibold ${STAGE_COLOR[issue.stage_index] ?? STAGE_COLOR[0]}`}>
        S{issue.stage_index}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-apple-dark">{issue.summary}</p>
        <p className="mt-0.5 text-xs text-apple-light">{issue.key}</p>
      </div>
      <PartnerElapsedBadge days={issue.elapsed_days} />
    </a>
  )
}
