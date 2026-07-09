// frontend/src/presentation/components/common/GenerateReportModal.tsx
import { useEffect, useState } from 'react'
import { useTrigger } from '@/infrastructure/hooks/useTrigger'
import { useUiStore } from '@/app/store/uiStore'

interface Props {
  onClose: () => void
}

const PRESETS = [
  { label: '1일', days: 1 },
  { label: '7일', days: 7 },
  { label: '15일', days: 15 },
  { label: '30일', days: 30 },
]

function toLocalDateStr(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export default function GenerateReportModal({ onClose }: Props) {
  const { setTriggerLoading, setTriggerMessage, isTriggerLoading } = useUiStore()

  const { mutate, isPending } = useTrigger({
    onComplete: (reportId) => {
      setTriggerLoading(false)
      setTriggerMessage(`보고서 생성 완료 (ID: ${reportId})`)
    },
    onError: (message) => {
      setTriggerLoading(false)
      setTriggerMessage(`보고서 생성 실패: ${message}`)
    },
    onTimeout: () => {
      setTriggerLoading(false)
      setTriggerMessage('보고서 생성이 시간 초과되었습니다.')
    },
  })

  const today = toLocalDateStr(new Date())
  const [selectedPreset, setSelectedPreset] = useState<number | null>(7)
  const [startDate, setStartDate] = useState('')
  const [endDate,   setEndDate]   = useState('')
  const [mode, setMode]           = useState<'preset' | 'custom'>('preset')

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  function handlePreset(days: number) {
    setSelectedPreset(days)
    setMode('preset')
    const end   = new Date()
    const start = new Date()
    start.setDate(start.getDate() - (days - 1))
    setStartDate(toLocalDateStr(start))
    setEndDate(toLocalDateStr(end))
  }

  function handleStartDate(val: string) { setStartDate(val); setMode('custom'); setSelectedPreset(null) }
  function handleEndDate(val: string)   { setEndDate(val);   setMode('custom'); setSelectedPreset(null) }

  function handleGenerate() {
    setTriggerLoading(true)
    setTriggerMessage(null)
    if (!startDate || !endDate) {
      mutate(undefined)
    } else {
      mutate({ start_date: startDate, end_date: endDate })
    }
    onClose()
  }

  const isDisabled  = isTriggerLoading || isPending
  const canGenerate = !isDisabled && ((mode === 'preset' && selectedPreset !== null) || (mode === 'custom' && !!startDate && !!endDate))
  const dateError   = mode === 'custom' && startDate && endDate && startDate > endDate

  useEffect(() => { handlePreset(7) }, [])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-apple-divider/60">
          <div>
            <h2 className="text-[15px] font-semibold text-apple-dark">보고서 생성</h2>
            <p className="text-[12px] text-apple-light mt-0.5">기준 일자를 설정하여 보고서를 생성합니다</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-apple-gray text-apple-light hover:text-apple-dark transition-colors">✕</button>
        </div>

        <div className="px-6 py-5 flex flex-col gap-5">
          <div>
            <p className="text-[12px] font-medium text-apple-dark mb-2">프리셋</p>
            <div className="flex gap-2">
              {PRESETS.map(({ label, days }) => (
                <button
                  key={days}
                  onClick={() => handlePreset(days)}
                  className={`flex-1 py-2 rounded-xl text-[13px] font-medium border transition-all duration-150 ${
                    mode === 'preset' && selectedPreset === days
                      ? 'bg-brand-600 border-brand-600 text-white shadow-sm'
                      : 'bg-white border-apple-divider text-apple-dark hover:border-brand-400 hover:text-brand-600'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="relative flex items-center gap-3">
            <div className="flex-1 h-px bg-apple-divider/60" />
            <span className="text-[11px] text-apple-light px-1">또는 직접 지정</span>
            <div className="flex-1 h-px bg-apple-divider/60" />
          </div>

          <div className="flex flex-col gap-3">
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-[12px] font-medium text-apple-dark mb-1.5">시작일</label>
                <input type="date" value={startDate} max={today} onChange={(e) => handleStartDate(e.target.value)}
                  className={`w-full px-3 py-2 rounded-lg border text-[13px] text-apple-dark bg-white transition-colors outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-200 ${
                    mode === 'custom' && startDate ? 'border-brand-400 ring-1 ring-brand-200' : 'border-apple-divider'
                  }`} />
              </div>
              <div className="flex-1">
                <label className="block text-[12px] font-medium text-apple-dark mb-1.5">완료일</label>
                <input type="date" value={endDate} max={today} onChange={(e) => handleEndDate(e.target.value)}
                  className={`w-full px-3 py-2 rounded-lg border text-[13px] text-apple-dark bg-white transition-colors outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-200 ${
                    mode === 'custom' && endDate ? 'border-brand-400 ring-1 ring-brand-200' : 'border-apple-divider'
                  }`} />
              </div>
            </div>
            {dateError && <p className="text-[12px] text-red-500">⚠️ 완료일은 시작일보다 많아야 합니다.</p>}
            {(startDate || endDate) && !dateError && (
              <div className="flex items-center gap-2 px-3 py-2 bg-brand-50 rounded-lg border border-brand-100">
                <span className="text-[11px] text-brand-700">확정 기간: <strong>{startDate || '—'}</strong> – <strong>{endDate || '—'}</strong></span>
              </div>
            )}
          </div>
        </div>

        <div className="px-6 py-4 border-t border-apple-divider/60 flex items-center justify-between gap-3">
          <button onClick={onClose} className="px-4 py-2 rounded-xl text-[13px] font-medium bg-apple-gray hover:bg-apple-divider text-apple-dark transition-colors">취소</button>
          <button
            onClick={handleGenerate}
            disabled={!canGenerate || !!dateError}
            className="px-5 py-2 rounded-xl text-[13px] font-semibold bg-brand-600 hover:bg-brand-700 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed text-white transition-all duration-200 shadow-sm hover:shadow-md flex items-center gap-2"
          >
            {isDisabled
              ? <><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /><span>생성 중...</span></>
              : <span>보고서 생성</span>
            }
          </button>
        </div>
      </div>
    </div>
  )
}
