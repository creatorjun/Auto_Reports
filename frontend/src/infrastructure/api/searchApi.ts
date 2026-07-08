// frontend/src/infrastructure/api/searchApi.ts
import client from './client'

export interface SearchResult {
  type: 'jira' | 'confluence'
  key: string
  title: string
  status: string
  issue_type: string
  url: string
}

export async function fetchSearchResults(
  query: string,
  limit = 5,
): Promise<SearchResult[]> {
  const { data } = await client.get<SearchResult[]>('/search', {
    params: { q: query, limit },
  })
  return data
}
