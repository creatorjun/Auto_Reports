// frontend/src/presentation/components/storage/FilePreviewModal.tsx
import { useEffect, useState } from 'react'
import { storageApi } from '@/infrastructure/api/storageApi'

type PreviewType =
  | 'image' | 'video' | 'pdf'
  | 'text' | 'markdown' | 'csv' | 'json'
  | 'xlsx' | 'docx' | 'pptx'
  | 'unsupported'

function detectType(name: string): PreviewType {
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  if (['png','jpg','jpeg','gif','webp','svg','bmp','ico'].includes(ext)) return 'image'
  if (['mp4','webm','ogg','mov'].includes(ext)) return 'video'
  if (ext === 'pdf') return 'pdf'
  if (['txt','log','sh','py','ts','tsx','js','jsx','css','html','env'].includes(ext)) return 'text'
  if (ext === 'md') return 'markdown'
  if (ext === 'csv') return 'csv'
  if (['json','yaml','yml','xml','toml'].includes(ext)) return 'json'
  if (['xlsx','xls'].includes(ext)) return 'xlsx'
  if (['docx','doc'].includes(ext)) return 'docx'
  if (['pptx','ppt'].includes(ext)) return 'pptx'
  return 'unsupported'
}

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M4 4l10 10M14 4L4 14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

function LoadingSpinnerSmall() {
  return (
    <div className="flex items-center justify-center h-40">
      <svg className="animate-spin w-8 h-8 text-brand-500" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeDashoffset="12" />
      </svg>
    </div>
  )
}

function TextPreview({ url }: { url: string }) {
  const [content, setContent] = useState<string | null>(null)
  useEffect(() => {
    fetch(url).then(r => r.text()).then(setContent)
  }, [url])
  if (content === null) return <LoadingSpinnerSmall />
  return (
    <pre className="text-[12px] leading-relaxed text-apple-dark whitespace-pre-wrap break-all font-mono p-4 overflow-auto max-h-[65vh]">
      {content}
    </pre>
  )
}

