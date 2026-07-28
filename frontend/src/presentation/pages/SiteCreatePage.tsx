// frontend/src/presentation/pages/SiteCreatePage.tsx
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { siteApi } from '@/infrastructure/api/siteApi'

const emptyToUndefined = (val: unknown) => (val === '' ? undefined : val)

const schema = z.object({
  site_name:           z.string().min(1, '사이트명을 입력하세요'),
  status:              z.preprocess(emptyToUndefined, z.enum(['installing', 'active', 'inactive', 'expired', 'maintenance']).optional()),
  contract_type:       z.preprocess(emptyToUndefined, z.enum(['정식라이센스', '임시라이센스']).optional()),
  maintenance_company: z.string().optional(),
  customer_name:       z.string().optional(),
  customer_phone:      z.string().optional(),
  customer_email:      z.string().email('올바른 이메일').or(z.literal('')).optional(),
  maintenance_name:    z.string().optional(),
  maintenance_phone:   z.string().optional(),
  maintenance_email:   z.string().email('올바른 이메일').or(z.literal('')).optional(),
  contract_start_date: z.preprocess(emptyToUndefined, z.string().optional()),
  contract_end_date:   z.preprocess(emptyToUndefined, z.string().optional()),
  cli_username:        z.string().optional(),
  cli_password:        z.string().optional(),
  cli_ip:              z.string().optional(),
  cli_port:            z.string().optional(),
  web_username:        z.string().optional(),
  web_password:        z.string().optional(),
  web_ip:              z.string().optional(),
  web_port:            z.string().optional(),
  db_username:         z.string().optional(),
  db_password:         z.string().optional(),
  db_ip:               z.string().optional(),
  db_port:             z.string().optional(),
  vpn_username:        z.string().optional(),
  vpn_password:        z.string().optional(),
  vpn_ip:              z.string().optional(),
  vpn_port:            z.string().optional(),
  access_note:         z.string().optional(),
})

type FormValues = z.infer<typeof schema>

type ApiError = {
  response?: {
    data?: {
      detail?: string | Array<{ msg: string; loc: (string | number)[] }>
    }
  }
}

function extractErrorMessage(error: unknown): string {
  const detail = (error as ApiError)?.response?.data?.detail
  if (!detail) return '저장 중 오류가 발생했습니다'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((e) => `${e.loc.slice(-1)[0]}: ${e.msg}`).join(' / ')
  }
  return '저장 중 오류가 발생했습니다'
}

function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 11)
  if (digits.length < 4) return digits
  if (digits.length < 7) return `${digits.slice(0, 3)}-${digits.slice(3)}`
  if (digits.length < 11) return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`
  return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`
}

function EyeIcon({ open }: { open: boolean }) {
  return open ? (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5Z" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.4" />
      <path d="M2 2l12 12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  ) : (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5Z" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  )
}

function Field({
  label, error, children,
}: {
  label: string; error?: string; children: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-apple-light">{label}</label>
      {children}
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  )
}

const inputCls = 'w-full border border-apple-divider rounded-xl px-3 py-2 text-sm text-apple-dark bg-white outline-none focus:ring-2 focus:ring-blue-500/30 transition'
const selectCls = inputCls + ' cursor-pointer'

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-sm font-semibold text-apple-dark border-b border-apple-divider pb-1.5 mb-4">
      {children}
    </h2>
  )
}

function PhoneInput({
  name, register, setValue, placeholder = '010-0000-0000',
}: {
  name: 'customer_phone' | 'maintenance_phone'
  register: ReturnType<typeof useForm<FormValues>>['register']
  setValue: ReturnType<typeof useForm<FormValues>>['setValue']
  placeholder?: string
}) {
  const { onChange, ...rest } = register(name)
  return (
    <input
      {...rest}
      className={inputCls}
      placeholder={placeholder}
      inputMode="numeric"
      onChange={(e) => {
        setValue(name, formatPhone(e.target.value), { shouldValidate: true })
      }}
    />
  )
}

function CredentialRow({
  label, usernameKey, passwordKey, ipKey, portKey, register, errors,
}: {
  label: string
  usernameKey: keyof FormValues
  passwordKey: keyof FormValues
  ipKey: keyof FormValues
  portKey: keyof FormValues
  register: ReturnType<typeof useForm<FormValues>>['register']
  errors: ReturnType<typeof useForm<FormValues>>['formState']['errors']
}) {
  const [showPw, setShowPw] = useState(false)
  return (
    <div className="rounded-xl border border-apple-divider/60 px-4 py-3 flex flex-col gap-3">
      <p className="text-xs font-semibold text-blue-600">{label}</p>
      <div className="grid grid-cols-2 gap-3">
        <Field label="ID" error={(errors[usernameKey] as { message?: string })?.message}>
          <input {...register(usernameKey)} className={inputCls} placeholder="username" />
        </Field>
        <Field label="PW" error={(errors[passwordKey] as { message?: string })?.message}>
          <div className="relative">
            <input
              {...register(passwordKey)}
              type={showPw ? 'text' : 'password'}
              className={inputCls + ' pr-9'}
              placeholder="password"
            />
            <button
              type="button"
              onClick={() => setShowPw(v => !v)}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-apple-light hover:text-apple-dark transition-colors"
              tabIndex={-1}
            >
              <EyeIcon open={showPw} />
            </button>
          </div>
        </Field>
        <Field label="IP(URL)" error={(errors[ipKey] as { message?: string })?.message}>
          <input {...register(ipKey)} className={inputCls} placeholder="192.168.0.1 또는 https://..." />
        </Field>
        <Field label="Port" error={(errors[portKey] as { message?: string })?.message}>
          <input {...register(portKey)} className={inputCls} placeholder="22" inputMode="numeric" />
        </Field>
      </div>
    </div>
  )
}

