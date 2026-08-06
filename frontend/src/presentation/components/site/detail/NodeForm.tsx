// frontend/src/presentation/components/site/detail/NodeForm.tsx
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { siteApi } from '@/infrastructure/api/siteApi'
import type { DeploymentNode } from '@/domain/Site'
import { inputCls } from './SiteDetailShared'

const nodeSchema = z.object({
  hostname:        z.string().optional(),
  role:            z.enum(['AllInOne', 'Analyzer', 'Collector', 'Proxy']).optional(),
  ip_address:      z.string().optional(),
  os_type:         z.string().optional(),
  os_version:      z.string().optional(),
  cpu_cores:       z.coerce.number().int().positive().optional().or(z.literal('')),
  cpu_threads:     z.coerce.number().int().positive().optional().or(z.literal('')),
  memory_total_gb: z.coerce.number().int().positive().optional().or(z.literal('')),
  disk_total_gb:   z.coerce.number().int().positive().optional().or(z.literal('')),
  disk_free_gb:    z.coerce.number().int().positive().optional().or(z.literal('')),
  pkg_version:     z.string().optional(),
})
type NodeFormValues = z.infer<typeof nodeSchema>

export default function NodeForm({
  siteId,
  initial,
  onSuccess,
  onCancel,
}: {
  siteId: number
  initial?: DeploymentNode
  onSuccess: () => void
  onCancel: () => void
}) {
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<NodeFormValues>({
    resolver: zodResolver(nodeSchema),
    defaultValues: {
      hostname:        initial?.hostname        ?? '',
      role:            initial?.role            ?? undefined,
      ip_address:      initial?.ip_address      ?? '',
      os_type:         initial?.os_type         ?? '',
      os_version:      initial?.os_version      ?? '',
      cpu_cores:       initial?.cpu_cores       ?? '',
      cpu_threads:     initial?.cpu_threads     ?? '',
      memory_total_gb: initial?.memory_total_gb ?? '',
      disk_total_gb:   initial?.disk_total_gb   ?? '',
      disk_free_gb:    initial?.disk_free_gb    ?? '',
      pkg_version:     initial?.pkg_version     ?? '',
    },
  })

  const { mutateAsync, isError } = useMutation({
    mutationFn: (v: NodeFormValues) => {
      const payload = {
        hostname:        v.hostname        || undefined,
        role:            v.role            || undefined,
        ip_address:      v.ip_address      || undefined,
        os_type:         v.os_type         || undefined,
        os_version:      v.os_version      || undefined,
        cpu_cores:       v.cpu_cores       !== '' ? Number(v.cpu_cores)       : undefined,
        cpu_threads:     v.cpu_threads     !== '' ? Number(v.cpu_threads)     : undefined,
        memory_total_gb: v.memory_total_gb !== '' ? Number(v.memory_total_gb) : undefined,
        disk_total_gb:   v.disk_total_gb   !== '' ? Number(v.disk_total_gb)   : undefined,
        disk_free_gb:    v.disk_free_gb    !== '' ? Number(v.disk_free_gb)    : undefined,
        pkg_version:     v.pkg_version     || undefined,
      }
      return initial?.id
        ? siteApi.updateNode(siteId, initial.id, payload)
        : siteApi.addNode(siteId, payload)
    },
    onSuccess,
  })

  return (
    <form
      onSubmit={handleSubmit((v) => mutateAsync(v))}
      className="mb-4 rounded-2xl border border-blue-200 bg-blue-50/40 px-5 py-4 flex flex-col gap-3"
    >
      <p className="text-xs font-semibold text-blue-700">
        {initial ? '하드웨어 수정' : '새 하드웨어 추가'}
      </p>
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">호스트명</label>
          <input {...register('hostname')} className={inputCls} placeholder="server-01" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">역할</label>
          <select {...register('role')} className={inputCls + ' cursor-pointer'}>
            <option value="">— 선택 —</option>
            <option value="AllInOne">AllInOne</option>
            <option value="Analyzer">Analyzer</option>
            <option value="Collector">Collector</option>
            <option value="Proxy">Proxy</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">IP 주소</label>
          <input {...register('ip_address')} className={inputCls} placeholder="192.168.0.1" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">OS 유형</label>
          <input {...register('os_type')} className={inputCls} placeholder="Oracle Linux" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">OS 버전</label>
          <input {...register('os_version')} className={inputCls} placeholder="22.04" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">CPU 코어</label>
          <input type="number" min={1} {...register('cpu_cores')} className={inputCls} placeholder="8" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">CPU 스레드</label>
          <input type="number" min={1} {...register('cpu_threads')} className={inputCls} placeholder="16" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">RAM (GB)</label>
          <input
            type="number"
            min={1}
            {...register('memory_total_gb')}
            className={inputCls}
            placeholder="32"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">디스크 전체 (GB)</label>
          <input
            type="number"
            min={1}
            {...register('disk_total_gb')}
            className={inputCls}
            placeholder="500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">디스크 여유 (GB)</label>
          <input
            type="number"
            min={0}
            {...register('disk_free_gb')}
            className={inputCls}
            placeholder="120"
          />
        </div>
        <div className="col-span-2 flex flex-col gap-1">
          <label className="text-xs font-medium text-apple-light">패키지</label>
          <input {...register('pkg_version')} className={inputCls} placeholder="v1.0.0" />
        </div>
      </div>
      {isError && <p className="text-xs text-red-500">저장 중 오류가 발생했습니다</p>}
      <div className="flex gap-2 justify-end pt-1">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-1.5 rounded-xl text-xs text-apple-light border border-apple-divider hover:bg-apple-gray transition-colors"
        >
          취소
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-1.5 rounded-xl text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {isSubmitting ? '저장 중...' : '저장'}
        </button>
      </div>
    </form>
  )
}