function MarkdownPreview({ url }: { url: string }) {
  const [html, setHtml] = useState<string | null>(null)
  useEffect(() => {
    fetch(url)
      .then(r => r.text())
      .then(async (text) => {
        const { marked } = await import('marked')
        setHtml(marked.parse(text) as string)
      })
  }, [url])
  if (html === null) return <LoadingSpinnerSmall />
  return (
    <div
      className="prose prose-sm max-w-none p-5 overflow-auto max-h-[65vh] text-apple-dark"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

function CsvPreview({ url }: { url: string }) {
  const [rows, setRows] = useState<string[][] | null>(null)
  useEffect(() => {
    fetch(url)
      .then(r => r.text())
      .then(text => {
        const lines = text.trim().split('\n')
        setRows(lines.map(l => l.split(',')))
      })
  }, [url])
  if (rows === null) return <LoadingSpinnerSmall />
  return (
    <div className="overflow-auto max-h-[65vh] p-2">
      <table className="text-[12px] border-collapse w-full">
        <thead>
          <tr>
            {rows[0]?.map((h, i) => (
              <th key={i} className="border border-apple-divider px-3 py-1.5 bg-apple-gray text-apple-dark font-semibold text-left whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(1).map((row, i) => (
            <tr key={i} className="even:bg-apple-gray/40">
              {row.map((cell, j) => (
                <td key={j} className="border border-apple-divider/60 px-3 py-1 text-apple-dark whitespace-nowrap">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function XlsxPreview({ url }: { url: string }) {
  const [html, setHtml] = useState<string | null>(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    fetch(url)
      .then(r => r.arrayBuffer())
      .then(async (buf) => {
        const XLSX = await import('xlsx')
        const wb = XLSX.read(buf, { type: 'array' })
        const ws = wb.Sheets[wb.SheetNames[0]]
        setHtml(XLSX.utils.sheet_to_html(ws, { header: '', footer: '' }))
      })
      .catch(() => setError(true))
  }, [url])
  if (error) return <p className="text-center text-[13px] text-apple-light py-10">파일을 읽을 수 없습니다.</p>
  if (html === null) return <LoadingSpinnerSmall />
  return (
    <div
      className="overflow-auto max-h-[65vh] p-3 xlsx-preview"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

function DocxPreview({ url }: { url: string }) {
  const [html, setHtml] = useState<string | null>(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    fetch(url)
      .then(r => r.arrayBuffer())
      .then(async (buf) => {
        const mammoth = await import('mammoth')
        const result = await mammoth.convertToHtml({ arrayBuffer: buf })
        setHtml(result.value)
      })
      .catch(() => setError(true))
  }, [url])
  if (error) return <p className="text-center text-[13px] text-apple-light py-10">파일을 읽을 수 없습니다.</p>
  if (html === null) return <LoadingSpinnerSmall />
  return (
    <div
      className="prose prose-sm max-w-none p-5 overflow-auto max-h-[65vh] text-apple-dark"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

function PptxPreview({ name, folder }: { name: string; folder: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-12 px-6">
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="text-orange-400">
        <rect x="4" y="4" width="40" height="40" rx="8" fill="currentColor" opacity="0.1" />
        <path d="M14 14h12a6 6 0 0 1 0 12H14V14Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
        <path d="M14 26v8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <div className="text-center">
        <p className="text-[14px] font-medium text-apple-dark">PPTX 미리보기</p>
        <p className="text-[12px] text-apple-light mt-1 leading-relaxed">
          브라우저에서 직접 렌더링이 제한됩니다.<br />
          아래 버튼으로 다운로드 후 확인하세요.
        </p>
      </div>
      <a
        href={storageApi.download(name, folder)}
        download={name}
        className="px-4 py-2 rounded-xl text-[13px] font-medium bg-brand-600 hover:bg-brand-700 text-white transition-colors"
      >
        다운로드
      </a>
    </div>
  )
}

interface Props {
  name: string
  folder: string
  onClose: () => void
}

export default function FilePreviewModal({ name, folder, onClose }: Props) {
  const type = detectType(name)
  const url = storageApi.preview(name, folder)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const renderContent = () => {
    switch (type) {
      case 'image':
        return (
          <div className="flex items-center justify-center p-4 max-h-[70vh] overflow-auto">
            <img src={url} alt={name} className="max-w-full max-h-[65vh] object-contain rounded-lg" />
          </div>
        )
      case 'video':
        return (
          <div className="flex items-center justify-center p-4">
            <video src={url} controls className="max-w-full max-h-[65vh] rounded-lg" />
          </div>
        )
      case 'pdf':
        return (
          <iframe
            src={url}
            title={name}
            className="w-full rounded-b-2xl"
            style={{ height: '70vh', border: 'none' }}
          />
        )
      case 'text':
      case 'json':
        return <TextPreview url={url} />
      case 'markdown':
        return <MarkdownPreview url={url} />
      case 'csv':
        return <CsvPreview url={url} />
      case 'xlsx':
        return <XlsxPreview url={url} />
      case 'docx':
        return <DocxPreview url={url} />
      case 'pptx':
        return <PptxPreview name={name} folder={folder} />
      default:
        return (
          <div className="flex flex-col items-center gap-3 py-12">
            <p className="text-[13px] text-apple-light">미리보기를 지원하지 않는 형식입니다.</p>
            <a
              href={storageApi.download(name, folder)}
              download={name}
              className="px-4 py-2 rounded-xl text-[13px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark transition-colors"
            >
              다운로드
            </a>
          </div>
        )
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-4xl mx-auto flex flex-col overflow-hidden max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-apple-divider/60 flex-shrink-0">
          <div className="flex flex-col min-w-0 pr-4">
            <p className="text-[14px] font-semibold text-apple-dark truncate">{name}</p>
            <p className="text-[11px] text-apple-light capitalize">{type === 'unsupported' ? '미지원 형식' : type.toUpperCase()}</p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {type !== 'unsupported' && type !== 'pptx' && (
              <a
                href={storageApi.download(name, folder)}
                download={name}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[12px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark transition-colors"
              >
                <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
                  <path d="M7 2v7M4 6.5l3 3 3-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M2 10.5v1a.5.5 0 0 0 .5.5h9a.5.5 0 0 0 .5-.5v-1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                </svg>
                다운로드
              </a>
            )}
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-xl flex items-center justify-center text-apple-light hover:text-apple-dark hover:bg-apple-gray transition-colors"
            >
              <CloseIcon />
            </button>
          </div>
        </div>
        <div className="overflow-auto flex-1">
          {renderContent()}
        </div>
      </div>
    </div>
  )
}
