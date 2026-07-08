// frontend/src/presentation/components/common/SearchWidget.tsx
import { useEffect, useRef, useState, useCallback } from 'react'
import { fetchSearchResults, fetchJiraBaseUrl, SearchResult } from '@/infrastructure/api/searchApi'

const JIRA_COLOR = 'bg-blue-100 text-blue-700'
const CONFLUENCE_COLOR = 'bg-purple-100 text-purple-700'
const DIRECT_COLOR = 'bg-brand-100 text-brand-700'

const ISSUE_NUMBER_RE = /^\d{4,5}$/

function isIssueNumber(q: string): boolean {
  return ISSUE_NUMBER_RE.test(q.trim())
}

function buildDirectItem(num: string, jiraBaseUrl: string): SearchResult {
  const key = `TACEA-${num}`
  return {
    type: 'jira',
    key,
    title: `${key} 이슈 바로가기`,
    status: 'direct',
    issue_type: 'direct',
    url: `${jiraBaseUrl}/browse/${key}`,
  }
}

function TypeBadge({ type, isDirect }: { type: string; isDirect?: boolean }) {
  const cls = isDirect ? DIRECT_COLOR : type === 'jira' ? JIRA_COLOR : CONFLUENCE_COLOR
  const label = isDirect ? '직접링크' : type === 'jira' ? 'JIRA' : 'Confluence'
  return (
    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full flex-shrink-0 ${cls}`}>
      {label}
    </span>
  )
}

function DropdownItem({
  item,
  isActive,
  isDirect,
  onClick,
}: {
  item: SearchResult
  isActive: boolean
  isDirect?: boolean
  onClick: () => void
}) {
  return (
    <li
      className={`flex items-center gap-2 px-3 py-2 cursor-pointer select-none ${
        isDirect
          ? isActive
            ? 'bg-brand-50 border-b border-brand-100'
            : 'bg-brand-50 border-b border-brand-100 hover:bg-brand-100'
          : isActive
          ? 'bg-gray-100'
          : 'hover:bg-gray-50'
      }`}
      onMouseDown={(e) => {
        e.preventDefault()
        onClick()
      }}
    >
      <TypeBadge type={item.type} isDirect={isDirect} />
      <span
        className={`text-[12px] font-medium truncate flex-1 ${
          isDirect ? 'text-brand-700' : 'text-gray-800'
        }`}
      >
        {item.key && !isDirect && <span className="text-gray-400 mr-1">[{item.key}]</span>}
        {item.title}
      </span>
      {!isDirect && item.status && (
        <span className="text-[10px] text-gray-400 flex-shrink-0">{item.status}</span>
      )}
      {isDirect && (
        <svg className="w-3 h-3 text-brand-400 flex-shrink-0" fill="none" viewBox="0 0 16 16">
          <path
            d="M3 8h10M9 4l4 4-4 4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </li>
  )
}

function SearchModal({
  results,
  query,
  jiraBaseUrl,
  onClose,
}: {
  results: SearchResult[]
  query: string
  jiraBaseUrl: string
  onClose: () => void
}) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <span className="text-[15px] font-semibold text-gray-800">
            "{query}" 검색 결과
          </span>
          <button
            className="text-gray-400 hover:text-gray-600 transition-colors"
            onClick={onClose}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                d="M5 5l10 10M15 5L5 15"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        {results.length === 0 ? (
          <div className="px-5 py-10 text-center text-gray-400 text-[13px]">
            검색 결과가 없습니다.
          </div>
        ) : (
          <ul className="divide-y">
            {results.map((item, idx) => {
              const isDirect = item.issue_type === 'direct'
              return (
                <li key={`${item.type}-${item.key}-${idx}`}>
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`flex items-start gap-3 px-5 py-3.5 transition-colors ${
                      isDirect ? 'bg-brand-50 hover:bg-brand-100' : 'hover:bg-gray-50'
                    }`}
                  >
                    <TypeBadge type={item.type} isDirect={isDirect} />
                    <div className="flex-1 min-w-0">
                      <p
                        className={`text-[13px] font-medium truncate ${
                          isDirect ? 'text-brand-700' : 'text-gray-800'
                        }`}
                      >
                        {!isDirect && item.key && (
                          <span className="text-gray-400 mr-1.5">[{item.key}]</span>
                        )}
                        {item.title}
                      </p>
                      {!isDirect && (
                        <p className="text-[11px] text-gray-400 mt-0.5">
                          {item.issue_type}
                          {item.status ? ` · ${item.status}` : ''}
                        </p>
                      )}
                    </div>
                    <svg
                      className={`w-4 h-4 flex-shrink-0 mt-0.5 ${
                        isDirect ? 'text-brand-400' : 'text-gray-300'
                      }`}
                      fill="none"
                      viewBox="0 0 16 16"
                    >
                      <path
                        d="M3 8h10M9 4l4 4-4 4"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </a>
                </li>
              )
            })}
          </ul>
        )}

        <div className="px-5 py-3 border-t bg-gray-50">
          <a
            href={`${jiraBaseUrl}/issues/?jql=${encodeURIComponent(`text ~ "${query}"`)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[12px] text-brand-600 hover:underline"
          >
            JIRA에서 더 검색하기 →
          </a>
        </div>
      </div>
    </div>
  )
}

export default function SearchWidget() {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<SearchResult[]>([])
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const [isLoading, setIsLoading] = useState(false)
  const [modalResults, setModalResults] = useState<SearchResult[] | null>(null)
  const [modalQuery, setModalQuery] = useState('')
  const [jiraBaseUrl, setJiraBaseUrl] = useState('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const jiraBaseUrlRef = useRef('')

  useEffect(() => {
    fetchJiraBaseUrl()
      .then((url) => {
        setJiraBaseUrl(url)
        jiraBaseUrlRef.current = url
      })
      .catch(() => {
        jiraBaseUrlRef.current = ''
      })
  }, [])

  const prependDirectIfNeeded = useCallback(
    (q: string, items: SearchResult[]): SearchResult[] => {
      if (!isIssueNumber(q)) return items
      const direct = buildDirectItem(q.trim(), jiraBaseUrlRef.current)
      return [direct, ...items]
    },
    [],
  )

  const fetchSuggestions = useCallback(
    async (q: string) => {
      if (abortRef.current) abortRef.current.abort()
      abortRef.current = new AbortController()
      setIsLoading(true)
      try {
        const results = await fetchSearchResults(q, 5)
        const merged = prependDirectIfNeeded(q, results)
        setSuggestions(merged)
        setIsDropdownOpen(merged.length > 0)
        setActiveIndex(-1)
      } catch {
        const fallback = prependDirectIfNeeded(q, [])
        setSuggestions(fallback)
        setIsDropdownOpen(fallback.length > 0)
      } finally {
        setIsLoading(false)
      }
    },
    [prependDirectIfNeeded],
  )

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (query.trim().length === 0) {
      setSuggestions([])
      setIsDropdownOpen(false)
      return
    }
    debounceRef.current = setTimeout(() => fetchSuggestions(query.trim()), 1000)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query, fetchSuggestions])

  const openModal = useCallback(
    async (q: string) => {
      setIsDropdownOpen(false)
      setModalQuery(q)
      setIsLoading(true)
      try {
        const results = await fetchSearchResults(q, 5)
        setModalResults(prependDirectIfNeeded(q, results))
      } catch {
        setModalResults(prependDirectIfNeeded(q, []))
      } finally {
        setIsLoading(false)
      }
    },
    [prependDirectIfNeeded],
  )

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isDropdownOpen && e.key !== 'Enter') return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((i) => Math.min(i + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((i) => Math.max(i - 1, -1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (activeIndex >= 0 && suggestions[activeIndex]) {
        window.open(suggestions[activeIndex].url, '_blank', 'noopener,noreferrer')
      } else if (query.trim()) {
        openModal(query.trim())
      }
    } else if (e.key === 'Escape') {
      setIsDropdownOpen(false)
    }
  }

  return (
    <>
      <div className="relative w-56 3xl:w-64">
        <div className="relative flex items-center">
          <svg
            className="absolute left-2.5 w-3.5 h-3.5 text-gray-400 pointer-events-none"
            fill="none"
            viewBox="0 0 16 16"
          >
            <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.5" />
            <path
              d="M10 10l3 3"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => suggestions.length > 0 && setIsDropdownOpen(true)}
            onBlur={() => setTimeout(() => setIsDropdownOpen(false), 150)}
            placeholder="JIRA / Confluence 검색"
            className="w-full pl-8 pr-8 py-1.5 text-[12px] bg-gray-100 rounded-lg border border-transparent focus:border-brand-400 focus:bg-white focus:outline-none transition-all placeholder-gray-400"
          />
          {isLoading ? (
            <svg
              className="absolute right-2.5 w-3.5 h-3.5 text-gray-400 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="3"
              />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          ) : (
            <button
              className="absolute right-2 text-gray-400 hover:text-brand-600 transition-colors"
              onMouseDown={(e) => {
                e.preventDefault()
                if (query.trim()) openModal(query.trim())
              }}
            >
              <svg width="14" height="14" fill="none" viewBox="0 0 16 16">
                <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.5" />
                <path
                  d="M10 10l3 3"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          )}
        </div>

        {isDropdownOpen && suggestions.length > 0 && (
          <ul className="absolute top-full mt-1 left-0 right-0 bg-white rounded-xl shadow-lg border border-gray-100 z-40 overflow-hidden">
            {suggestions.map((item, idx) => {
              const isDirect = item.issue_type === 'direct'
              return (
                <DropdownItem
                  key={`${item.type}-${item.key}-${idx}`}
                  item={item}
                  isActive={idx === activeIndex}
                  isDirect={isDirect}
                  onClick={() => {
                    setIsDropdownOpen(false)
                    window.open(item.url, '_blank', 'noopener,noreferrer')
                  }}
                />
              )
            })}
            <li
              className="px-3 py-1.5 text-center border-t"
              onMouseDown={(e) => {
                e.preventDefault()
                openModal(query.trim())
              }}
            >
              <span className="text-[11px] text-brand-600 cursor-pointer hover:underline">
                전체 결과 보기
              </span>
            </li>
          </ul>
        )}
      </div>

      {modalResults !== null && (
        <SearchModal
          results={modalResults}
          query={modalQuery}
          jiraBaseUrl={jiraBaseUrl}
          onClose={() => setModalResults(null)}
        />
      )}
    </>
  )
}
