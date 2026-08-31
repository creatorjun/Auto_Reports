// frontend/src/presentation/pages/SiteManagementPage.tsx
import { useRef, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import type { SiteSummary } from '@/domain/Site'

const STATUS_LABEL: Record<string, string> = {
  installing: '설치 중',
  active: '운영 중',
  inactive: '비활성',
  expired: '만료',
  maintenance: '유지보수',
}

const STATUS_COLOR: Record<string, string> = {
  installing: 'bg-blue-100 text-blue-700',
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
    <div className="relative mx-auto flex min-h-full w-full max-w-content flex-col 3xl:max-w-none">
      <div className="mb-5 flex items-start justify-between gap-4 sm:mb-6 3xl:mb-8">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-apple-dark sm:text-2xl 3xl:text-3xl">사이트 관리</h1>
          <p className="mt-1 text-sm text-apple-light 3xl:text-base">사이트를 검색하거나 최근 업데이트된 사이트로 바로 이동할 수 있습니다.</p>
        </div>
        <button
          type="button"
          onClick={() => navigate('/sites/new')}
          aria-label="새 사이트 등록"
          className="inline-flex h-10 flex-shrink-0 items-center justify-center gap-2 rounded-xl bg-blue-600 px-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30 sm:px-4 xl:hidden"
        >
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d="M10 4v12M4 10h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <span className="hidden sm:inline">새 사이트 등록</span>
        </button>
      </div>

      <section className="rounded-2xl border border-apple-divider/80 bg-white p-4 shadow-sm sm:p-6 3xl:rounded-3xl 3xl:p-8">
        <div className="relative">
          <div className="flex min-h-12 items-center gap-3 rounded-2xl border border-apple-divider bg-apple-gray/40 px-4 py-3 transition focus-within:border-blue-400 focus-within:bg-white focus-within:ring-2 focus-within:ring-blue-500/20 sm:px-5 sm:py-3.5 3xl:min-h-16 3xl:px-6">
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none" className="flex-shrink-0 text-apple-light 3xl:h-5 3xl:w-5">
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
              aria-label="사이트명 검색"
              className="min-w-0 flex-1 bg-transparent text-sm text-apple-dark outline-none placeholder:text-apple-light sm:text-base 3xl:text-lg"
              aria-autocomplete="list"
              aria-expanded={dropdownOpen}
              aria-activedescendant={activeIndex >= 0 ? `site-option-${activeIndex}` : undefined}
              role="combobox"
            />
            {query && (
              <button
                type="button"
                onMouseDown={(e) => { e.preventDefault(); setQuery('') }}
                aria-label="검색어 지우기"
                className="rounded-full p-1 text-apple-light transition-colors hover:bg-apple-gray hover:text-apple-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30"
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
              className="absolute left-0 right-0 top-full z-50 mt-2 max-h-[60vh] overflow-y-auto rounded-2xl border border-apple-divider bg-white shadow-apple-lg"
            >
              {isSearching ? (
                <div className="px-4 py-4 text-sm text-apple-light sm:px-5">검색 중...</div>
              ) : searchResults.length === 0 ? (
                <div className="px-4 py-4 text-sm text-apple-light sm:px-5">검색 결과가 없습니다</div>
              ) : (
                searchResults.map((site, idx) => (
                  <div
                    key={site.id}
                    id={`site-option-${idx}`}
                    role="option"
                    aria-selected={idx === activeIndex}
                    onMouseDown={() => handleSelect(site)}
                    className={[
                      'flex cursor-pointer items-center justify-between gap-3 px-4 py-3 transition-colors sm:px-5 3xl:py-4',
                      idx === activeIndex ? 'bg-blue-50' : 'hover:bg-apple-gray',
                    ].join(' ')}
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-apple-dark sm:text-base">{site.site_name}</p>
                      {site.customer_name && (
                        <p className="mt-0.5 truncate text-xs text-apple-light sm:text-sm">{site.customer_name}</p>
                      )}
                    </div>
                    <span
                      className={[
                        'flex-shrink-0 rounded-full px-2.5 py-1 text-xs font-medium',
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
      </section>

      <section
        className={[
          'mt-6 transition-all duration-200 3xl:mt-8',
          query.length >= 1 ? 'pointer-events-none opacity-0' : 'opacity-100',
        ].join(' ')}
      >
        {recentSites.length > 0 && (
          <>
            <div className="mb-3 flex items-center justify-between sm:mb-4">
              <h2 className="text-sm font-semibold text-apple-dark sm:text-base 3xl:text-lg">최근 사이트</h2>
              <span className="text-xs text-apple-light">{recentSites.length}개</span>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 3xl:grid-cols-5 3xl:gap-5">
              {recentSites.map((site) => (
                <button
                  key={site.id}
                  type="button"
                  onClick={() => navigate(`/sites/${site.id}`)}
                  aria-label={`${site.site_name} 사이트 열기`}
                  className="group flex min-w-0 items-center justify-between gap-3 rounded-2xl border border-apple-divider bg-white px-4 py-4 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-apple focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30 sm:px-5 3xl:min-h-24 3xl:rounded-3xl 3xl:px-6"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-apple-dark transition-colors group-hover:text-blue-700 sm:text-base">
                      {site.site_name}
                    </p>
                    {site.customer_name && (
                      <p className="mt-1 truncate text-xs text-apple-light sm:text-sm">{site.customer_name}</p>
                    )}
                  </div>
                  <span
                    className={[
                      'flex-shrink-0 rounded-full px-2.5 py-1 text-xs font-medium',
                      STATUS_COLOR[site.status ?? ''] ?? 'bg-gray-100 text-gray-500',
                    ].join(' ')}
                  >
                    {STATUS_LABEL[site.status ?? ''] ?? site.status}
                  </span>
                </button>
              ))}
            </div>
          </>
        )}
      </section>

      <button
        type="button"
        onClick={() => navigate('/sites/new')}
        title="새 사이트 등록"
        aria-label="새 사이트 등록"
        className="fixed z-40 hidden h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg transition-all hover:bg-blue-700 active:scale-95 xl:bottom-8 xl:right-8 xl:flex 3xl:right-12"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M10 4v12M4 10h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  )
}
