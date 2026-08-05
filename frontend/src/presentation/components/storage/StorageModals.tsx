// frontend/src/presentation/components/storage/StorageModals.tsx
import { useEffect, useRef, useState } from 'react'
import { format } from 'date-fns'
import { ko } from 'date-fns/locale'
import { storageApi } from '@/infrastructure/api/storageApi'
import type { DuplicateFile, FileProgress } from '@/infrastructure/hooks/useStorage'
import type { StorageItem } from '@/domain/Storage'
import { FolderIcon, FileIcon, EyeIcon, TrashIcon, DownloadIcon } from './StorageIcons'
import { formatBytes, isPreviewable } from './StorageUtils'
import { CopyLinkButton, CopyLinkButtonMobile } from './StorageUtils'

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

export function CreateFolderRow({ onConfirm, onCancel }: { onConfirm: (name: string) => void; onCancel: () => void }) {
  const [value, setValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  useEffect(() => { inputRef.current?.focus() }, [])
  const handleSubmit = () => { const t = value.trim(); if (t) onConfirm(t) }
  return (
    <tr className="bg-brand-50/30">
      <td className="px-6 py-3 3xl:px-8" colSpan={4}>
        <div className="flex items-center gap-2">
          <span className="text-brand-500"><FolderIcon /></span>
          <input ref={inputRef} value={value} onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit(); if (e.key === 'Escape') onCancel() }}
            placeholder="폴더 이름"
            className="flex-1 text-[13px] bg-transparent border-b border-brand-400 focus:outline-none text-apple-dark placeholder:text-apple-light/60 pb-0.5" />
          <button onClick={handleSubmit} className="text-[12px] font-medium text-brand-600 hover:text-brand-700 transition-colors px-2 py-1">만들기</button>
          <button onClick={onCancel} className="text-[12px] text-apple-light hover:text-apple-dark transition-colors px-2 py-1">취소</button>
        </div>
      </td>
    </tr>
  )
}

export function CreateFolderRowMobile({ onConfirm, onCancel }: { onConfirm: (name: string) => void; onCancel: () => void }) {
  const [value, setValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  useEffect(() => { inputRef.current?.focus() }, [])
  const handleSubmit = () => { const t = value.trim(); if (t) onConfirm(t) }
  return (
    <div className="flex items-center gap-2 px-4 py-3 bg-brand-50/30 border-b border-apple-divider/40">
      <span className="text-brand-500"><FolderIcon /></span>
      <input ref={inputRef} value={value} onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit(); if (e.key === 'Escape') onCancel() }}
        placeholder="폴더 이름"
        className="flex-1 text-[13px] bg-transparent border-b border-brand-400 focus:outline-none text-apple-dark placeholder:text-apple-light/60 pb-0.5" />
      <button onClick={handleSubmit} className="text-[12px] font-medium text-brand-600 px-2 py-1">만들기</button>
      <button onClick={onCancel} className="text-[12px] text-apple-light px-2 py-1">취소</button>
    </div>
  )
}