export default function SiteCreatePage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const isEdit = !!id
  const queryClient = useQueryClient()

  const { data: existing, isLoading } = useQuery({
    queryKey: ['site-detail', id],
    queryFn: () => siteApi.getById(id!),
    enabled: isEdit,
  })

  const {
    register, handleSubmit, setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: isEdit && existing ? {
      site_name:           existing.site_name ?? '',
      status:              (existing.status as FormValues['status']) ?? undefined,
      contract_type:       (existing.contract_type as FormValues['contract_type']) ?? undefined,
      maintenance_company: existing.maintenance_company ?? '',
      customer_name:       existing.customer_info?.name ?? '',
      customer_phone:      existing.customer_info?.phone ?? '',
      customer_email:      existing.customer_info?.email ?? '',
      maintenance_name:    existing.maintenance_info?.name ?? '',
      maintenance_phone:   existing.maintenance_info?.phone ?? '',
      maintenance_email:   existing.maintenance_info?.email ?? '',
      contract_start_date: existing.contract_start_date ?? '',
      contract_end_date:   existing.contract_end_date ?? '',
      cli_username:        existing.access_credentials?.cli?.username ?? '',
      cli_password:        existing.access_credentials?.cli?.password ?? '',
      cli_ip:              existing.access_credentials?.cli?.ip ?? '',
      cli_port:            existing.access_credentials?.cli?.port ?? '',
      web_username:        existing.access_credentials?.web?.username ?? '',
      web_password:        existing.access_credentials?.web?.password ?? '',
      web_ip:              existing.access_credentials?.web?.ip ?? '',
      web_port:            existing.access_credentials?.web?.port ?? '',
      db_username:         existing.access_credentials?.db?.username ?? '',
      db_password:         existing.access_credentials?.db?.password ?? '',
      db_ip:               existing.access_credentials?.db?.ip ?? '',
      db_port:             existing.access_credentials?.db?.port ?? '',
      vpn_username:        existing.access_credentials?.vpn?.username ?? '',
      vpn_password:        existing.access_credentials?.vpn?.password ?? '',
      vpn_ip:              existing.access_credentials?.vpn?.ip ?? '',
      vpn_port:            existing.access_credentials?.vpn?.port ?? '',
      access_note:         existing.access_credentials?.note ?? '',
    } : undefined,
  })

  const { mutateAsync, isError, error } = useMutation({
    mutationFn: (values: FormValues) => {
      const buildCred = (
        u?: string, p?: string, ip?: string, port?: string,
      ) => u ? {
        username: u,
        password: p ?? '',
        ip:       ip   || undefined,
        port:     port || undefined,
      } : undefined

      const creds = {
        cli:  buildCred(values.cli_username,  values.cli_password,  values.cli_ip,  values.cli_port),
        web:  buildCred(values.web_username,  values.web_password,  values.web_ip,  values.web_port),
        db:   buildCred(values.db_username,   values.db_password,   values.db_ip,   values.db_port),
        vpn:  buildCred(values.vpn_username,  values.vpn_password,  values.vpn_ip,  values.vpn_port),
        note: values.access_note || undefined,
      }
      const hasAnyCred = creds.cli || creds.web || creds.db || creds.vpn || creds.note

      const buildContact = (name?: string, phone?: string, email?: string) =>
        name || phone || email
          ? { name: name || undefined, phone: phone || undefined, email: email || undefined }
          : undefined

      const payload = {
        site_name:           values.site_name,
        maintenance_company: values.maintenance_company || undefined,
        customer_info:       buildContact(values.customer_name, values.customer_phone, values.customer_email),
        maintenance_info:    buildContact(values.maintenance_name, values.maintenance_phone, values.maintenance_email),
        contract_start_date: values.contract_start_date || undefined,
        contract_end_date:   values.contract_end_date   || undefined,
        contract_type:       values.contract_type       || undefined,
        status:              values.status              || undefined,
        nodes:               existing?.nodes            ?? [],
        patch_histories:     existing?.patch_histories  ?? [],
        visit_histories:     existing?.visit_histories  ?? [],
        access_credentials:  hasAnyCred ? creds : undefined,
      }

      return isEdit
        ? siteApi.update(Number(id), payload)
        : siteApi.create(payload)
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['site-detail', String(data.id)] })
      navigate(`/sites/${data.id}`)
    },
  })

  if (isEdit && isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-sm text-apple-light">불러오는 중...</span>
      </div>
    )
  }

  return (
    <div className="w-full max-w-2xl mx-auto px-6 py-10">
      <div className="flex items-center gap-3 mb-8">
        <button
          type="button"
          onClick={() => navigate(isEdit ? `/sites/${id}` : '/sites')}
          className="text-apple-light hover:text-apple-dark transition-colors"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M11 4L6 9l5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <h1 className="text-xl font-semibold text-apple-dark">
          {isEdit ? '사이트 수정' : '새 사이트 등록'}
        </h1>
      </div>

      <form onSubmit={handleSubmit(v => mutateAsync(v))} className="flex flex-col gap-8">
        <section>
          <SectionTitle>기본 정보 <span className="text-red-400">*</span></SectionTitle>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Field label="사이트명 *" error={errors.site_name?.message}>
                <input {...register('site_name')} className={inputCls} placeholder="사이트명" />
              </Field>
            </div>
            <Field label="상태 (선택)" error={(errors.status as { message?: string })?.message}>
              <select {...register('status')} className={selectCls}>
                <option value="">— 미입력 —</option>
                <option value="installing">구축중</option>
                <option value="active">운영 중</option>
                <option value="inactive">비활성</option>
                <option value="expired">만료</option>
                <option value="maintenance">유지보수</option>
              </select>
            </Field>
            <Field label="라이센스 (선택)" error={(errors.contract_type as { message?: string })?.message}>
              <select {...register('contract_type')} className={selectCls}>
                <option value="">— 미입력 —</option>
                <option value="정식라이센스">정식라이센스</option>
                <option value="임시라이센스">임시라이센스</option>
              </select>
            </Field>
          </div>
        </section>

        <section>
          <SectionTitle>고객 정보 (선택)</SectionTitle>
          <div className="grid grid-cols-2 gap-4">
            <Field label="담당자명">
              <input {...register('customer_name')} className={inputCls} placeholder="홍길동" />
            </Field>
            <Field label="연락처">
              <PhoneInput name="customer_phone" register={register} setValue={setValue} />
            </Field>
            <div className="col-span-2">
              <Field label="이메일" error={errors.customer_email?.message}>
                <input {...register('customer_email')} className={inputCls} placeholder="example@email.com" />
              </Field>
            </div>
          </div>
        </section>

        <section>
          <SectionTitle>유지보수 담당 (선택)</SectionTitle>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Field label="유지보수 업체">
                <input {...register('maintenance_company')} className={inputCls} placeholder="업체명" />
              </Field>
            </div>
            <Field label="담당자명">
              <input {...register('maintenance_name')} className={inputCls} placeholder="담당자명" />
            </Field>
            <Field label="연락처">
              <PhoneInput name="maintenance_phone" register={register} setValue={setValue} />
            </Field>
            <div className="col-span-2">
              <Field label="이메일" error={errors.maintenance_email?.message}>
                <input {...register('maintenance_email')} className={inputCls} placeholder="example@email.com" />
              </Field>
            </div>
          </div>
        </section>

        <section>
          <SectionTitle>계약 기간 (선택)</SectionTitle>
          <div className="grid grid-cols-2 gap-4">
            <Field label="계약 시작일">
              <input type="date" {...register('contract_start_date')} className={inputCls} />
            </Field>
            <Field label="계약 종료일">
              <input type="date" {...register('contract_end_date')} className={inputCls} />
            </Field>
          </div>
        </section>

        <section>
          <SectionTitle>접속 정보 (선택)</SectionTitle>
          <div className="flex flex-col gap-3">
            <CredentialRow
              label="CLI"
              usernameKey="cli_username" passwordKey="cli_password"
              ipKey="cli_ip" portKey="cli_port"
              register={register} errors={errors}
            />
            <CredentialRow
              label="WEB"
              usernameKey="web_username" passwordKey="web_password"
              ipKey="web_ip" portKey="web_port"
              register={register} errors={errors}
            />
            <CredentialRow
              label="DB"
              usernameKey="db_username" passwordKey="db_password"
              ipKey="db_ip" portKey="db_port"
              register={register} errors={errors}
            />
            <CredentialRow
              label="VPN"
              usernameKey="vpn_username" passwordKey="vpn_password"
              ipKey="vpn_ip" portKey="vpn_port"
              register={register} errors={errors}
            />
            <Field label="기타 사항">
              <textarea
                {...register('access_note')}
                className={inputCls + ' resize-none'}
                rows={3}
                placeholder="추가 접속 정보 및 참고사항..."
              />
            </Field>
          </div>
        </section>

        {isError && (
          <p className="text-sm text-red-500">
            {extractErrorMessage(error)}
          </p>
        )}

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={() => navigate(isEdit ? `/sites/${id}` : '/sites')}
            className="px-5 py-2 rounded-xl text-sm text-apple-light border border-apple-divider hover:bg-apple-gray transition-colors"
          >
            취소
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-5 py-2 rounded-xl text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? '저장 중...' : isEdit ? '수정 완료' : '사이트 등록'}
          </button>
        </div>
      </form>
    </div>
  )
}
