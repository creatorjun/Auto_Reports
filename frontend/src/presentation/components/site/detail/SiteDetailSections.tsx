// frontend/src/presentation/components/site/detail/SiteDetailSections.tsx
import { useState } from 'react'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import { siteApi } from '@/infrastructure/api/siteApi'
import type { SiteDetail, PatchHistory, VisitHistory } from '@/domain/Site'
import { Section, Row, CredRow, AddBtn, CardActions } from './SiteDetailShared'
import NodeForm from './NodeForm'
import PatchForm from './PatchForm'
import VisitForm from './VisitForm'

export function SiteBasicInfo({ site }: { site: SiteDetail }) {
  return (
    <Section title="기본 정보" defaultOpen>
      <Row label="사이트 ID"   value={site.id} />
      <Row label="사이트명"    value={site.site_name} />
      <Row label="유지보수 업체" value={site.maintenance_company} />
      <Row label="라이센스 유형" value={site.contract_type} />
      <Row label="계약 시작"   value={site.contract_start_date} />
      <Row label="계약 종료"   value={site.contract_end_date} />
      <Row label="등록일"      value={site.created_at?.slice(0, 10)} />
      <Row label="최종수정"    value={site.updated_at?.slice(0, 10)} />
    </Section>
  )
}

export function SiteContactInfo({ site }: { site: SiteDetail }) {
  return (
    <Section title="담당자 정보" defaultOpen={false}>
      {site.customer_info && (
        <>
          <p className="text-xs font-semibold text-apple-light mb-1.5 mt-1">고객사</p>
          <Row label="이름"   value={site.customer_info.name} />
          <Row label="연락처" value={site.customer_info.phone} />
          <Row label="이메일" value={site.customer_info.email} />
        </>
      )}
      {site.maintenance_info && (
        <>
          <p className="text-xs font-semibold text-apple-light mb-1.5 mt-3">유지보수</p>
          <Row label="이름" value={site.maintenance_info.name} />
          <Row label="소속" value={site.maintenance_info.company} />
          <Row label="연락처" value={site.maintenance_info.phone} />
          <Row label="이메일" value={site.maintenance_info.email} />
        </>
      )}
      {!site.customer_info && !site.maintenance_info && (
        <p className="text-sm text-apple-light">등록된 담당자 정보가 없습니다</p>
      )}
    </Section>
  )
}

