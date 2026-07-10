// frontend/src/presentation/components/storage/FilePreviewModal.tsx
import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github.css'
import { storageApi } from '@/infrastructure/api/storageApi'

type PreviewType =
  | 'image' | 'video' | 'pdf'
  | 'text' | 'markdown' | 'csv' | 'json'
  | 'xlsx' | 'docx' | 'pptx'
  | 'archive' | 'unsupported'

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
  if (['zip','tar','gz','tgz','bz2','xz','7z','rar','zst'].includes(ext)) return 'archive'
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

function PdfPreview({ url, name, folder }: { url: string; name: string; folder: string }) {
  const [failed, setFailed] = useState(false)
  const objRef = useRef<HTMLObjectElement>(null)

  useEffect(() => {
    const timer = setTimeout(() => {
      const obj = objRef.current
      if (obj && (obj.contentDocument === null || obj.contentDocument?.body?.childElementCount === 0)) {
        setFailed(true)
      }
    }, 3000)
    return () => clearTimeout(timer)
  }, [])

  if (failed) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 h-full px-6">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="text-red-400">
          <rect x="4" y="4" width="40" height="40" rx="8" fill="currentColor" opacity="0.1" />
          <path d="M14 6h14l10 10v26H14V6z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
          <path d="M28 6v10h10" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
          <path d="M18 28h12M18 32h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <div className="text-center">
          <p className="text-[14px] font-medium text-apple-dark">PDF 미리보기를 표시할 수 없습니다</p>
          <p className="text-[12px] text-apple-light mt-1">브라우저 설정에서 PDF 라이븷플러그인을 확인하거나 다운로드 해 주세요.</p>
        </div>
        <a
          href={storageApi.download(name, folder)}
          download={name}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-[13px] font-medium bg-brand-600 hover:bg-brand-700 text-white transition-colors"
        >
          다운로드
        </a>
      </div>
    )
  }

  return (
    <object
      ref={objRef}
      data={url}
      type="application/pdf"
      className="w-full h-full"
      onError={() => setFailed(true)}
    >
      <embed
        src={url}
        type="application/pdf"
        className="w-full h-full"
        onError={() => setFailed(true)}
      />
    </object>
  )
}

function PptxPreview({ name, folder }: { name: string; folder: string }) {
  const [useViewer, setUseViewer] = useState(true)
  const [viewerLoaded, setViewerLoaded] = useState(false)
  const downloadUrl = storageApi.download(name, folder)
  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  const fileUrl = `${origin}${storageApi.preview(name, folder)}`
  const googleViewerUrl = `https://docs.google.com/gview?url=${encodeURIComponent(fileUrl)}&embedded=true`

  return (
    <div className="flex flex-col w-full h-full">
      {useViewer ? (
        <>
          {!viewerLoaded && (
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <LoadingSpinnerSmall />
            </div>
          )}
          <iframe
            src={googleViewerUrl}
            className="w-full h-full"
            style={{ border: 'none' }}
            onLoad={() => setViewerLoaded(true)}
            onError={() => setUseViewer(false)}
            title={name}
            sandbox="allow-scripts allow-same-origin allow-popups"
          />
          <div className="flex items-center justify-between px-4 py-2 border-t border-apple-divider/60 bg-apple-gray/40 flex-shrink-0">
            <span className="text-[11px] text-apple-light">Google Docs Viewer 사용 중 &middot; 온라인 환경 필요</span>
            <button
              onClick={() => setUseViewer(false)}
              className="text-[11px] text-brand-600 hover:underline"
            >
              로컴 미리보기 시도
            </button>
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center gap-4 h-full px-6">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="text-orange-400">
            <rect x="4" y="4" width="40" height="40" rx="8" fill="currentColor" opacity="0.1" />
            <path d="M14 14h12a6 6 0 0 1 0 12H14V14Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
            <path d="M14 26v8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <div className="text-center">
            <p className="text-[14px] font-medium text-apple-dark">PPTX 미리보기</p>
            <p className="text-[12px] text-apple-light mt-1 leading-relaxed">
              브라우저에서 직접 렌더링이 제한됩니다.<br />
              다운로드 후 확인하세요.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => { setUseViewer(true); setViewerLoaded(false) }}
              className="px-4 py-2 rounded-xl text-[13px] font-medium border border-apple-divider hover:bg-apple-gray text-apple-dark transition-colors"
            >
              븷어 시도
            </button>
            <a
              href={downloadUrl}
              download={name}
              className="px-4 py-2 rounded-xl text-[13px] font-medium bg-brand-600 hover:bg-brand-700 text-white transition-colors"
            >
              다운로드
            </a>
          </div>
        </div>
      )}
    </div>
  )
}

function TextPreview({ url }: { url: string }) {
  const [content, setContent] = useState<string | null>(null)
  useEffect(() => {
    fetch(url)
      .then(r => r.arrayBuffer())
      .then(buf => {
        const tryDecode = (enc: string) => new TextDecoder(enc, { fatal: true }).decode(buf)
        let text = ''
        try { text = tryDecode('utf-8') }
        catch { try { text = tryDecode('euc-kr') } catch { text = new TextDecoder('utf-8', { fatal: false }).decode(buf) } }
        setContent(text)
      })
  }, [url])
  if (content === null) return <LoadingSpinnerSmall />
  return (
    <div className="flex justify-center w-full h-full overflow-auto">
      <pre className="text-[12px] leading-relaxed text-apple-dark whitespace-pre-wrap break-all font-mono p-8 w-full max-w-4xl">
        {content}
      </pre>
    </div>
  )
}