export function ItemRow({ item, folder, onEnterDir, onPreview, onDeleteFile, onDeleteDir }: {
  item: StorageItem; folder: string
  onEnterDir: (name: string) => void; onPreview: (name: string) => void
  onDeleteFile: (name: string) => void; onDeleteDir: (name: string) => void
}) {
  const formattedDate = format(new Date(item.uploaded_at), 'MM/dd HH:mm', { locale: ko })
  const canPreview = !item.is_dir && isPreviewable(item.name)
  return (
    <tr className="hover:bg-apple-gray/60 transition-colors duration-150">
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4">
        <div className="flex items-center gap-2">
          <span className={item.is_dir ? 'text-brand-500' : 'text-apple-light'}>
            {item.is_dir ? <FolderIcon /> : <FileIcon />}
          </span>
          {item.is_dir ? (
            <button onClick={() => onEnterDir(item.name)} className="text-[13px] 3xl:text-[14px] font-medium text-brand-600 hover:text-brand-700 hover:underline transition-colors text-left break-all">{item.name}</button>
          ) : canPreview ? (
            <button onClick={() => onPreview(item.name)} className="text-[13px] 3xl:text-[14px] text-apple-dark hover:text-brand-600 hover:underline transition-colors text-left break-all">{item.name}</button>
          ) : (
            <span className="text-[13px] 3xl:text-[14px] text-apple-dark break-all">{item.name}</span>
          )}
        </div>
      </td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-light tabular-nums whitespace-nowrap">{item.is_dir ? '—' : formatBytes(item.size)}</td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4 text-[13px] 3xl:text-[14px] text-apple-light tabular-nums whitespace-nowrap">{formattedDate}</td>
      <td className="px-6 py-3.5 3xl:px-8 3xl:py-4">
        <div className="flex items-center justify-end gap-1.5">
          {canPreview && <button onClick={() => onPreview(item.name)} className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors" title="미리보기"><EyeIcon /></button>}
          {!item.is_dir && <CopyLinkButton name={item.name} folder={folder} />}
          {!item.is_dir && <a href={storageApi.download(item.name, folder)} download={item.name} className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors" title="다운로드"><DownloadIcon /></a>}
          <button onClick={() => item.is_dir ? onDeleteDir(item.name) : onDeleteFile(item.name)} className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors" title="삭제"><TrashIcon /></button>
        </div>
      </td>
    </tr>
  )
}

export function ItemRowMobile({ item, folder, onEnterDir, onPreview, onDeleteFile, onDeleteDir }: {
  item: StorageItem; folder: string
  onEnterDir: (name: string) => void; onPreview: (name: string) => void
  onDeleteFile: (name: string) => void; onDeleteDir: (name: string) => void
}) {
  const formattedDate = format(new Date(item.uploaded_at), 'MM/dd HH:mm', { locale: ko })
  const canPreview = !item.is_dir && isPreviewable(item.name)
  return (
    <div className="flex items-center justify-between px-4 py-4 hover:bg-apple-gray/60 transition-colors">
      <div className="flex items-center gap-2 flex-1 min-w-0 pr-3">
        <span className={`flex-shrink-0 ${item.is_dir ? 'text-brand-500' : 'text-apple-light'}`}>{item.is_dir ? <FolderIcon /> : <FileIcon />}</span>
        {item.is_dir ? (
          <button onClick={() => onEnterDir(item.name)} className="flex flex-col gap-0.5 min-w-0 text-left">
            <span className="text-[13px] font-medium text-brand-600 truncate">{item.name}</span>
            <span className="text-[11px] text-apple-light">{formattedDate}</span>
          </button>
        ) : (
          <button onClick={() => canPreview ? onPreview(item.name) : undefined} className={`flex flex-col gap-0.5 min-w-0 text-left ${canPreview ? 'cursor-pointer' : 'cursor-default'}`}>
            <span className={`text-[13px] font-medium truncate ${canPreview ? 'text-apple-dark hover:text-brand-600' : 'text-apple-dark'}`}>{item.name}</span>
            <span className="text-[11px] text-apple-light">{formatBytes(item.size)} · {formattedDate}</span>
          </button>
        )}
      </div>
      <div className="flex items-center gap-1 flex-shrink-0">
        {canPreview && <button onClick={() => onPreview(item.name)} className="w-8 h-8 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors"><EyeIcon /></button>}
        {!item.is_dir && <CopyLinkButtonMobile name={item.name} folder={folder} />}
        {!item.is_dir && <a href={storageApi.download(item.name, folder)} download={item.name} className="w-8 h-8 rounded-lg flex items-center justify-center text-apple-light hover:text-brand-600 hover:bg-brand-50 transition-colors"><DownloadIcon /></a>}
        <button onClick={() => item.is_dir ? onDeleteDir(item.name) : onDeleteFile(item.name)} className="w-8 h-8 rounded-lg flex items-center justify-center text-apple-light hover:text-red-500 hover:bg-red-50 transition-colors"><TrashIcon /></button>
      </div>
    </div>
  )
}
