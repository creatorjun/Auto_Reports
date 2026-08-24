// frontend/src/presentation/components/common/IssueTypeFilter.tsx
import { Check, ListFilter, RotateCcw } from 'lucide-react'

interface Props {
  issueTypes: string[]
  selectedTypes: ReadonlySet<string> | null
  supported: boolean
  onToggle: (issueType: string) => void
  onReset: () => void
}

const ISSUE_TYPE_LABELS: Record<string, string> = {
  '라이선스': '라이센스 요청',
}

export default function IssueTypeFilter({
  issueTypes,
  selectedTypes,
  supported,
  onToggle,
  onReset,
}: Props) {
  const selectedCount = selectedTypes?.size ?? issueTypes.length

  return (
    <section className="card flex flex-col gap-4" aria-labelledby="issue-type-filter-title">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
            <ListFilter size={20} aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 id="issue-type-filter-title" className="text-ui-sm font-semibold text-apple-dark">
                요청 유형
              </h2>
              {supported && (
                <span className="rounded-full bg-apple-gray px-2.5 py-1 text-xs font-semibold text-apple-mid">
                  {selectedCount}/{issueTypes.length} 포함
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-apple-light">
              현재 Jira에 등록된 모든 요청 유형을 실시간으로 포함하거나 제외할 수 있습니다.
            </p>
          </div>
        </div>
        {supported && (
          <button
            type="button"
            onClick={onReset}
            disabled={selectedTypes === null}
            className="inline-flex min-h-10 shrink-0 items-center justify-center gap-2 self-start rounded-xl border border-apple-divider bg-white px-3.5 py-2 text-sm font-semibold text-apple-mid transition-colors hover:border-brand-200 hover:text-brand-600 disabled:cursor-default disabled:opacity-40 sm:self-auto"
          >
            <RotateCcw size={15} aria-hidden="true" />
            전체 포함
          </button>
        )}
      </div>

      {supported ? (
        <div className="flex flex-wrap gap-2" role="group" aria-label="요청 유형 포함 여부">
          {issueTypes.map((issueType) => {
            const selected = selectedTypes === null || selectedTypes.has(issueType)
            return (
              <button
                key={issueType}
                type="button"
                aria-pressed={selected}
                onClick={() => onToggle(issueType)}
                className={`inline-flex min-h-11 items-center gap-2 rounded-xl border px-3.5 py-2 text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 ${
                  selected
                    ? 'border-brand-200 bg-brand-50 text-brand-700 shadow-apple-sm'
                    : 'border-apple-divider bg-white text-apple-light hover:border-apple-mid hover:text-apple-mid'
                }`}
              >
                <span className={`flex h-5 w-5 items-center justify-center rounded-md border ${
                  selected ? 'border-brand-500 bg-brand-500 text-white' : 'border-apple-divider bg-white'
                }`}>
                  {selected && <Check size={13} strokeWidth={3} aria-hidden="true" />}
                </span>
                {ISSUE_TYPE_LABELS[issueType] ?? issueType}
              </button>
            )
          })}
        </div>
      ) : (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-800">
          이 보고서는 유형별 집계 데이터가 없습니다. 보고서를 새로 생성하거나 갱신하면 유형 필터를 사용할 수 있습니다.
        </div>
      )}
    </section>
  )
}