function MarkdownPreview({ url }: { url: string }) {
  const [content, setContent] = useState<string | null>(null)
  useEffect(() => {
    fetch(url)
      .then(r => r.arrayBuffer())
      .then(buf => {
        const tryDecode = (enc: string) => new TextDecoder(enc, { fatal: true }).decode(buf)
        let text = ''
        try { text = tryDecode('utf-8') }
        catch { try { text = tryDecode('euc-kr') } catch { text = new TextDecoder('utf-8', { fatal: false }).decode(buf) } }
        setContent(text)
      })
  }, [url])
  if (content === null) return <LoadingSpinnerSmall />
  return (
    <div className="overflow-auto h-full">
      <div className="max-w-3xl mx-auto px-8 py-8 markdown-body">
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
          {content}
        </ReactMarkdown>
      </div>
    </div>
  )
}

function CsvPreview({ url }: { url: string }) {
  const [rows, setRows] = useState<string[][] | null>(null)
  useEffect(() => {
    fetch(url)
      .then(r => r.arrayBuffer())
      .then(buf => {
        const tryDecode = (enc: string) => new TextDecoder(enc, { fatal: true }).decode(buf)
        let text = ''
        try { text = tryDecode('utf-8') }
        catch { try { text = tryDecode('euc-kr') } catch { text = new TextDecoder('utf-8', { fatal: false }).decode(buf) } }
        const lines = text.trim().split('\n')
        setRows(lines.map(l => l.split(',')))
      })
  }, [url])
  if (rows === null) return <LoadingSpinnerSmall />
  return (
    <div className="flex justify-center w-full h-full overflow-auto">
      <div className="p-6 w-full max-w-6xl">
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
        const wb = XLSX.read(buf, { type: 'array', codepage: 949 })
        const ws = wb.Sheets[wb.SheetNames[0]]
        setHtml(XLSX.utils.sheet_to_html(ws, { header: '', footer: '' }))
      })
      .catch(() => setError(true))
  }, [url])
  if (error) return <p className="text-center text-[13px] text-apple-light py-10">파일을 읽을 수 없습니다.</p>
  if (html === null) return <LoadingSpinnerSmall />
  return (
    <div className="flex justify-center w-full h-full overflow-auto">
      <div className="p-6 w-full max-w-6xl xlsx-preview" dangerouslySetInnerHTML={{ __html: html }} />
    </div>
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
    <div className="overflow-auto h-full">
      <div className="prose prose-sm max-w-3xl mx-auto px-8 py-8 text-apple-dark" dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  )
}

function ArchivePreview({ name, folder }: { name: string; folder: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 h-full px-6">
      <svg width="52" height="52" viewBox="0 0 52 52" fill="none" className="text-amber-500">
        <rect x="4" y="4" width="44" height="44" rx="10" fill="currentColor" opacity="0.1" />
        <path d="M20 10h12v6h-12zM20 16h12v6h-12zM20 22h12v6h-12z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
        <path d="M14 10h6v32H14a2 2 0 0 1-2-2V12a2 2 0 0 1 2-2zM38 10h-6v32h6a2 2 0 0 0 2-2V12a2 2 0 0 0-2-2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        <circle cx="26" cy="30" r="3" stroke="currentColor" strokeWidth="2" />
      </svg>
      <div className="text-center">
        <p className="text-[15px] font-semibold text-apple-dark">{name}</p>
        <p className="text-[12px] text-apple-light mt-1 leading-relaxed">
          압욹 파일은 브라우저에서 직접 열 수 없습니다.<br />
          다운로드 후 압욹을 해제하세요.
        </p>
      </div>
      <a
        href={storageApi.download(name, folder)}
        download={name}
        className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-[13px] font-medium bg-brand-600 hover:bg-brand-700 text-white transition-colors"
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
    document.body.style.overflow = 'hidden'
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', handler)
    }
  }, [onClose])

  const renderContent = () => {
    switch (type) {
      case 'image':
        return (
          <div className="flex items-center justify-center w-full h-full p-6 bg-black/5">
            <img src={url} alt={name} className="max-w-full max-h-full object-contain" style={{ width: 'auto', height: 'auto' }} />
          </div>
        )
      case 'video':
        return (
          <div className="flex items-center justify-center w-full h-full bg-black">
            <video src={url} controls autoPlay className="max-w-full max-h-full" style={{ width: 'auto', height: 'auto' }} />
          </div>
        )
      case 'pdf':
        return <PdfPreview url={url} name={name} folder={folder} />
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
      case 'archive':
        return <ArchivePreview name={name} folder={folder} />
      default:
        return (
          <div className="flex flex-col items-center justify-center gap-3 h-full">
            <p className="text-[13px] text-apple-light">미리보기를 지원하지 않는 형식입니다.</p>
            <a href={storageApi.download(name, folder)} download={name} className="px-4 py-2 rounded-xl text-[13px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark transition-colors">
              다운로드
            </a>
          </div>
        )
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-white">
      <div className="flex items-center justify-between px-5 py-3 border-b border-apple-divider/60 flex-shrink-0 bg-white">
        <div className="flex flex-col min-w-0 pr-4">
          <p className="text-[14px] font-semibold text-apple-dark truncate">{name}</p>
          <p className="text-[11px] text-apple-light capitalize">
            {type === 'unsupported' ? '미지원 형식'
              : type === 'archive' ? '압욹 파일'
              : type.toUpperCase()}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
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
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-xl flex items-center justify-center text-apple-light hover:text-apple-dark hover:bg-apple-gray transition-colors"
          >
            <CloseIcon />
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-hidden relative">
        {renderContent()}
      </div>
    </div>
  )
}
