// frontend/src/presentation/hooks/useIssueColumnSearch.ts
import { useCallback, useMemo, useState } from 'react'
import type { RecentIssue } from '@/domain/Issue'
import { filterIssuesByColumns } from '@/domain/IssueColumnSearch'
import type { IssueColumn, IssueColumnFilters } from '@/domain/IssueColumnSearch'

export function useIssueColumnSearch(
  issues: RecentIssue[],
  filters?: IssueColumnFilters,
  onFilterChange?: (column: IssueColumn, value: string) => void,
) {
  const [localFilters, setLocalFilters] = useState<IssueColumnFilters>({})
  const columnFilters = filters ?? localFilters
  const onColumnFilterChange = useCallback((column: IssueColumn, value: string) => {
    if (filters === undefined) setLocalFilters((current) => ({ ...current, [column]: value }))
    onFilterChange?.(column, value)
  }, [filters, onFilterChange])
  const filteredIssues = useMemo(
    () => filterIssuesByColumns(issues, columnFilters),
    [issues, columnFilters],
  )
  return { columnFilters, onColumnFilterChange, filteredIssues }
}
