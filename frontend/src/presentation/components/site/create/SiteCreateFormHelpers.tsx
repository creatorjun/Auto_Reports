// frontend/src/presentation/components/site/create/SiteCreateFormHelpers.tsx
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

const emptyToUndefined = (val: unknown) => (val === '' ? undefined : val)

export const schema = z.object({
  site_name:               z.string().min(1, '사이트명을 입력하세요'),
  status:                  z.preprocess(emptyToUndefined, z.enum(['installing', 'active', 'inactive', 'expired', 'maintenance']).optional()),
  contract_type:           z.preprocess(emptyToUndefined, z.enum(['정식라이센스', '임시라이센스']).optional()),
  maintenance_company:     z.string().optional(),
  customer_name:           z.string().optional(),
  customer_phone:          z.string().optional(),
  customer_email:          z.string().email('올바른 이메일').or(z.literal('')).optional(),
  maintenance_name:        z.string().optional(),
  maintenance_phone:       z.string().optional(),
  maintenance_email:       z.string().email('올바른 이메일').or(z.literal('')).optional(),
  maintenance_contact_company: z.string().optional(),
  contract_start_date:     z.preprocess(emptyToUndefined, z.string().optional()),
  contract_end_date:       z.preprocess(emptyToUndefined, z.string().optional()),
  cli_username:            z.string().optional(),
  cli_password:            z.string().optional(),
  cli_ip:                  z.string().optional(),
  cli_port:                z.string().optional(),
  web_username:            z.string().optional(),
  web_password:            z.string().optional(),
  web_ip:                  z.string().optional(),
  web_port:                z.string().optional(),
  db_username:             z.string().optional(),
  db_password:             z.string().optional(),
  db_ip:                   z.string().optional(),
  db_port:                 z.string().optional(),
  vpn_username:            z.string().optional(),
  vpn_password:            z.string().optional(),
  vpn_ip:                  z.string().optional(),
  vpn_port:                z.string().optional(),
  access_note:             z.string().optional(),
})

export type FormValues = z.infer<typeof schema>

export type ApiError = {
  response?: {
    data?: {
      detail?: string | Array<{ msg: string; loc: (string | number)[] }>
    }
  }
}

export function extractErrorMessage(error: unknown): string {
  const detail = (error as ApiError)?.response?.data?.detail
  if (!detail) return '저장 중 오류가 발생했습니다'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((e) => `${e.loc.slice(-1)[0]}: ${e.msg}`).join(' / ')
  }
  return '저장 중 오류가 발생했습니다'
}

export function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 11)
  if (digits.length < 4) return digits
  if (digits.length < 7) return `${digits.slice(0, 3)}-${digits.slice(3)}`
  if (digits.length < 11) return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`
  return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`
}

export const inputCls = 'w-full border border-apple-divider rounded-xl px-3 py-2 text-sm text-apple-dark bg-white outline-none focus:ring-2 focus:ring-blue-500/30 transition'
export const selectCls = inputCls + ' cursor-pointer'

export function EyeIcon({ open }: { open: boolean }) {
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

export function Field({
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

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-sm font-semibold text-apple-dark border-b border-apple-divider pb-1.5 mb-4">
      {children}
    </h2>
  )
}

export function PhoneInput({
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

export function CredentialRow({
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
          <input {...register(usernameKey)} className={inputCls} placeholder="username" autoComplete="off" />
        </Field>
        <Field label="PW" error={(errors[passwordKey] as { message?: string })?.message}>
          <div className="relative">
            <input
              {...register(passwordKey)}
              type="text"
              className={inputCls + ' pr-9'}
              placeholder="password"
              autoComplete="off"
              style={showPw ? undefined : { WebkitTextSecurity: 'disc' } as React.CSSProperties}
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
