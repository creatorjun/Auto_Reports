// frontend/src/presentation/components/site/detail/PatchForm.tsx
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import type { PatchHistory } from '@/domain/Site'
import { inputCls } from './SiteDetailShared'

const patchSchema = z.object({
  patch_date:      z.string().optional(),
  patch_type:      z.enum(['정기패치', '긴급패치', '핫픽스']).optional(),
  applied_by:      z.string().optional(),
  result_status:   z.enum(['성공', '실패', '롤백']).optional(),
  issue_link:      z.string().optional(),
  patch_file_link: z.string().optional(),
  rollback_date:   z.string().optional(),
  note:            z.string().optional(),
})
type PatchFormValues = z.infer<typeof patchSchema>

export default function PatchForm({
  siteId,
  initial,
  onSuccess,
  onCancel,
}: {
  siteId: number
  initial?: PatchHistory
  onSuccess: () => void
  onCancel: () => void
}) {
  const { sites } = useApplicationServices()
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<PatchFormValues>({
    resolver: zodResolver(patchSchema),
    defaultValues: {
      patch_date:      initial?.patch_date      ?? '',
      patch_type:      initial?.patch_type      ?? undefined,
      applied_by:      initial?.applied_by      ?? '',
      result_status:   initial?.result_status   ?? undefined,
      issue_link:      initial?.issue_link      ?? '',
      patch_file_link: initial?.patch_file_link ?? '',
      rollback_date:   initial?.rollback_date   ?? '',
      note:            initial?.note            ?? '',
    },
  })

  const { mutateAsync, isError } = useMutation({
    mutationFn: (v: PatchFormValues) => {
      const payload = {
        patch_date:      v.patch_date      ? v.patch_date      : undefined,
        patch_type:      v.patch_type      ? v.patch_type      : undefined,
        applied_by:      v.applied_by      ? v.applied_by      : undefined,
        result_status:   v.result_status   ? v.result_status   : undefined,
        issue_link:      v.issue_link      ? v.issue_link      : undefined,
        patch_file_link: v.patch_file_link ? v.patch_file_link : undefined,
        rollback_date:   v.rollback_date   ? v.rollback_date   : undefined,
        note:            v.note            ? v.note            : undefined,
      }
      return initial?.id
        ? sites.updatePatchHistory(siteId, initial.id, payload)
        : sites.addPatchHistory(siteId, payload)
    },
    onSuccess,
  })

  return (
    <form
      onSubmit={handleSubmit((v) => mutateAsync(v))}
      className="mb-4 rounded-2xl border border-blue-200 bg-blue-50/40 px-5 py-4 flex flex-col gap-3"
    >
      <p className="text-xs font-semibold text-blue-700">
        {initial ? '패치 수정' : '새 패치 기록'}
      </p>
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
