// frontend/src/presentation/pages/SiteDetailPage.tsx
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { siteApi } from '@/infrastructure/api/siteApi'
import type { SiteDetail, PatchHistory, VisitHistory } from '@/domain/Site'

const STATUS_LABEL: Record<string, string> = {
  installing: '구축중',
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

const inputCls = 'w-full border border-apple-divider rounded-xl px-3 py-2 text-sm text-apple-dark bg-white outline-none focus:ring-2 focus:ring-blue-500/30 transition'

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"
      className={`transition-transform duration-200 ${open ? 'rotate-180' : ''}`}>
      <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function Section({ title, badge, defaultOpen = true, children }: {
  title: string; badge?: string | number; defaultOpen?: boolean; children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-apple-divider rounded-2xl overflow-hidden">
      <button type="button" onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 bg-white hover:bg-apple-gray transition-colors">
        <span className="flex items-center gap-2">
          <span className="text-sm font-semibold text-apple-dark">{title}</span>
          {badge !== undefined && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">{badge}</span>
          )}
        </span>
        <span className="text-apple-light"><ChevronIcon open={open} /></span>
      </button>
      <div className={`transition-all duration-200 overflow-hidden ${open ? 'max-h-[6000px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className="px-5 py-4 border-t border-apple-divider bg-white">{children}</div>
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

function CredRow({ label, cred }: {
  label: string
  cred?: { username: string; password: string; ip?: string; port?: string } | null
}) {
  const [show, setShow] = useState(false)
  if (!cred) return null
  return (
    <div className="flex gap-3 py-1.5 border-b border-apple-divider/50 last:border-0 items-start">
      <span className="w-36 flex-shrink-0 text-xs text-apple-light pt-0.5">{label}</span>
      <div className="flex flex-col gap-0.5 text-sm text-apple-dark">
        <span>{cred.username}</span>
        <span className="flex items-center gap-1.5">
          <span className="font-mono text-xs">{show ? cred.password : '•'.repeat(Math.min(cred.password.length, 10))}</span>
          <button type="button" onClick={() => setShow(v => !v)}
            className="text-[10px] text-blue-500 hover:text-blue-700 transition-colors">
            {show ? '숨기기' : '보기'}
          </button>
        </span>
        {cred.ip && (
          <span className="text-xs text-apple-light">
            {cred.ip}{cred.port ? `:${cred.port}` : ''}
          </span>
        )}
      </div>
    </div>
  )
}

function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 11)
  if (digits.length < 4) return digits
  if (digits.length < 7) return `${digits.slice(0, 3)}-${digits.slice(3)}`
  if (digits.length < 11) return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`
  return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`
}

function AddBtn({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button type="button" onClick={onClick}
      className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors">
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
        <path d="M6 1v10M1 6h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
      {label}
    </button>
  )
}

function CardActions({ onEdit, onDelete }: { onEdit: () => void; onDelete: () => void }) {
  return (
    <div className="flex gap-1.5">
      <button type="button" onClick={onEdit}
        className="text-xs px-2.5 py-1 rounded-lg border border-apple-divider text-apple-light hover:text-blue-600 hover:border-blue-300 transition-colors">
        수정
      </button>
      <button type="button" onClick={onDelete}
        className="text-xs px-2.5 py-1 rounded-lg border border-apple-divider text-apple-light hover:text-red-500 hover:border-red-300 transition-colors">
        삭제
      </button>
    </div>
  )
}

const patchSchema = z.object({
  patch_date:      z.string().optional(),
  patch_type:      z.string().optional(),
  applied_by:      z.string().optional(),
  result_status:   z.string().optional(),
  issue_link:      z.string().optional(),
  patch_file_link: z.string().optional(),
  rollback_date:   z.string().optional(),
  note:            z.string().optional(),
})
type PatchFormValues = z.infer<typeof patchSchema>

const visitSchema = z.object({
  visit_datetime:  z.string().min(1, '방문일시를 입력하세요'),
  engineer_name:   z.string().optional(),
  engineer_phone:  z.string().optional(),
  request_content: z.string().optional(),
  action_content:  z.string().optional(),
})
type VisitFormValues = z.infer<typeof visitSchema>

function PatchForm({
  siteId, initial, onSuccess, onCancel,
}: {
  siteId: number; initial?: PatchHistory; onSuccess: () => void; onCancel: () => void
}) {
  const { register, handleSubmit, formState: { isSubmitting } } = useForm<PatchFormValues>({
    resolver: zodResolver(patchSchema),
    defaultValues: {
      patch_date:      initial?.patch_date      ?? '',
      patch_type:      initial?.patch_type      ?? '',
      applied_by:      initial?.applied_by      ?? '',
      result_status:   initial?.result_status   ?? '',
      issue_link:      initial?.issue_link      ?? '',
      patch_file_link: initial?.patch_file_link ?? '',
      rollback_date:   initial?.rollback_date   ?? '',
      note:            initial?.note            ?? '',
    },
  })

  const { mutateAsync, isError } = useMutation({
    mutationFn: (v: PatchFormValues) => {
      const payload = {
        patch_date:      v.patch_date      || undefined,
        patch_type:      v.patch_type      || undefined,
        applied_by:      v.applied_by      || undefined,
        result_status:   v.result_status   || undefined,
        issue_link:      v.issue_link      || undefined,
        patch_file_link: v.patch_file_link || undefined,
        rollback_date:   v.rollback_date   || undefined,
        note:            v.note            || undefined,
      }
      return initial?.id
        ? siteApi.updatePatchHistory(siteId, initial.id, payload)
        : siteApi.addPatchHistory(siteId, payload)
    },
    onSuccess,
  })

  return (
    <form onSubmit={handleSubmit(v => mutateAsync(v))}
      className="mb-4 rounded-2xl border border-blue-200 bg-blue-50/40 px-5 py-4 flex flex-col gap-3">
      <p className="text-xs font-semibold text-blue-700">{initial ? '패치 수정' : '새 패치 기록'}</p>
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">패치일</label>
          <input type="date" {...register('patch_date')} className={inputCls} />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">패치 유형</label>
          <select {...register('patch_type')} className={inputCls + ' cursor-pointer'}>
            <option value="">— 선택 —</option>
            <option value="정기패치">정기패치</option>
            <option value="긴급패치">긴급패치</option>
            <option value="핫픽스">핫픽스</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">적용자</label>
          <input {...register('applied_by')} className={inputCls} placeholder="담당자명" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">결과</label>
          <select {...register('result_status')} className={inputCls + ' cursor-pointer'}>
            <option value="">— 선택 —</option>
            <option value="성공">성공</option>
            <option value="실패">실패</option>
            <option value="롤백">롤백</option>
          </select>
        </div>
        <div className="col-span-2 flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">이슈 링크</label>
          <input {...register('issue_link')} className={inputCls} placeholder="https://..." />
        </div>
        <div className="col-span-2 flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">패치파일 링크</label>
          <input {...register('patch_file_link')} className={inputCls} placeholder="https://..." />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">롤백일</label>
          <input type="date" {...register('rollback_date')} className={inputCls} />
        </div>
        <div className="col-span-2 flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">비고</label>
          <textarea {...register('note')} className={inputCls + ' resize-none'} rows={2} />
        </div>
      </div>
      {isError && <p className="text-xs text-red-500">저장 중 오류가 발생했습니다</p>}
      <div className="flex gap-2 justify-end pt-1">
        <button type="button" onClick={onCancel}
          className="px-4 py-1.5 rounded-xl text-xs text-apple-light border border-apple-divider hover:bg-apple-gray transition-colors">
          취소
        </button>
        <button type="submit" disabled={isSubmitting}
          className="px-4 py-1.5 rounded-xl text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors">
          {isSubmitting ? '저장 중...' : '저장'}
        </button>
      </div>
    </form>
  )
}

function VisitForm({
  siteId, initial, onSuccess, onCancel,
}: {
  siteId: number; initial?: VisitHistory; onSuccess: () => void; onCancel: () => void
}) {
  const { register, handleSubmit, setValue, formState: { errors, isSubmitting } } = useForm<VisitFormValues>({
    resolver: zodResolver(visitSchema),
    defaultValues: {
      visit_datetime:  initial?.visit_datetime  ?? new Date().toISOString().slice(0, 16),
      engineer_name:   initial?.engineer_name   ?? '',
      engineer_phone:  initial?.engineer_phone  ?? '',
      request_content: initial?.request_content ?? '',
      action_content:  initial?.action_content  ?? '',
    },
  })

  const { mutateAsync, isError } = useMutation({
    mutationFn: (v: VisitFormValues) => {
      const payload = {
        visit_datetime:  v.visit_datetime  || undefined,
        engineer_name:   v.engineer_name   || undefined,
        engineer_phone:  v.engineer_phone  || undefined,
        request_content: v.request_content || undefined,
        action_content:  v.action_content  || undefined,
      }
      return initial?.id
        ? siteApi.updateVisitHistory(siteId, initial.id, payload)
        : siteApi.addVisitHistory(siteId, payload)
    },
    onSuccess,
  })

  return (
    <form onSubmit={handleSubmit(v => mutateAsync(v))}
      className="mb-4 rounded-2xl border border-blue-200 bg-blue-50/40 px-5 py-4 flex flex-col gap-3">
      <p className="text-xs font-semibold text-blue-700">{initial ? '방문 수정' : '새 방문 기록'}</p>
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2 flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">방문일시 *</label>
          <input type="datetime-local" {...register('visit_datetime')} className={inputCls} />
          {errors.visit_datetime && <p className="text-xs text-red-500">{errors.visit_datetime.message}</p>}
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">담당자</label>
          <input {...register('engineer_name')} className={inputCls} placeholder="담당자명" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">연락처</label>
          <input className={inputCls} placeholder="010-0000-0000" inputMode="numeric"
            {...register('engineer_phone')}
            onChange={e => setValue('engineer_phone', formatPhone(e.target.value), { shouldValidate: true })} />
        </div>
        <div className="col-span-2 flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">요청내용</label>
          <textarea {...register('request_content')} className={inputCls + ' resize-none'} rows={2}
            placeholder="고객 요청 사항" />
        </div>
        <div className="col-span-2 flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">조치내용</label>
          <textarea {...register('action_content')} className={inputCls + ' resize-none'} rows={2}
            placeholder="처리 및 조치 내용" />
        </div>
      </div>
      {isError && <p className="text-xs text-red-500">저장 중 오류가 발생했습니다</p>}
      <div className="flex gap-2 justify-end pt-1">
        <button type="button" onClick={onCancel}
          className="px-4 py-1.5 rounded-xl text-xs text-apple-light border border-apple-divider hover:bg-apple-gray transition-colors">
          취소
        </button>
        <button type="submit" disabled={isSubmitting}
          className="px-4 py-1.5 rounded-xl text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors">
          {isSubmitting ? '저장 중...' : '저장'}
        </button>
      </div>
    </form>
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
            <div className="mt-3 rounded-xl bg-apple-gray/60 px-4 py-3 text-sm text-apple-dark whitespace-pre-wrap">{creds.note}</div>
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
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [editTarget, setEditTarget] = useState<PatchHistory | null>(null)

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['site-detail', String(site.id)] })

  const { mutate: deletePatch } = useMutation({
    mutationFn: (patchId: number) => siteApi.deletePatchHistory(site.id, patchId),
    onSuccess: invalidate,
  })

  return (
    <Section title="패치 히스토리" badge={site.patch_histories.length} defaultOpen={false}>
      <div className="flex justify-end mb-4">
        <AddBtn onClick={() => { setShowAddForm(v => !v); setEditTarget(null) }} label="패치 추가" />
      </div>
      {showAddForm && !editTarget && (
        <PatchForm siteId={site.id}
          onSuccess={() => { invalidate(); setShowAddForm(false) }}
          onCancel={() => setShowAddForm(false)} />
      )}
      {site.patch_histories.length === 0 ? (
        <p className="text-sm text-apple-light">패치 이력이 없습니다</p>
      ) : (
        <div className="flex flex-col gap-3">
          {[...site.patch_histories].reverse().map((p, i) => (
            <div key={p.id ?? i}>
              {editTarget?.id === p.id ? (
                <PatchForm siteId={site.id} initial={p}
                  onSuccess={() => { invalidate(); setEditTarget(null) }}
                  onCancel={() => setEditTarget(null)} />
              ) : (
                <div className="rounded-xl border border-apple-divider/70 bg-white px-4 py-3 shadow-sm">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-apple-dark">{p.patch_date ?? '—'}</span>
                      {p.result_status && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-green-50 text-green-700 font-medium">{p.result_status}</span>
                      )}
                    </div>
                    <CardActions
                      onEdit={() => { setEditTarget(p); setShowAddForm(false) }}
                      onDelete={() => p.id && deletePatch(p.id)}
                    />
                  </div>
                  <Row label="패치 유형" value={p.patch_type} />
                  <Row label="적용자" value={p.applied_by} />
                  <Row label="이슈" value={p.issue_link} />
                  <Row label="비고" value={p.note} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}

function SiteVisitHistory({ site }: { site: SiteDetail }) {
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [editTarget, setEditTarget] = useState<VisitHistory | null>(null)

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['site-detail', String(site.id)] })

  const { mutate: deleteVisit } = useMutation({
    mutationFn: (visitId: number) => siteApi.deleteVisitHistory(site.id, visitId),
    onSuccess: invalidate,
  })

  return (
    <Section title="방문 히스토리" badge={site.visit_histories.length} defaultOpen={false}>
      <div className="flex justify-end mb-4">
        <AddBtn onClick={() => { setShowAddForm(v => !v); setEditTarget(null) }} label="방문 추가" />
      </div>
      {showAddForm && !editTarget && (
        <VisitForm siteId={site.id}
          onSuccess={() => { invalidate(); setShowAddForm(false) }}
          onCancel={() => setShowAddForm(false)} />
      )}
      {site.visit_histories.length === 0 ? (
        <p className="text-sm text-apple-light">방문 이력이 없습니다</p>
      ) : (
        <div className="flex flex-col gap-3">
          {[...site.visit_histories].reverse().map((v, i) => (
            <div key={v.id ?? i}>
              {editTarget?.id === v.id ? (
                <VisitForm siteId={site.id} initial={v}
                  onSuccess={() => { invalidate(); setEditTarget(null) }}
                  onCancel={() => setEditTarget(null)} />
              ) : (
                <div className="rounded-xl border border-apple-divider/70 bg-white px-4 py-3 shadow-sm">
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-xs font-semibold text-apple-dark">
                      {v.visit_datetime?.slice(0, 16).replace('T', ' ') ?? '—'}
                    </span>
                    <CardActions
                      onEdit={() => { setEditTarget(v); setShowAddForm(false) }}
                      onDelete={() => v.id && deleteVisit(v.id)}
                    />
                  </div>
                  <Row label="담당자" value={v.engineer_name} />
                  <Row label="연락처" value={v.engineer_phone} />
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
        <button onClick={() => navigate('/sites')}
          className="text-xs text-blue-600 hover:underline">목록으로 돌아가기</button>
      </div>
    )
  }

  return (
    <div className="w-full max-w-2xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <button type="button" onClick={() => navigate('/sites')}
            className="text-apple-light hover:text-apple-dark transition-colors">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M11 4L6 9l5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-semibold text-apple-dark">{site.site_name}</h1>
            {site.status && (
              <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                STATUS_COLOR[site.status] ?? 'bg-gray-100 text-gray-500'
              }`}>
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
            <path d="M9.5 1.5a1.414 1.414 0 0 1 2 2L4 11H1.5V8.5L9.5 1.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          수정
        </button>
      </div>

      <div className="flex flex-col gap-3">
        <SiteBasicInfo site={site} />
        <SiteContactInfo site={site} />
        <SiteHardwareInfo site={site} />
        <SiteSolutionInfo site={site} />
        <SiteAccessInfo site={site} />
        <SitePatchHistory site={site} />
        <SiteVisitHistory site={site} />
      </div>
    </div>
  )
}
