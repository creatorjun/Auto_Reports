// frontend/src/presentation/components/site/detail/VisitForm.tsx
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import type { VisitHistory } from '@/domain/Site'
import { inputCls, formatPhone } from './SiteDetailShared'

const visitSchema = z.object({
  visit_datetime:  z.string().min(1, '방문일시를 입력하세요'),
  engineer_name:   z.string().optional(),
  engineer_phone:  z.string().optional(),
  request_content: z.string().optional(),
  action_content:  z.string().optional(),
})
type VisitFormValues = z.infer<typeof visitSchema>

export default function VisitForm({
  siteId,
  initial,
  onSuccess,
  onCancel,
}: {
  siteId: number
  initial?: VisitHistory
  onSuccess: () => void
  onCancel: () => void
}) {
  const { sites } = useApplicationServices()
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<VisitFormValues>({
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
        ? sites.updateVisitHistory(siteId, initial.id, payload)
        : sites.addVisitHistory(siteId, payload)
    },
    onSuccess,
  })

  return (
    <form
      onSubmit={handleSubmit((v) => mutateAsync(v))}
      className="mb-4 flex flex-col gap-3 rounded-2xl border border-blue-200 bg-blue-50/40 px-4 py-4 sm:px-5 3xl:p-6"
    >
      <p className="text-xs font-semibold text-blue-700">
        {initial ? '방문 수정' : '새 방문 기록'}
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4 3xl:gap-4">
        <div className="flex flex-col gap-1 sm:col-span-2 xl:col-span-4">
          <label className="text-xs font-medium text-apple-light">방문일시 *</label>
          <input type="datetime-local" {...register('visit_datetime')} className={inputCls} />
          {errors.visit_datetime && (
            <p className="text-xs text-red-500">{errors.visit_datetime.message}</p>
          )}
        </div>
        <div className="flex flex-col gap-1 xl:col-span-2">
          <label className="text-xs font-medium text-apple-light">담당자</label>
          <input {...register('engineer_name')} className={inputCls} placeholder="담당자명" />
        </div>
        <div className="flex flex-col gap-1 xl:col-span-2">
          <label className="text-xs font-medium text-apple-light">연락처</label>
          <input
            className={inputCls}
            placeholder="010-0000-0000"
            inputMode="numeric"
            {...register('engineer_phone')}
            onChange={(e) =>
              setValue('engineer_phone', formatPhone(e.target.value), { shouldValidate: true })
            }
          />
        </div>
        <div className="flex flex-col gap-1 sm:col-span-2 xl:col-span-4">
          <label className="text-xs font-medium text-apple-light">요청내용</label>
          <textarea
            {...register('request_content')}
            className={inputCls + ' resize-none'}
            rows={2}
            placeholder="고객 요청 사항"
          />
        </div>
        <div className="flex flex-col gap-1 sm:col-span-2 xl:col-span-4">
          <label className="text-xs font-medium text-apple-light">조치내용</label>
          <textarea
            {...register('action_content')}
            className={inputCls + ' resize-none'}
            rows={2}
            placeholder="처리 및 조치 내용"
          />
        </div>
      </div>
      {isError && <p className="text-xs text-red-500">저장 중 오류가 발생했습니다</p>}
      <div className="flex flex-col-reverse gap-2 pt-1 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={onCancel}
          className="w-full rounded-xl border border-apple-divider px-4 py-2 text-xs text-apple-light transition-colors hover:bg-apple-gray sm:w-auto sm:py-1.5"
        >
          취소
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-xl bg-blue-600 px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50 sm:w-auto sm:py-1.5"
        >
          {isSubmitting ? '저장 중...' : '저장'}
        </button>
      </div>
    </form>
  )
}
