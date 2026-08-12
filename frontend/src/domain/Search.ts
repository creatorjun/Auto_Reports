// frontend/src/domain/Search.ts
export interface SearchResult {
  type: 'jira' | 'confluence'
  key: string
  title: string
  status: string
  issue_type: string
  url: string
}
