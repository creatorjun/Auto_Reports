// frontend/src/presentation/pages/SiteManagementPage.tsx
import { useRef, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import type { SiteSummary } from '@/domain/Site'

const STATUS_LABEL: Record<string, string> = {
  active: '운영 중',
  inactive: '비활성',
  expired: '만료',
  maintenance: '유지보수',
}

const STATUS_COLOR: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  inactive: 'bg-gray-100 text-gray-500',
  expired: 'bg-red-100 text-red-600',
  maintenance: 'bg-yellow-100 text-yellow-700',
}

function useDebounce(value: string, delay: number) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(id)
  }, [value, delay])
  return debounced
}

export default function SiteManagementPage() {
  const { sites } = useApplicationServices()
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(-1)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const debouncedQuery = useDebounce(query, 300)

  const { data: searchResults = [], isLoading: isSearching } = useQuery({
    queryKey: ['site-search', debouncedQuery],
    queryFn: () => sites.search(debouncedQuery),
    enabled: debouncedQuery.trim().length >= 1,
    staleTime: 0,
  })

  const { data: recentSites = [] } = useQuery({
    queryKey: ['site-recent'],
    queryFn: () => sites.getRecent(5),
    staleTime: 60_000,
  })

  useEffect(() => {
    setActiveIndex(-1)
    setDropdownOpen(debouncedQuery.trim().length >= 1)
  }, [debouncedQuery])

  const handleSelect = useCallback(
    (site: SiteSummary) => {
      setQuery('')
      setDropdownOpen(false)
      navigate(`/sites/${site.id}`)
    },
    [navigate],
  )

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!dropdownOpen || searchResults.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((i) => Math.min(i + 1, searchResults.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault()
      handleSelect(searchResults[activeIndex])
    } else if (e.key === 'Escape') {
      setDropdownOpen(false)
    }
  }

  return (
    <div className="relative flex flex-col items-center w-full min-h-full px-6 py-10">
      <div className="w-full max-w-xl">
        <h1 className="text-xl font-semibold text-apple-dark mb-6">사이트 관리</h1>

        <div className="relative">
          <div className="flex items-center gap-2 border border-apple-divider rounded-2xl px-4 py-2.5 bg-white shadow-sm focus-within:ring-2 focus-within:ring-blue-500/30">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-apple-light flex-shrink-0">
              <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.4" />
              <path d="M10 10l3 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => debouncedQuery.trim().length >= 1 && setDropdownOpen(true)}
              onBlur={() => setTimeout(() => setDropdownOpen(false), 150)}
              placeholder="사이트명으로 검색..."
              className="flex-1 bg-transparent outline-none text-sm text-apple-dark placeholder:text-apple-light"
              aria-autocomplete="list"
              aria-expanded={dropdownOpen}
              aria-activedescendant={activeIndex >= 0 ? `site-option-${activeIndex}` : undefined}
              role="combobox"
            />
            {query && (
              <button
                onMouseDown={(e) => { e.preventDefault(); setQuery('') }}
                className="text-apple-light hover:text-apple-dark transition-colors"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
                </svg>
              </button>
            )}
          </div>

          {dropdownOpen && (
            <div
              role="listbox"
              className="absolute top-full left-0 right-0 mt-1 bg-white border border-apple-divider rounded-2xl shadow-lg overflow-hidden z-50"
            >
              {isSearching ? (
                <div className="px-4 py-3 text-sm text-apple-light">검색 중...</div>
              ) : searchResults.length === 0 ? (
                <div className="px-4 py-3 text-sm text-apple-light">검색 결과가 없습니다</div>
              ) : (
                searchResults.map((site, idx) => (
                  <div
                    key={site.id}
                    id={`site-option-${idx}`}
                    role="option"
                    aria-selected={idx === activeIndex}
                    onMouseDown={() => handleSelect(site)}
                    className={[
                      'flex items-center justify-between px-4 py-2.5 cursor-pointer transition-colors',
                      idx === activeIndex ? 'bg-blue-50' : 'hover:bg-apple-gray',
                    ].join(' ')}
                  >
                    <div>
                      <p className="text-sm font-medium text-apple-dark">{site.site_name}</p>
                      <p className="text-xs text-apple-light">{site.customer_name}</p>
                    </div>
                    <span
                      className={[
                        'text-xs px-2 py-0.5 rounded-full font-medium',
                        STATUS_COLOR[site.status ?? ''] ?? 'bg-gray-100 text-gray-500',
                      ].join(' ')}
                    >
                      {STATUS_LABEL[site.status ?? ''] ?? site.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        <div
          className={[
            'mt-6 transition-all duration-200',
            query.length >= 1 ? 'opacity-0 pointer-events-none' : 'opacity-100',
          ].join(' ')}
        >
          {recentSites.length > 0 && (
            <>
              <p className="text-xs text-apple-light mb-2 font-medium tracking-wide">최근 사이트</p>
              <div className="flex flex-wrap gap-2">
                {recentSites.map((site) => (
                  <button
                    key={site.id}
                    onClick={() => navigate(`/sites/${site.id}`)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-apple-divider bg-white text-sm text-apple-dark hover:bg-apple-gray transition-colors"
                  >
                    <span
                      className={[
                        'w-1.5 h-1.5 rounded-full',
                        site.status === 'active' ? 'bg-green-500' :
                        site.status === 'expired' ? 'bg-red-400' :
                        site.status === 'maintenance' ? 'bg-yellow-400' : 'bg-gray-400',
                      ].join(' ')}
                    />
                    {site.site_name}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <button
        onClick={() => navigate('/sites/new')}
        title="새 사이트 등록"
        className="fixed right-8 bottom-8 w-12 h-12 rounded-full bg-blue-600 text-white shadow-lg hover:bg-blue-700 active:scale-95 transition-all flex items-center justify-center z-40"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M10 4v12M4 10h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  )
}
