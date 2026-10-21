// frontend/src/presentation/components/notifications/JiraNotificationsPanel.tsx
import { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ExternalLink, Loader2, RefreshCw, X } from 'lucide-react'
import type { JiraNotification, JiraNotificationCategory } from '@/domain/JiraNotification'
import { RequestError } from '@/application/errors/RequestError'
import { safeJiraNotificationUrl } from '@/application/services/jiraNotifications'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'
import { useJiraNotifications } from '@/presentation/hooks/useJiraNotifications'
import { useAuthStore } from '@/presentation/state/authStore'

const categories = [{ value: 'all', label: '전체' }, { value: 'direct', label: '직접' }, { value: 'watching', label: '관심' }] as const
const timestamp = new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })

function NotificationItem({ item }: { item: JiraNotification }) {
  const url = safeJiraNotificationUrl(item.url)
  const date = new Date(item.created_at)
  const content = <>
    <span className="flex items-start gap-2">
      {!item.is_read && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand-600"><span className="sr-only">읽지 않음</span></span>}
      <span className={`min-w-0 flex-1 break-words text-label text-apple-dark ${item.is_read ? 'font-medium' : 'font-semibold'}`}>{item.title}</span>
      {url && <ExternalLink size={14} className="mt-0.5 shrink-0 text-apple-light" aria-hidden="true" />}
    </span>
    {item.message && <span className="mt-1.5 block whitespace-pre-wrap break-words text-caption leading-relaxed text-apple-mid">{item.message}</span>}
    <span className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-caption text-apple-light">
      {item.actor && <span className="break-words">{item.actor}</span>}
      <time dateTime={item.created_at}>{Number.isFinite(date.getTime()) ? timestamp.format(date) : '시간 확인 불가'}</time>
      {item.group_size > 1 && <span>{item.group_size.toLocaleString('ko-KR')}개 묶음</span>}
      <span>{item.category === 'direct' ? '직접' : '관심'}</span>
    </span>
  </>
  const className = 'block rounded-xl px-4 py-3'
  return <li data-notification-id={item.id} className="border-t border-apple-divider/60 first:border-t-0">
    {url ? <a href={url} target="_blank" rel="noopener noreferrer" className={`${className} hover:bg-apple-gray focus-visible:outline-brand-500`}>{content}</a> : <div className={className}>{content}</div>}
  </li>
}

interface Props {
  id: string
  trigger: HTMLButtonElement
  sessionToken: string
  sidebarCollapsed?: boolean
  onClose: () => void
}

export default function JiraNotificationsPanel({ id, trigger, sessionToken, sidebarCollapsed = false, onClose }: Props) {
  const [category, setCategory] = useState<JiraNotificationCategory>('all')
  const panel = useRef<HTMLElement>(null)
  const active = useRef(true)
  const { auth } = useApplicationServices()
  const query = useJiraNotifications(category)
  const reconnect = useMutation({
    mutationFn: auth.startJira,
    onSuccess: ({ authorization_url }) => {
      if (active.current && useAuthStore.getState().accessToken === sessionToken) window.location.assign(authorization_url)
    },
    retry: false,
  })
  useEffect(() => {
    active.current = true
    panel.current?.focus()
    const pointer = (event: PointerEvent) => {
      if (event.target instanceof Node && !panel.current?.contains(event.target) && !trigger.contains(event.target)) onClose()
    }
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); onClose() }
    }
    document.addEventListener('pointerdown', pointer)
    document.addEventListener('keydown', keyboard)
    return () => {
      active.current = false
      document.removeEventListener('pointerdown', pointer)
      document.removeEventListener('keydown', keyboard)
      if (trigger.isConnected) trigger.focus()
    }
  }, [onClose, trigger])

  const error = query.error instanceof RequestError && typeof query.error.detail === 'string'
    ? query.error.detail : 'Jira 알림을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.'
  return (
    <section ref={panel} id={id} role="dialog" aria-modal="false" aria-labelledby={`${id}-title`} tabIndex={-1}
      className={`fixed inset-x-3 bottom-4 z-50 flex max-h-[calc(100dvh-2rem)] min-w-0 flex-col overflow-hidden whitespace-normal rounded-2xl border border-apple-divider bg-apple-surface shadow-apple-lg outline-none sm:right-auto sm:w-[420px] ${sidebarCollapsed ? 'xl:left-16 3xl:left-20' : 'xl:left-64 2xl:left-[17rem] 3xl:left-[19rem]'}`}>
      <div className="flex items-start justify-between gap-3 border-b border-apple-divider/60 px-4 py-4">
        <div><h2 id={`${id}-title`} className="text-section-title font-semibold text-apple-dark">Jira 알림</h2><p className="mt-1 text-caption text-apple-mid">읽음 상태는 조회 시점 기준</p></div>
        <div className="flex shrink-0 items-center gap-1">
          <button type="button" disabled={query.isFetching || reconnect.isPending} onClick={() => void query.refresh()} aria-label="Jira 알림 새로고침" className="rounded-lg p-2 text-apple-mid hover:bg-apple-gray focus-visible:ring-2 focus-visible:ring-brand-500 disabled:opacity-40"><RefreshCw size={17} className={query.isFetching ? 'animate-spin' : ''} aria-hidden="true" /></button>
          <button type="button" onClick={onClose} aria-label="Jira 알림 닫기" className="rounded-lg p-2 text-apple-mid hover:bg-apple-gray focus-visible:ring-2 focus-visible:ring-brand-500"><X size={18} aria-hidden="true" /></button>
        </div>
      </div>
      <div role="group" aria-label="Jira 알림 분류" className="flex gap-2 border-b border-apple-divider/60 px-4 py-3">{categories.map(({ value, label }) => <button key={value} type="button" aria-pressed={category === value} onClick={() => setCategory(value)} className={`rounded-lg px-3 py-1.5 text-control font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${category === value ? 'bg-brand-50 text-brand-700' : 'text-apple-mid hover:bg-apple-gray'}`}>{label}</button>)}</div>
      <div className="min-h-0 overflow-y-auto overscroll-contain" aria-busy={query.isFetching}>
        {query.reconnectRequired ? <div className="space-y-3 px-5 py-8 text-center"><p className="text-label text-apple-dark">Jira 알림을 보려면 다시 로그인해 주세요.</p><p className="text-caption text-apple-mid">현재 Jira 계정으로 알림 조회 권한을 연결합니다.</p><button type="button" disabled={reconnect.isPending} onClick={() => reconnect.mutate()} className="rounded-xl bg-brand-600 px-4 py-2.5 text-control font-medium text-white hover:bg-brand-700 disabled:opacity-50">{reconnect.isPending ? 'Jira로 이동 중...' : 'Jira 다시 로그인'}</button>{reconnect.isError && <p role="alert" className="text-caption text-red-600">Jira 로그인에 연결하지 못했습니다. 다시 시도해 주세요.</p>}</div>
          : query.isError ? <div role="alert" className="space-y-3 px-5 py-8 text-center"><p className="text-label text-red-600">{error}</p><button type="button" onClick={() => void query.refresh()} disabled={query.isFetching} className="rounded-lg border border-apple-divider px-4 py-2 text-control text-apple-dark hover:bg-apple-gray disabled:opacity-50">다시 불러오기</button></div>
          : query.isPending ? <p role="status" className="flex items-center justify-center gap-2 px-5 py-10 text-label text-apple-mid"><Loader2 size={17} className="animate-spin" aria-hidden="true" />Jira 알림을 불러오는 중...</p>
          : query.items.length === 0 ? <p role="status" className="px-5 py-10 text-center text-label text-apple-mid">표시할 Jira 알림이 없습니다.</p>
          : <ul aria-label="Jira 알림 목록">{query.items.map((item) => <NotificationItem key={item.id} item={item} />)}</ul>}
        {query.hasMore && <div className="border-t border-apple-divider/60 p-3"><button type="button" disabled={query.isFetching} onClick={query.loadMore} className="w-full rounded-xl border border-apple-divider py-2.5 text-control text-apple-mid hover:bg-apple-gray disabled:opacity-40">{query.isFetching ? '불러오는 중...' : '더 보기'}</button></div>}
      </div>
      <p className="border-t border-apple-divider/60 px-4 py-3 text-caption text-apple-mid">알림을 열어도 Jira의 읽음 상태는 변경되지 않습니다.</p>
    </section>
  )
}
