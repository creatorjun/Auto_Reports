// frontend/src/presentation/components/common/IssueTypeFilter.tsx
import { Check } from 'lucide-react'
import type { Semester } from '@/domain/Dashboard'

interface Props {
  issueTypes: string[]
  selectedTypes: ReadonlySet<string> | null
  selectedSemester: Semester | null
  supported: boolean
  semesterSupported: boolean
  onToggle: (issueType: string) => void
  onSemesterChange: (semester: Semester | null) => void
  onReset: () => void
}

const ISSUE_TYPE_LABELS: Record<string, string> = {
  '라이선스': '라이센스 요청',
}

export default function IssueTypeFilter({
  issueTypes,
  selectedTypes,
  selectedSemester,
  supported,
  semesterSupported,
  onToggle,
  onSemesterChange,
  onReset,
}: Props) {
  const selectedCount = selectedTypes?.size ?? issueTypes.length
  const hasFilters = selectedTypes !== null || selectedSemester !== null

  return (
    <section className="card" aria-labelledby="issue-type-filter-title">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="issue-type-filter-title" className="text-ui-sm font-semibold text-apple-dark">
            요청 유형
          </h2>
          {supported && (
            <span className="rounded-full bg-apple-gray px-2.5 py-1 text-xs font-semibold text-apple-mid">
              {selectedCount}/{issueTypes.length}
            </span>
          )}
        </div>
        {(supported || semesterSupported) && (
          <button
            type="button"
            onClick={onReset}
            disabled={!hasFilters}
            className="inline-flex min-h-9 items-center justify-center rounded-lg px-3 text-xs font-semibold text-apple-mid transition-colors hover:bg-apple-gray hover:text-brand-600 disabled:cursor-default disabled:opacity-40"
          >
            초기화
          </button>
        )}
      </div>

      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="min-w-0 flex-1">
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
                    className={`inline-flex min-h-10 items-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 ${
                      selected
                        ? 'border-brand-200 bg-brand-50 text-brand-700'
                        : 'border-apple-divider bg-apple-surface text-apple-light hover:border-apple-mid hover:text-apple-mid'
                    }`}
                  >
                    <span className={`flex h-5 w-5 items-center justify-center rounded border ${
                      selected ? 'border-brand-500 bg-brand-500 text-white' : 'border-apple-divider bg-apple-surface'
                    }`}>
                      {selected && <Check size={12} strokeWidth={3} aria-hidden="true" />}
                    </span>
                    {ISSUE_TYPE_LABELS[issueType] ?? issueType}
                  </button>
                )
              })}
            </div>
          ) : (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm font-medium text-amber-800">
              보고서를 갱신하면 요청 유형을 선택할 수 있습니다.
            </div>
          )}
        </div>

        <div className="border-t border-apple-divider pt-4 xl:min-w-64 xl:border-l xl:border-t-0 xl:pb-0.5 xl:pl-5 xl:pt-0">
          <div className="mb-2 text-xs font-semibold text-apple-mid">조회 기간</div>
          <div className="grid grid-cols-2 gap-2" role="group" aria-label="반기 선택">
            {([
              ['h1', '상반기'],
              ['h2', '하반기'],
            ] as const).map(([value, label]) => {
              const selected = selectedSemester === value
              return (
                <button
                  key={value}
                  type="button"
                  aria-pressed={selected}
                  disabled={!semesterSupported}
                  onClick={() => onSemesterChange(selected ? null : value)}
                  className={`min-h-10 rounded-lg border px-4 py-2 text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-40 ${
                    selected
                      ? 'border-brand-500 bg-brand-500 text-white shadow-apple-sm'
                      : 'border-apple-divider bg-apple-surface text-apple-mid hover:border-brand-200 hover:text-brand-600'
                  }`}
                >
                  {label}
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </section>
  )
}
