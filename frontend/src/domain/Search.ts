// frontend/src/domain/Search.ts
export interface SearchResult {
  type: 'jira' | 'confluence'
  key: string
  title: string
  status: string
  issue_type: string
  url: string
}

export function normalizeSearchText(value: string): string {
  return value.normalize('NFKC').trim().toLocaleLowerCase('ko-KR')
}
