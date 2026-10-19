// frontend/src/presentation/utils/issueTableSorting.ts
export type IssueSortValue = string | number | boolean | null | undefined
export type IssueSortDirection = 'asc' | 'desc'

export interface IssueTableSort {
  column: string
  direction: IssueSortDirection
}

export interface SortableIssueColumn<T> {
  header: string
  sortValue: (row: T) => IssueSortValue
  sortType?: 'text' | 'number' | 'date'
}

const COLLATOR = new Intl.Collator('ko', { numeric: true, sensitivity: 'base' })

function normalizedValue(value: IssueSortValue, type: SortableIssueColumn<unknown>['sortType']): string | number | null {
  if (value == null) return null
  if (typeof value === 'string') {
    value = value.trim()
    if (!value || value === '-' || value === '—') return null
  }
  if (type === 'date') {
    const timestamp = typeof value === 'number' ? value : Date.parse(String(value).replace(' ', 'T'))
    return Number.isFinite(timestamp) ? timestamp : null
  }
  if (type === 'number' || typeof value === 'number' || typeof value === 'boolean') {
    const number = Number(value)
    return Number.isFinite(number) ? number : null
  }
  return value
}

export function sortIssueTableRows<T>(data: T[], columns: SortableIssueColumn<T>[], sort: IssueTableSort | null): T[] {
  const column = sort && columns.find((candidate) => candidate.header === sort.column)
  if (!sort || !column) return data
  const direction = sort.direction === 'asc' ? 1 : -1
  return [...data].sort((left, right) => {
    const a = normalizedValue(column.sortValue(left), column.sortType)
    const b = normalizedValue(column.sortValue(right), column.sortType)
    if (a == null) return b == null ? 0 : 1
    if (b == null) return -1
    const comparison = typeof a === 'number' && typeof b === 'number' ? a - b : COLLATOR.compare(String(a), String(b))
    return comparison * direction
  })
}
