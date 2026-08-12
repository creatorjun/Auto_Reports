// frontend/src/infrastructure/api/searchApi.ts
import client from './client'
import type { SearchResult } from '@/domain/Search'

async function fetchSearchResults(
  query: string,
  limit = 5,
  signal?: AbortSignal,
): Promise<SearchResult[]> {
  const { data } = await client.get<SearchResult[]>('/search', {
    params: { q: query, limit },
    signal,
  })
  return data
}

async function fetchJiraBaseUrl(): Promise<string> {
  const { data } = await client.get<{ jira_base_url: string }>('/config')
  return data.jira_base_url.replace(/\/$/, '')
}

export const searchApi = {
  search: fetchSearchResults,
  getJiraBaseUrl: fetchJiraBaseUrl,
}