export function SiteHardwareInfo({ site }: { site: SiteDetail }) {
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [editTarget, setEditTarget] = useState<number | null>(null)
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['site-detail', String(site.id)] })
  const { mutate: deleteNode } = useMutation({
    mutationFn: (nodeId: number) => siteApi.deleteNode(site.id, nodeId),
    onSuccess: invalidate,
  })

  return (
    <Section title="하드웨어" badge={site.nodes?.length ?? 0} defaultOpen={false}>
      <div className="flex justify-end mb-4">
        <AddBtn
          onClick={() => {
            setShowAddForm((v) => !v)
            setEditTarget(null)
          }}
          label="하드웨어 추가"
        />
      </div>
      {showAddForm && editTarget === null && (
        <NodeForm
          siteId={site.id}
          onSuccess={() => {
            invalidate()
            setShowAddForm(false)
          }}
          onCancel={() => setShowAddForm(false)}
        />
      )}
      {!site.nodes || site.nodes.length === 0 ? (
        <p className="text-sm text-apple-light">등록된 하드웨어가 없습니다</p>
      ) : (
        <div className="flex flex-col gap-3">
          {site.nodes.map((node, i) => (
            <div key={node.id ?? i}>
              {editTarget === node.id ? (
                <NodeForm
                  siteId={site.id}
                  initial={node}
                  onSuccess={() => {
                    invalidate()
                    setEditTarget(null)
                  }}
                  onCancel={() => setEditTarget(null)}
                />
              ) : (
                <div className="rounded-xl border border-apple-divider/70 bg-white px-4 py-3 shadow-sm">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-apple-dark">
                        {node.hostname ?? '—'}
                      </span>
                      {node.role && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-medium">
                          {node.role}
                        </span>
                      )}
                    </div>
                    <CardActions
                      onEdit={() => {
                        setEditTarget(node.id ?? null)
                        setShowAddForm(false)
                      }}
                      onDelete={() => node.id && deleteNode(node.id)}
                    />
                  </div>
                  <Row label="IP 주소"       value={node.ip_address} />
                  <Row label="OS"           value={node.os_type} />
                  <Row label="OS 버전"       value={node.os_version} />
                  <Row label="CPU 코어"      value={node.cpu_cores} />
                  <Row label="CPU 스레드"    value={node.cpu_threads} />
                  <Row label="RAM (GB)"     value={node.memory_total_gb} />
                  <Row label="디스크 전체"   value={node.disk_total_gb} />
                  <Row label="디스크 여유"   value={node.disk_free_gb} />
                  <Row label="패키지"        value={node.pkg_version} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}

export function SiteAccessInfo({ site }: { site: SiteDetail }) {
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

export function SitePatchHistory({ site }: { site: SiteDetail }) {
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [editTarget, setEditTarget] = useState<PatchHistory | null>(null)
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['site-detail', String(site.id)] })
  const { mutate: deletePatch } = useMutation({
    mutationFn: (patchId: number) => siteApi.deletePatchHistory(site.id, patchId),
    onSuccess: invalidate,
  })

  return (
    <Section title="패치 히스토리" badge={site.patch_histories.length} defaultOpen={false}>
      <div className="flex justify-end mb-4">
        <AddBtn
          onClick={() => {
            setShowAddForm((v) => !v)
            setEditTarget(null)
          }}
          label="패치 추가"
        />
      </div>
      {showAddForm && !editTarget && (
        <PatchForm
          siteId={site.id}
          onSuccess={() => {
            invalidate()
            setShowAddForm(false)
          }}
          onCancel={() => setShowAddForm(false)}
        />
      )}
      {site.patch_histories.length === 0 ? (
        <p className="text-sm text-apple-light">패치 이력이 없습니다</p>
      ) : (
        <div className="flex flex-col gap-3">
          {[...site.patch_histories].reverse().map((p, i) => (
            <div key={p.id ?? i}>
              {editTarget?.id === p.id ? (
                <PatchForm
                  siteId={site.id}
                  initial={p}
                  onSuccess={() => {
                    invalidate()
                    setEditTarget(null)
                  }}
                  onCancel={() => setEditTarget(null)}
                />
              ) : (
                <div className="rounded-xl border border-apple-divider/70 bg-white px-4 py-3 shadow-sm">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-apple-dark">
                        {p.patch_date ?? '—'}
                      </span>
                      {p.result_status && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-green-50 text-green-700 font-medium">
                          {p.result_status}
                        </span>
                      )}
                    </div>
                    <CardActions
                      onEdit={() => {
                        setEditTarget(p)
                        setShowAddForm(false)
                      }}
                      onDelete={() => p.id && deletePatch(p.id)}
                    />
                  </div>
                  <Row label="패치 유형" value={p.patch_type} />
                  <Row label="적용자"   value={p.applied_by} />
                  <Row label="이슈"     value={p.issue_link} />
                  <Row label="비고"     value={p.note} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}

export function SiteVisitHistory({ site }: { site: SiteDetail }) {
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [editTarget, setEditTarget] = useState<VisitHistory | null>(null)
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['site-detail', String(site.id)] })
  const { mutate: deleteVisit } = useMutation({
    mutationFn: (visitId: number) => siteApi.deleteVisitHistory(site.id, visitId),
    onSuccess: invalidate,
  })

  return (
    <Section title="방문 히스토리" badge={site.visit_histories.length} defaultOpen={false}>
      <div className="flex justify-end mb-4">
        <AddBtn
          onClick={() => {
            setShowAddForm((v) => !v)
            setEditTarget(null)
          }}
          label="방문 추가"
        />
      </div>
      {showAddForm && !editTarget && (
        <VisitForm
          siteId={site.id}
          onSuccess={() => {
            invalidate()
            setShowAddForm(false)
          }}
          onCancel={() => setShowAddForm(false)}
        />
      )}
      {site.visit_histories.length === 0 ? (
        <p className="text-sm text-apple-light">방문 이력이 없습니다</p>
      ) : (
        <div className="flex flex-col gap-3">
          {[...site.visit_histories].reverse().map((v, i) => (
            <div key={v.id ?? i}>
              {editTarget?.id === v.id ? (
                <VisitForm
                  siteId={site.id}
                  initial={v}
                  onSuccess={() => {
                    invalidate()
                    setEditTarget(null)
                  }}
                  onCancel={() => setEditTarget(null)}
                />
              ) : (
                <div className="rounded-xl border border-apple-divider/70 bg-white px-4 py-3 shadow-sm">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-apple-dark">
                        {v.visit_datetime
                          ? v.visit_datetime.replace('T', ' ').slice(0, 16)
                          : '—'}
                      </span>
                    </div>
                    <CardActions
                      onEdit={() => {
                        setEditTarget(v)
                        setShowAddForm(false)
                      }}
                      onDelete={() => v.id && deleteVisit(v.id)}
                    />
                  </div>
                  <Row label="담당자"   value={v.engineer_name} />
                  <Row label="연락처"   value={v.engineer_phone} />
                  <Row label="요청내용" value={v.request_content} />
                  <Row label="조치내용" value={v.action_content} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}
