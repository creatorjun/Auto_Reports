// frontend/src/presentation/pages/SiteCreatePage.tsx
import { useNavigate, useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import type { Credential } from '@/domain/Site'
import {
  schema, type FormValues,
  extractErrorMessage, inputCls, selectCls,
  Field, SectionTitle, PhoneInput, CredentialRow,
} from '@/presentation/components/site/create/SiteCreateFormHelpers'

export default function SiteCreatePage() {
  const { sites } = useApplicationServices()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const isEdit = !!id
  const queryClient = useQueryClient()

  const { data: existing, isLoading } = useQuery({
    queryKey: ['site-detail', id],
    queryFn: () => sites.getById(id!),
    enabled: isEdit,
  })

  const {
    register, handleSubmit, setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: isEdit && existing ? {
      site_name:               existing.site_name ?? '',
      status:                  (existing.status as FormValues['status']) ?? undefined,
      contract_type:           (existing.contract_type as FormValues['contract_type']) ?? undefined,
      maintenance_company:     existing.maintenance_company ?? '',
      customer_name:           existing.customer_info?.name ?? '',
      customer_phone:          existing.customer_info?.phone ?? '',
      customer_email:          existing.customer_info?.email ?? '',
      maintenance_name:        existing.maintenance_info?.name ?? '',
      maintenance_phone:       existing.maintenance_info?.phone ?? '',
      maintenance_email:       existing.maintenance_info?.email ?? '',
      maintenance_contact_company: existing.maintenance_info?.company ?? '',
      contract_start_date:     existing.contract_start_date ?? '',
      contract_end_date:       existing.contract_end_date ?? '',
      cli_username:            existing.access_credentials?.cli?.username ?? '',
      cli_password:            existing.access_credentials?.cli?.password ?? '',
      cli_ip:                  existing.access_credentials?.cli?.ip ?? '',
      cli_port:                existing.access_credentials?.cli?.port ?? '',
      web_username:            existing.access_credentials?.web?.username ?? '',
      web_password:            existing.access_credentials?.web?.password ?? '',
      web_ip:                  existing.access_credentials?.web?.ip ?? '',
      web_port:                existing.access_credentials?.web?.port ?? '',
      db_username:             existing.access_credentials?.db?.username ?? '',
      db_password:             existing.access_credentials?.db?.password ?? '',
      db_ip:                   existing.access_credentials?.db?.ip ?? '',
      db_port:                 existing.access_credentials?.db?.port ?? '',
      vpn_username:            existing.access_credentials?.vpn?.username ?? '',
      vpn_password:            existing.access_credentials?.vpn?.password ?? '',
      vpn_ip:                  existing.access_credentials?.vpn?.ip ?? '',
      vpn_port:                existing.access_credentials?.vpn?.port ?? '',
      access_note:             existing.access_credentials?.note ?? '',
    } : undefined,
  })

  const { mutateAsync, isError, error } = useMutation({
    mutationFn: (values: FormValues) => {
      const buildCred = (
        u?: string, p?: string, ip?: string, port?: string,
        existingCred?: Credential,
      ): Credential | undefined => {
        const resolvedUsername = u || existingCred?.username
        const resolvedPassword = p || existingCred?.password
        const resolvedIp = ip || existingCred?.ip
        const resolvedPort = port || existingCred?.port
        if (!resolvedUsername && !resolvedPassword && !resolvedIp && !resolvedPort) return undefined
        return {
          username: resolvedUsername || undefined,
          password: resolvedPassword || undefined,
          ip: resolvedIp || undefined,
          port: resolvedPort || undefined,
        }
      }

      const ec = existing?.access_credentials
      const creds = {
        cli:  buildCred(values.cli_username,  values.cli_password,  values.cli_ip,  values.cli_port,  ec?.cli),
        web:  buildCred(values.web_username,  values.web_password,  values.web_ip,  values.web_port,  ec?.web),
        db:   buildCred(values.db_username,   values.db_password,   values.db_ip,   values.db_port,   ec?.db),
        vpn:  buildCred(values.vpn_username,  values.vpn_password,  values.vpn_ip,  values.vpn_port,  ec?.vpn),
        note: values.access_note || undefined,
      }
      const hasAnyCred = creds.cli || creds.web || creds.db || creds.vpn || creds.note

      const buildContact = (name?: string, phone?: string, email?: string, company?: string) =>
        name || phone || email || company
          ? { name: name || undefined, phone: phone || undefined, email: email || undefined, company: company || undefined }
          : undefined

      const baseFields = {
        site_name:           values.site_name,
        maintenance_company: values.maintenance_company || undefined,
        customer_info:       buildContact(values.customer_name, values.customer_phone, values.customer_email),
        maintenance_info:    buildContact(values.maintenance_name, values.maintenance_phone, values.maintenance_email, values.maintenance_contact_company),
        contract_start_date: values.contract_start_date || undefined,
        contract_end_date:   values.contract_end_date   || undefined,
        contract_type:       values.contract_type       || undefined,
        status:              values.status              || undefined,
        access_credentials:  hasAnyCred ? creds : undefined,
      }

      if (isEdit) return sites.update(Number(id), baseFields)
      return sites.create({ ...baseFields, nodes: [], patch_histories: [], visit_histories: [] })
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

      <form onSubmit={handleSubmit(v => mutateAsync(v))} className="flex flex-col gap-8" autoComplete="off">
        <section>
          <SectionTitle>기본 정보 <span className="text-red-400">*</span></SectionTitle>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Field label="사이트명 *" error={errors.site_name?.message}>
                <input {...register('site_name')} className={inputCls} placeholder="사이트명을 입력하세요" />
              </Field>
            </div>
            <Field label="상태">
              <select {...register('status')} className={selectCls}>
                <option value="">선택 안함</option>
                <option value="installing">설치중</option>
                <option value="active">운영중</option>
                <option value="inactive">비활성</option>
                <option value="expired">만료</option>
                <option value="maintenance">점검중</option>
              </select>
            </Field>
            <Field label="계약 유형">
              <select {...register('contract_type')} className={selectCls}>
                <option value="">선택 안함</option>
                <option value="정식라이센스">정식라이센스</option>
                <option value="임시라이센스">임시라이센스</option>
              </select>
            </Field>
            <Field label="유지보수 업체">
              <input {...register('maintenance_company')} className={inputCls} placeholder="업체명" />
            </Field>
            <Field label="계약 시작일">
              <input {...register('contract_start_date')} type="date" className={inputCls} />
            </Field>
            <Field label="계약 종료일">
              <input {...register('contract_end_date')} type="date" className={inputCls} />
            </Field>
          </div>
        </section>

        <section>
          <SectionTitle>고객 정보</SectionTitle>
          <div className="grid grid-cols-2 gap-4">
            <Field label="담당자명">
              <input {...register('customer_name')} className={inputCls} placeholder="홍길동" />
            </Field>
            <Field label="연락처">
              <PhoneInput name="customer_phone" register={register} setValue={setValue} />
            </Field>
            <Field label="이메일" error={errors.customer_email?.message}>
              <input {...register('customer_email')} className={inputCls} placeholder="email@example.com" />
            </Field>
          </div>
        </section>

        <section>
          <SectionTitle>유지보수 담당자</SectionTitle>
          <div className="grid grid-cols-2 gap-4">
            <Field label="담당자명">
              <input {...register('maintenance_name')} className={inputCls} placeholder="홍길동" />
            </Field>
            <Field label="연락처">
              <PhoneInput name="maintenance_phone" register={register} setValue={setValue} />
            </Field>
            <Field label="이메일" error={errors.maintenance_email?.message}>
              <input {...register('maintenance_email')} className={inputCls} placeholder="email@example.com" />
            </Field>
            <Field label="소속 업체">
              <input {...register('maintenance_contact_company')} className={inputCls} placeholder="업체명" />
            </Field>
          </div>
        </section>

        <section>
          <SectionTitle>접속 정보</SectionTitle>
          <div className="flex flex-col gap-4">
            <CredentialRow label="CLI" usernameKey="cli_username" passwordKey="cli_password" ipKey="cli_ip" portKey="cli_port" register={register} errors={errors} />
            <CredentialRow label="Web" usernameKey="web_username" passwordKey="web_password" ipKey="web_ip" portKey="web_port" register={register} errors={errors} />
            <CredentialRow label="DB"  usernameKey="db_username"  passwordKey="db_password"  ipKey="db_ip"  portKey="db_port"  register={register} errors={errors} />
            <CredentialRow label="VPN" usernameKey="vpn_username" passwordKey="vpn_password" ipKey="vpn_ip" portKey="vpn_port" register={register} errors={errors} />
            <Field label="비고">
              <textarea {...register('access_note')} className={inputCls + ' resize-none'} rows={3} placeholder="추가 접속 정보나 메모를 입력하세요" />
            </Field>
          </div>
        </section>

        {isError && (
          <p className="text-sm text-red-500 bg-red-50 rounded-xl px-4 py-3">
            {extractErrorMessage(error)}
          </p>
        )}

        <div className="flex gap-3 justify-end pt-2">
          <button
            type="button"
            onClick={() => navigate(isEdit ? `/sites/${id}` : '/sites')}
            className="px-5 py-2 text-sm rounded-xl border border-apple-divider text-apple-dark hover:bg-apple-bg transition-colors"
          >
            취소
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-5 py-2 text-sm rounded-xl bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? '저장 중...' : isEdit ? '수정 완료' : '등록'}
          </button>
        </div>
      </form>
    </div>
  )
}
