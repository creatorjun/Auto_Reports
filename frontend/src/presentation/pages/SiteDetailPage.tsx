// frontend/src/presentation/pages/SiteDetailPage.tsx
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { siteApi } from '@/infrastructure/api/siteApi'
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
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: site, isLoading, isError } = useQuery({
    queryKey: ['site-detail', id],
    queryFn: () => siteApi.getById(id!),
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
    <div className="w-full max-w-2xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate('/sites')}
            className="text-apple-light hover:text-apple-dark transition-colors"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path
                d="M11 4L6 9l5 5"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-semibold text-apple-dark">{site.site_name}</h1>
            {site.status && (
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-medium ${
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
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium border border-apple-divider text-apple-dark hover:bg-apple-gray hover:border-blue-300 hover:text-blue-600 transition-colors"
        >
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
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

      <div className="flex flex-col gap-3">
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
