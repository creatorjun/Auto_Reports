// frontend/src/presentation/pages/SiteCreatePage.tsx
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { siteApi } from '@/infrastructure/api/siteApi'

const schema = z.object({
  id: z.string().min(1, '사이트 ID를 입력하세요'),
  site_name: z.string().min(1, '사이트명을 입력하세요'),
  status: z.enum(['active', 'inactive', 'expired', 'maintenance']),
  contract_type: z.enum(['annual', 'monthly', 'one_time']),
  customer_name: z.string().min(1, '담당자명을 입력하세요'),
  customer_phone: z.string().min(1, '연락처를 입력하세요'),
  customer_email: z.string().email('올바른 이메일을 입력하세요').or(z.literal('')).optional(),
  maintenance_company: z.string().min(1, '유지보수 업체명을 입력하세요'),
  maintenance_name: z.string().min(1, '담당자명을 입력하세요'),
  maintenance_phone: z.string().min(1, '연락처를 입력하세요'),
  maintenance_email: z.string().email('올바른 이메일을 입력하세요').or(z.literal('')).optional(),
  contract_start_date: z.string().min(1, '계약 시작일을 입력하세요'),
  contract_end_date: z.string().min(1, '계약 종료일을 입력하세요'),
})

type FormValues = z.infer<typeof schema>

function Field({
  label,
  error,
  children,
}: {
  label: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-apple-light">{label}</label>
      {children}
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  )
}

const inputCls =
  'w-full border border-apple-divider rounded-xl px-3 py-2 text-sm text-apple-dark bg-white outline-none focus:ring-2 focus:ring-blue-500/30 transition'

const selectCls = inputCls + ' cursor-pointer'

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-sm font-semibold text-apple-dark border-b border-apple-divider pb-1.5 mb-4">
      {children}
    </h2>
  )
}

export default function SiteCreatePage() {
  const navigate = useNavigate()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { status: 'active', contract_type: 'annual' },
  })

  const { mutateAsync, isError, error } = useMutation({
    mutationFn: (values: FormValues) =>
      siteApi.create({
        id: values.id,
        site_name: values.site_name,
        maintenance_company: values.maintenance_company,
        customer_info: {
          name: values.customer_name,
          phone: values.customer_phone,
          email: values.customer_email || undefined,
        },
        maintenance_info: {
          name: values.maintenance_name,
          phone: values.maintenance_phone,
          email: values.maintenance_email || undefined,
        },
        contract_start_date: values.contract_start_date,
        contract_end_date: values.contract_end_date,
        contract_type: values.contract_type,
        status: values.status,
        nodes: [],
        patch_histories: [],
        visit_histories: [],
      }),
    onSuccess: (data) => navigate(`/sites/${data.id}`),
  })

  const onSubmit = (values: FormValues) => mutateAsync(values)

  return (
    <div className="w-full max-w-2xl mx-auto px-6 py-10">
      <div className="flex items-center gap-3 mb-8">
        <button
          type="button"
          onClick={() => navigate('/sites')}
          className="text-apple-light hover:text-apple-dark transition-colors"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M11 4L6 9l5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <h1 className="text-xl font-semibold text-apple-dark">새 사이트 등록</h1>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-8">
        <section>
          <SectionTitle>기본 정보</SectionTitle>
          <div className="grid grid-cols-2 gap-4">
            <Field label="사이트 ID" error={errors.id?.message}>
              <input {...register('id')} className={inputCls} placeholder="예: SITE-001" />
            </Field>
            <Field label="사이트명" error={errors.site_name?.message}>
              <input {...register('site_name')} className={inputCls} placeholder="사이트명" />
            </Field>
            <Field label="상태" error={errors.status?.message}>
              <select {...register('status')} className={selectCls}>
                <option value="active">운영 중</option>
                <option value="inactive">비활성</option>
                <option value="expired">만료</option>
                <option value="maintenance">유지보수</option>
              </select>
            </Field>
            <Field label="계약 유형" error={errors.contract_type?.message}>
              <select {...register('contract_type')} className={selectCls}>
                <option value="annual">연간</option>
                <option value="monthly">월간</option>
                <option value="one_time">일회성</option>
              </select>
            </Field>
          </div>
        </section>

        <section>
          <SectionTitle>고객 정보</SectionTitle>
          <div className="grid grid-cols-2 gap-4">
            <Field label="담당자명" error={errors.customer_name?.message}>
              <input {...register('customer_name')} className={inputCls} placeholder="홍길동" />
            </Field>
            <Field label="연락처" error={errors.customer_phone?.message}>
              <input {...register('customer_phone')} className={inputCls} placeholder="010-0000-0000" />
            </Field>
            <div className="col-span-2">
              <Field label="이메일 (선택)" error={errors.customer_email?.message}>
                <input {...register('customer_email')} className={inputCls} placeholder="example@email.com" />
              </Field>
            </div>
          </div>
        </section>

        <section>
          <SectionTitle>유지보수 담당</SectionTitle>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Field label="유지보수 업체" error={errors.maintenance_company?.message}>
                <input {...register('maintenance_company')} className={inputCls} placeholder="업체명" />
              </Field>
            </div>
            <Field label="담당자명" error={errors.maintenance_name?.message}>
              <input {...register('maintenance_name')} className={inputCls} placeholder="담당자명" />
            </Field>
            <Field label="연락처" error={errors.maintenance_phone?.message}>
              <input {...register('maintenance_phone')} className={inputCls} placeholder="010-0000-0000" />
            </Field>
            <div className="col-span-2">
              <Field label="이메일 (선택)" error={errors.maintenance_email?.message}>
                <input {...register('maintenance_email')} className={inputCls} placeholder="example@email.com" />
              </Field>
            </div>
          </div>
        </section>

        <section>
          <SectionTitle>계약 기간</SectionTitle>
          <div className="grid grid-cols-2 gap-4">
            <Field label="계약 시작일" error={errors.contract_start_date?.message}>
              <input type="date" {...register('contract_start_date')} className={inputCls} />
            </Field>
            <Field label="계약 종료일" error={errors.contract_end_date?.message}>
              <input type="date" {...register('contract_end_date')} className={inputCls} />
            </Field>
          </div>
        </section>

        {isError && (
          <p className="text-sm text-red-500">
            {(error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '등록 중 오류가 발생했습니다'}
          </p>
        )}

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={() => navigate('/sites')}
            className="px-5 py-2 rounded-xl text-sm text-apple-light border border-apple-divider hover:bg-apple-gray transition-colors"
          >
            취소
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-5 py-2 rounded-xl text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? '등록 중...' : '사이트 등록'}
          </button>
        </div>
      </form>
    </div>
  )
}
