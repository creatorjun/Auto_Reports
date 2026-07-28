// frontend/src/presentation/pages/SiteDetailPage.tsx
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { siteApi } from '@/infrastructure/api/siteApi'
import type { SiteDetail } from '@/domain/Site'

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

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      className={`transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
    >
      <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function Section({
  title,
  badge,
  defaultOpen = true,
  children,
}: {
  title: string
  badge?: string | number
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-apple-divider rounded-2xl overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 bg-white hover:bg-apple-gray transition-colors"
      >
        <span className="flex items-center gap-2">
          <span className="text-sm font-semibold text-apple-dark">{title}</span>
          {badge !== undefined && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">
              {badge}
            </span>
          )}
        </span>
        <span className="text-apple-light">
          <ChevronIcon open={open} />
        </span>
      </button>

      <div
        className={`transition-all duration-200 overflow-hidden ${
          open ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-5 py-4 border-t border-apple-divider bg-white">
          {children}
        </div>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value?: string | number | null }) {
  if (value === undefined || value === null || value === '') return null
  return (
    <div className="flex gap-3 py-1.5 border-b border-apple-divider/50 last:border-0">
      <span className="w-36 flex-shrink-0 text-xs text-apple-light">{label}</span>
      <span className="text-sm text-apple-dark break-all">{String(value)}</span>
    </div>
  )
}

function CredRow({ label, cred }: { label: string; cred?: { username: string; password: string } | null }) {
  const [show, setShow] = useState(false)
  if (!cred) return null
  return (
    <div className="flex gap-3 py-1.5 border-b border-apple-divider/50 last:border-0 items-start">
      <span className="w-36 flex-shrink-0 text-xs text-apple-light pt-0.5">{label}</span>
      <div className="flex flex-col gap-0.5 text-sm text-apple-dark">
        <span>{cred.username}</span>
        <span className="flex items-center gap-1.5">
          <span className="font-mono text-xs">{show ? cred.password : '•'.repeat(Math.min(cred.password.length, 10))}</span>
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            className="text-[10px] text-blue-500 hover:text-blue-700 transition-colors"
          >
            {show ? '숨기기' : '보기'}
          </button>
        </span>
      </div>
    </div>
  )
}

function SiteBasicInfo({ site }: { site: SiteDetail }) {
  return (
    <Section title="기본 정보" defaultOpen>
      <Row label="사이트 ID" value={site.id} />
      <Row label="사이트명" value={site.site_name} />
      <Row label="유지보수 업체" value={site.maintenance_company} />
      <Row label="계약 유형" value={site.contract_type} />
      <Row label="계약 시작" value={site.contract_start_date} />
      <Row label="계약 종료" value={site.contract_end_date} />
      <Row label="등록일" value={site.created_at?.slice(0, 10)} />
      <Row label="최종수정" value={site.updated_at?.slice(0, 10)} />
    </Section>
  )
}

function SiteContactInfo({ site }: { site: SiteDetail }) {
  return (
    <Section title="담당자 정보" defaultOpen={false}>
      {site.customer_info && (
        <>
          <p className="text-xs font-semibold text-apple-light mb-1.5 mt-1">고객사</p>
          <Row label="이름" value={site.customer_info.name} />
          <Row label="연락처" value={site.customer_info.phone} />
          <Row label="이메일" value={site.customer_info.email} />
        </>
      )}
      {site.maintenance_info && (
        <>
          <p className="text-xs font-semibold text-apple-light mb-1.5 mt-3">유지보수담당</p>
          <Row label="이름" value={site.maintenance_info.name} />
          <Row label="연락처" value={site.maintenance_info.phone} />
          <Row label="이메일" value={site.maintenance_info.email} />
        </>
      )}
      {!site.customer_info && !site.maintenance_info && (
        <p className="text-sm text-apple-light">입력된 정보가 없습니다</p>
      )}
    </Section>
  )
}

