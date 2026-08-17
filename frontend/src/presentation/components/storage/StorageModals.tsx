// frontend/src/presentation/components/storage/StorageModals.tsx
import type { DuplicateFile, FileProgress } from '@/presentation/hooks/useStorage'
import { formatBytes } from './StorageUtils'

export function QuotaBar({ used, limit, available, percent }: { used: number; limit: number; available: number; percent: number }) {
  const isWarning = percent >= 80
  const isCritical = percent >= 95
  const barColor = isCritical ? 'bg-red-500' : isWarning ? 'bg-amber-400' : 'bg-brand-500'
  const textColor = isCritical ? 'text-red-600' : isWarning ? 'text-amber-600' : 'text-apple-light'
  return (
    <div className="rounded-xl border border-apple-divider/60 bg-white px-4 py-3 shadow-sm">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[12px] font-medium text-apple-dark">저장소 사용량</span>
        <span className={`text-[12px] font-medium ${textColor}`}>
          {formatBytes(used)} / {formatBytes(limit)} ({percent.toFixed(1)}%)
        </span>
      </div>
      <div className="w-full h-1.5 bg-apple-gray rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
      <p className="text-[11px] text-apple-light mt-1">남은 용량 {formatBytes(available)}</p>
    </div>
  )
}

export function DeleteConfirmModal({ target, isDir, onConfirm, onCancel, isPending }: {
  target: string; isDir: boolean; onConfirm: () => void; onCancel: () => void; isPending: boolean
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative bg-white rounded-2xl shadow-2xl p-6 w-[320px] md:w-[380px] mx-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-full bg-red-50 flex items-center justify-center flex-shrink-0">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M9 3.75v5.5M9 11.75v.5" stroke="#ef4444" strokeWidth="1.6" strokeLinecap="round" />
              <path d="M7.273 2.5h3.454c.28 0 .537.15.674.393l4.925 8.625A.75.75 0 0 1 15.652 12.5H2.348a.75.75 0 0 1-.674-1.082l4.925-8.625A.75.75 0 0 1 7.273 2.5Z" stroke="#ef4444" strokeWidth="1.4" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <p className="text-[14px] font-semibold text-apple-dark">{isDir ? '폴더 삭제' : '파일 삭제'}</p>
            <p className="text-[12px] text-apple-light mt-0.5 break-all max-w-[260px]">{target}</p>
          </div>
        </div>
        <p className="text-[13px] text-apple-dark/80 mb-5 leading-relaxed">
          {isDir
            ? <>폴더 내의 모든 파일이 함께 삭제됩니다.<br />정말 삭제하시겠습니까?</>
            : <>이 파일을 삭제하면 복구할 수 없습니다.<br />정말 삭제하시겠습니까?</>
          }
        </p>
        <div className="flex gap-2">
          <button onClick={onCancel} disabled={isPending}
            className="flex-1 px-4 py-2 rounded-xl text-[13px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark transition-colors disabled:opacity-50">취소하기</button>
          <button onClick={onConfirm} disabled={isPending}
            className="flex-1 px-4 py-2 rounded-xl text-[13px] font-medium bg-red-500 hover:bg-red-600 text-white transition-colors disabled:opacity-60 flex items-center justify-center gap-1.5">
            {isPending && <svg className="animate-spin w-3.5 h-3.5" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeDashoffset="12" /></svg>}
            삭제
          </button>
        </div>
      </div>
    </div>
  )
}

export function QuotaExceededModal({ available, needed, onClose }: {
  available: number; needed: number; onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl p-6 w-[340px] md:w-[400px] mx-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-full bg-red-50 flex items-center justify-center flex-shrink-0">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M10 4v6M10 13v.5" stroke="#ef4444" strokeWidth="1.8" strokeLinecap="round" />
              <circle cx="10" cy="10" r="8" stroke="#ef4444" strokeWidth="1.4" />
            </svg>
          </div>
          <div>
            <p className="text-[14px] font-semibold text-apple-dark">저장 용량 부족</p>
            <p className="text-[12px] text-apple-light mt-0.5">업로드를 진행할 수 없습니다</p>
          </div>
        </div>
        <div className="rounded-xl bg-red-50 p-3 mb-5 space-y-1">
          <div className="flex justify-between text-[12px]">
            <span className="text-apple-light">필요 용량</span>
            <span className="font-medium text-red-600">{formatBytes(needed)}</span>
          </div>
          <div className="flex justify-between text-[12px]">
            <span className="text-apple-light">남은 용량</span>
            <span className="font-medium text-apple-dark">{formatBytes(available)}</span>
          </div>
          <div className="flex justify-between text-[12px]">
            <span className="text-apple-light">부족 용량</span>
            <span className="font-medium text-red-600">{formatBytes(needed - available)}</span>
          </div>
        </div>
        <p className="text-[12px] text-apple-light mb-5 leading-relaxed">
          저장소 용량이 부족합니다. 불필요한 파일을 삭제하여 공간을 확보한 후 다시 시도하세요.
        </p>
        <button onClick={onClose}
          className="w-full px-4 py-2.5 rounded-xl text-[13px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark transition-colors">
          확인
        </button>
      </div>
    </div>
  )
}

