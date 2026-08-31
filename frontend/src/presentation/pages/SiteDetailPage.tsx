// frontend/src/presentation/pages/SiteDetailPage.tsx
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { STATUS_LABEL, STATUS_COLOR } from '@/presentation/components/site/detail/SiteDetailShared'
import {
  SiteBasicInfo,
  SiteContactInfo,
  SiteHardwareInfo,
  SiteAccessInfo,
  SitePatchHistory,
  SiteVisitHistory,
} from '@/presentation/components/site/detail/SiteDetailSections'

export default function SiteDetailPage() {
  const { sites } = useApplicationServices()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: site, isLoading, isError } = useQuery({
    queryKey: ['site-detail', id],
    queryFn: () => sites.getById(id!),
    enabled: !!id,
    retry: 1,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-sm text-apple-light">불러오는 중...</span>
      </div>
    )
  }

  if (isError || !site) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-sm text-apple-light">사이트 정보를 불러오지 못했습니다</p>
        <button
          onClick={() => navigate('/sites')}
          className="text-xs text-blue-600 hover:underline"
        >
          목록으로 돌아가기
        </button>
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-content 3xl:max-w-none">
      <div className="mb-6 flex flex-col gap-4 sm:mb-8 sm:flex-row sm:items-center sm:justify-between 3xl:mb-10">
        <div className="flex min-w-0 items-start gap-3 sm:items-center">
          <button
            type="button"
            onClick={() => navigate('/sites')}
            aria-label="사이트 목록으로 돌아가기"
            className="mt-1 flex-shrink-0 rounded-full p-1 text-apple-light transition-colors hover:bg-apple-gray hover:text-apple-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30 sm:mt-0"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
              <path
                d="M11 4L6 9l5 5"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
          <div className="flex min-w-0 flex-wrap items-center gap-2.5">
            <h1 className="min-w-0 break-words text-xl font-semibold text-apple-dark sm:text-2xl 3xl:text-3xl">
              {site.site_name}
            </h1>
            {site.status && (
              <span
                className={`flex-shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${
                  STATUS_COLOR[site.status] ?? 'bg-gray-100 text-gray-500'
                }`}
              >
                {STATUS_LABEL[site.status] ?? site.status}
              </span>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={() => navigate(`/sites/${id}/edit`)}
          className="flex w-full flex-shrink-0 items-center justify-center gap-1.5 rounded-xl border border-apple-divider px-4 py-2.5 text-sm font-medium text-apple-dark transition-colors hover:border-blue-300 hover:bg-apple-gray hover:text-blue-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30 sm:w-auto sm:py-2 sm:text-xs"
        >
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
            <path
              d="M9.5 1.5a1.414 1.414 0 0 1 2 2L4 11H1.5V8.5L9.5 1.5Z"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          수정
        </button>
      </div>

      <div className="flex flex-col gap-3 sm:gap-4 3xl:gap-5">
        <SiteBasicInfo    site={site} />
        <SiteContactInfo  site={site} />
        <SiteHardwareInfo site={site} />
        <SiteAccessInfo   site={site} />
        <SitePatchHistory site={site} />
        <SiteVisitHistory site={site} />
      </div>
    </div>
  )
}