function SiteHardwareInfo({ site }: { site: SiteDetail }) {
  return (
    <Section title="하드웨어 정보" badge={site.nodes.length} defaultOpen={false}>
      {site.nodes.length === 0 ? (
        <p className="text-sm text-apple-light">등록된 노드가 없습니다</p>
      ) : (
        <div className="flex flex-col gap-4">
          {site.nodes.map((node, i) => (
            <div key={node.id ?? i} className="rounded-xl border border-apple-divider/70 px-4 py-3">
              <p className="text-xs font-semibold text-blue-600 mb-2">
                {node.role ?? '—'} {node.hostname ? `— ${node.hostname}` : ''}
              </p>
              <Row label="IP 주소" value={node.ip_address} />
              <Row label="CPU" value={node.cpu_cores != null ? `${node.cpu_cores}코어 / ${node.cpu_threads}스레드` : undefined} />
              <Row label="메모리" value={node.memory_total_gb != null ? `${node.memory_total_gb} GB` : undefined} />
              <Row label="디스크 (전체)" value={node.disk_total_gb != null ? `${node.disk_total_gb} GB` : undefined} />
              <Row label="디스크 (여유)" value={node.disk_free_gb != null ? `${node.disk_free_gb} GB` : undefined} />
              <Row label="OS" value={node.os_type && node.os_version ? `${node.os_type} ${node.os_version}` : (node.os_type ?? node.os_version)} />
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}

function SiteSolutionInfo({ site }: { site: SiteDetail }) {
  const pkg = site.solution_package
  return (
    <Section title="소루션 패키지" defaultOpen={false}>
      {!pkg ? (
        <p className="text-sm text-apple-light">등록된 소루션 정보가 없습니다</p>
      ) : (
        <>
          <Row label="버전" value={pkg.version} />
          <Row label="인스톨러" value={pkg.installer_filename} />
          <Row label="배포 유형" value={pkg.deployment_type} />
          <Row label="라이선스 용량" value={pkg.license_capacity_gb != null ? `${pkg.license_capacity_gb} GB` : undefined} />
          <Row label="라이선스 키" value={pkg.license_key} />
          <Row label="라이선스 만료" value={pkg.license_expire_date} />
          <Row label="설치일" value={pkg.installed_at?.slice(0, 10)} />
        </>
      )}
    </Section>
  )
}

function SiteAccessInfo({ site }: { site: SiteDetail }) {
  const creds = site.access_credentials
  return (
    <Section title="접속 정보" defaultOpen={false}>
      {!creds ? (
        <p className="text-sm text-apple-light">등록된 접속 정보가 없습니다</p>
      ) : (
        <>
          <CredRow label="CLI" cred={creds.cli} />
          <CredRow label="WEB" cred={creds.web} />
          <CredRow label="DB"  cred={creds.db} />
          <CredRow label="VPN" cred={creds.vpn} />
          {creds.note && (
            <div className="mt-3 rounded-xl bg-apple-gray/60 px-4 py-3 text-sm text-apple-dark whitespace-pre-wrap">
              {creds.note}
            </div>
          )}
          {!creds.cli && !creds.web && !creds.db && !creds.vpn && !creds.note && (
            <p className="text-sm text-apple-light">입력된 접속 정보가 없습니다</p>
          )}
        </>
      )}
    </Section>
  )
}

function SitePatchHistory({ site }: { site: SiteDetail }) {
  return (
    <Section title="패치 히스토리" badge={site.patch_histories.length} defaultOpen={false}>
      {site.patch_histories.length === 0 ? (
        <p className="text-sm text-apple-light">패치 이력이 없습니다</p>
      ) : (
        <div className="flex flex-col gap-3">
          {[...site.patch_histories].reverse().map((p, i) => (
            <div key={p.id ?? i} className="rounded-xl border border-apple-divider/70 px-4 py-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-apple-dark">{p.patch_date ?? '—'}</span>
                {p.result_status && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    p.result_status === '성공' ? 'bg-green-100 text-green-700' :
                    p.result_status === '실패' ? 'bg-red-100 text-red-600' :
                    'bg-yellow-100 text-yellow-700'
                  }`}>
                    {p.result_status}
                  </span>
                )}
              </div>
              <Row label="패치 유형" value={p.patch_type} />
              <Row label="적용자" value={p.applied_by} />
              <Row label="이슈링크" value={p.issue_link} />
              <Row label="패치파일" value={p.patch_file_link} />
              <Row label="롤백일" value={p.rollback_date} />
              <Row label="비고" value={p.note} />
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}

function SiteVisitHistory({ site }: { site: SiteDetail }) {
  return (
    <Section title="방문 히스토리" badge={site.visit_histories.length} defaultOpen={false}>
      {site.visit_histories.length === 0 ? (
        <p className="text-sm text-apple-light">방문 이력이 없습니다</p>
      ) : (
        <div className="flex flex-col gap-3">
          {[...site.visit_histories].reverse().map((v, i) => (
            <div key={v.id ?? i} className="rounded-xl border border-apple-divider/70 px-4 py-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-apple-dark">{v.visit_date ?? '—'}</span>
                {v.visit_type && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">
                    {v.visit_type}
                  </span>
                )}
              </div>
              <Row label="방문자" value={v.visitor} />
              <Row label="내용" value={v.visit_summary} />
              <Row label="다음 방문" value={v.next_visit_scheduled} />
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}

export default function SiteDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: site, isLoading, isError } = useQuery({
    queryKey: ['site-detail', id],
    queryFn: () => siteApi.getById(id!),
    enabled: !!id,
    staleTime: 30_000,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center w-full h-full py-20">
        <span className="text-sm text-apple-light">로딩 중...</span>
      </div>
    )
  }

  if (isError || !site) {
    return (
      <div className="flex flex-col items-center justify-center w-full h-full py-20 gap-3">
        <p className="text-sm text-red-500">사이트 정보를 불러오지 못했습니다</p>
        <button
          onClick={() => navigate('/sites')}
          className="text-sm text-blue-600 hover:underline"
        >
          목록으로 돌아가기
        </button>
      </div>
    )
  }

  return (
    <div className="w-full max-w-2xl mx-auto px-6 py-10">
      <div className="flex items-center gap-3 mb-6">
        <button
          type="button"
          onClick={() => navigate('/sites')}
          className="text-apple-light hover:text-apple-dark transition-colors"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M11 4L6 9l5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-apple-dark truncate">{site.site_name}</h1>
          {site.maintenance_company && (
            <p className="text-xs text-apple-light mt-0.5">{site.maintenance_company}</p>
          )}
        </div>
        {site.status && (
          <span
            className={`text-xs px-2.5 py-1 rounded-full font-medium flex-shrink-0 ${
              STATUS_COLOR[site.status] ?? 'bg-gray-100 text-gray-500'
            }`}
          >
            {STATUS_LABEL[site.status] ?? site.status}
          </span>
        )}
      </div>

      <div className="flex flex-col gap-3">
        <SiteBasicInfo      site={site} />
        <SiteContactInfo    site={site} />
        <SiteHardwareInfo   site={site} />
        <SiteSolutionInfo   site={site} />
        <SiteAccessInfo     site={site} />
        <SitePatchHistory   site={site} />
        <SiteVisitHistory   site={site} />
      </div>
    </div>
  )
}