export function OverwriteConfirmModal({ duplicates, onConfirm, onCancel }: {
  duplicates: DuplicateFile[]
  onConfirm: (overwriteAll: boolean) => void
  onCancel: () => void
}) {
  const dupNames = duplicates.filter(d => d.exists).map(d => d.file.name)
  const newFiles = duplicates.filter(d => !d.exists).map(d => d.file.name)
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative bg-white rounded-2xl shadow-2xl p-6 w-[340px] md:w-[420px] mx-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-full bg-amber-50 flex items-center justify-center flex-shrink-0">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M9 3.75v5.5M9 11.75v.5" stroke="#f59e0b" strokeWidth="1.6" strokeLinecap="round" />
              <path d="M7.273 2.5h3.454c.28 0 .537.15.674.393l4.925 8.625A.75.75 0 0 1 15.652 12.5H2.348a.75.75 0 0 1-.674-1.082l4.925-8.625A.75.75 0 0 1 7.273 2.5Z" stroke="#f59e0b" strokeWidth="1.4" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <p className="text-[14px] font-semibold text-apple-dark">중복 파일 감지</p>
            <p className="text-[12px] text-apple-light mt-0.5">{dupNames.length}개 파일이 이미 존재합니다</p>
          </div>
        </div>
        <div className="mb-4 max-h-32 overflow-y-auto">
          {dupNames.map(name => (
            <div key={name} className="flex items-center gap-2 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
              <span className="text-[12px] text-apple-dark truncate">{name}</span>
              <span className="text-[11px] text-amber-500 flex-shrink-0">덮어쓰기</span>
            </div>
          ))}
          {newFiles.map(name => (
            <div key={name} className="flex items-center gap-2 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
              <span className="text-[12px] text-apple-dark truncate">{name}</span>
              <span className="text-[11px] text-green-500 flex-shrink-0">신규</span>
            </div>
          ))}
        </div>
        <p className="text-[12px] text-apple-light mb-5">
          기존 파일을 덮어쓰고 모두 업로드하거나, 신규 파일만 업로드할 수 있습니다.
        </p>
        <div className="flex gap-2">
          <button onClick={onCancel}
            className="flex-1 px-3 py-2 rounded-xl text-[12px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark transition-colors">취소</button>
          {newFiles.length > 0 && (
            <button onClick={() => onConfirm(false)}
              className="flex-1 px-3 py-2 rounded-xl text-[12px] font-medium bg-brand-50 hover:bg-brand-100 text-brand-700 transition-colors">
              신규만 업로드
            </button>
          )}
          <button onClick={() => onConfirm(true)}
            className="flex-1 px-3 py-2 rounded-xl text-[12px] font-medium bg-amber-500 hover:bg-amber-600 text-white transition-colors">
            모두 덮어쓰기
          </button>
        </div>
      </div>
    </div>
  )
}

export function UploadProgressBar({ progressList, totalPercent }: { progressList: FileProgress[]; totalPercent: number }) {
  if (progressList.length === 0) return null
  return (
    <div className="rounded-xl border border-apple-divider/60 bg-white p-3 space-y-2 shadow-sm">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[12px] font-medium text-apple-dark">
          {progressList.every(p => p.done) ? '업로드 완료 ✓' : `업로드 중... ${totalPercent}%`}
        </span>
        <span className="text-[11px] text-apple-light">{progressList.filter(p => p.done).length} / {progressList.length}개</span>
      </div>
      <div className="w-full h-1.5 bg-apple-gray rounded-full overflow-hidden">
        <div
          className="h-full bg-brand-500 rounded-full transition-all duration-300"
          style={{ width: `${totalPercent}%` }}
        />
      </div>
      {progressList.length > 1 && (
        <div className="space-y-1.5 max-h-32 overflow-y-auto pt-1">
          {progressList.map((p) => (
            <div key={p.name}>
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-[11px] text-apple-light truncate max-w-[75%]">{p.name}</span>
                <span className="text-[11px] text-apple-light flex-shrink-0">
                  {p.done ? <span className="text-green-500">완료</span> : `${p.percent}%`}
                </span>
              </div>
              <div className="w-full h-1 bg-apple-gray rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${p.done ? 'bg-green-400' : 'bg-brand-400'}`}
                  style={{ width: `${p.percent}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
