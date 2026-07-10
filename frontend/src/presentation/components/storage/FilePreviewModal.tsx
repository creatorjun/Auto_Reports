// frontend/src/presentation/components/storage/FilePreviewModal.tsx
import { useEffect, useRef, useState, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github.css'
import { storageApi } from '@/infrastructure/api/storageApi'

const PDFJS_VERSION = '4.4.168'
const PDFJS_CDN = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${PDFJS_VERSION}`

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
    <div className="flex items-center justify-center h-full">
      <svg className="animate-spin w-8 h-8 text-brand-500" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeDashoffset="12" />
      </svg>
    </div>
  )
}

let _pdfjsLib: any = null

async function getPdfjsLib() {
  if (_pdfjsLib) return _pdfjsLib
  const lib = await import('pdfjs-dist')
  lib.GlobalWorkerOptions.workerSrc = `${PDFJS_CDN}/build/pdf.worker.min.mjs`
  _pdfjsLib = lib
  return lib
}

function PdfViewer({ url }: { url: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [totalPages, setTotalPages] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pdfRef = useRef<any>(null)
  const renderTaskRef = useRef<any>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    pdfRef.current = null

    const load = async () => {
      try {
        const pdfjsLib = await getPdfjsLib()
        const loadingTask = pdfjsLib.getDocument({
          url,
          cMapUrl: `${PDFJS_CDN}/cmaps/`,
          cMapPacked: true,
          withCredentials: false,
        })
        const pdf = await loadingTask.promise
        if (cancelled) { pdf.destroy(); return }
        pdfRef.current = pdf
        setTotalPages(pdf.numPages)
        setCurrentPage(1)
        setLoading(false)
      } catch (e: any) {
        if (!cancelled) {
          const msg = e?.message ?? String(e)
          setError(`PDF 로드 실패: ${msg}`)
        }
      }
    }
    load()
    return () => {
      cancelled = true
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel()
        renderTaskRef.current = null
      }
    }
  }, [url])

  const renderPage = useCallback(async (pageNum: number) => {
    if (!pdfRef.current || !canvasRef.current) return
    if (renderTaskRef.current) {
      renderTaskRef.current.cancel()
      renderTaskRef.current = null
    }
    try {
      const page = await pdfRef.current.getPage(pageNum)
      const container = containerRef.current
      const containerWidth = container ? container.clientWidth - 32 : 800
      const viewport = page.getViewport({ scale: 1 })
      const scale = Math.min(containerWidth / viewport.width, 2)
      const scaledViewport = page.getViewport({ scale })
      const canvas = canvasRef.current
      if (!canvas) return
      const dpr = window.devicePixelRatio || 1
      canvas.width = scaledViewport.width * dpr
      canvas.height = scaledViewport.height * dpr
      canvas.style.width = `${scaledViewport.width}px`
      canvas.style.height = `${scaledViewport.height}px`
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.scale(dpr, dpr)
      const task = page.render({ canvasContext: ctx, viewport: scaledViewport })
      renderTaskRef.current = task
      await task.promise
      renderTaskRef.current = null
    } catch (e: any) {
      if (e?.name !== 'RenderingCancelledException') {
        console.error('PDF render error:', e)
      }
    }
  }, [])

  useEffect(() => {
    if (!loading && !error) renderPage(currentPage)
  }, [loading, error, currentPage, renderPage])

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 h-full px-6">
        <p className="text-[13px] text-apple-light text-center">{error}</p>
      </div>
    )
  }

  return (
    <div ref={containerRef} className="flex flex-col w-full h-full overflow-hidden">
      {loading && <LoadingSpinnerSmall />}
      <div className="flex-1 overflow-auto flex justify-center bg-gray-100 p-4">
        <canvas ref={canvasRef} className="shadow-md" style={{ display: loading ? 'none' : 'block' }} />
      </div>
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 py-2 border-t border-apple-divider/60 bg-white flex-shrink-0">
          <button
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
            className="px-3 py-1 rounded-lg text-[12px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark disabled:opacity-40 transition-colors"
          >
            ← 이전
          </button>
          <span className="text-[12px] text-apple-light">{currentPage} / {totalPages}</span>
          <button
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage >= totalPages}
            className="px-3 py-1 rounded-lg text-[12px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark disabled:opacity-40 transition-colors"
          >
            다음 →
          </button>
        </div>
      )}
    </div>
  )
}

function PptxPreview({ name, folder }: { name: string; folder: string }) {
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [errMsg, setErrMsg] = useState('')

  useEffect(() => {
    const p = new URLSearchParams({ name, ...(folder ? { folder } : {}) })
    const token = localStorage.getItem('auth-storage')
      ? JSON.parse(localStorage.getItem('auth-storage') ?? '{}')?.state?.accessToken
      : null
    if (token) p.set('_t', token)
    const url = `/api/v1/storage/preview-converted?${p.toString()}`
    let objUrl: string | null = null

    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.blob()
      })
      .then(blob => {
        objUrl = URL.createObjectURL(blob)
        setPdfUrl(objUrl)
        setStatus('ready')
      })
      .catch((e) => { setErrMsg(e?.message ?? ''); setStatus('error') })

    return () => { if (objUrl) URL.revokeObjectURL(objUrl) }
  }, [name, folder])

  if (status === 'loading') {
    return (
      <div className="flex flex-col items-center justify-center gap-3 h-full">
        <svg className="animate-spin w-8 h-8 text-brand-500" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeDashoffset="12" />
        </svg>
        <p className="text-[13px] text-apple-light">PPTX → PDF 변환 중...</p>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="flex flex-col items-center justify-center gap-4 h-full px-6">
        <div className="text-center">
          <p className="text-[14px] font-medium text-apple-dark">변환 실패</p>
          <p className="text-[12px] text-apple-light mt-1">{errMsg || '서버에서 PDF 변환에 실패했습니다.'}</p>
        </div>
        <a href={storageApi.download(name, folder)} download={name}
          className="px-4 py-2 rounded-xl text-[13px] font-medium bg-brand-600 hover:bg-brand-700 text-white transition-colors">
          다운로드
        </a>
      </div>
    )
  }

  return <PdfViewer url={pdfUrl!} />
}

function TextPreview({ url }: { url: string }) {
  const [content, setContent] = useState<string | null>(null)
  useEffect(() => {
    fetch(url).then(r => r.arrayBuffer()).then(buf => {
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
      <pre className="text-[12px] leading-relaxed text-apple-dark whitespace-pre-wrap break-all font-mono p-8 w-full max-w-4xl">{content}</pre>
    </div>
  )
}

function MarkdownPreview({ url }: { url: string }) {
  const [content, setContent] = useState<string | null>(null)
  useEffect(() => {
    fetch(url).then(r => r.arrayBuffer()).then(buf => {
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
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>{content}</ReactMarkdown>
      </div>
    </div>
  )
}

function CsvPreview({ url }: { url: string }) {
  const [rows, setRows] = useState<string[][] | null>(null)
  useEffect(() => {
    fetch(url).then(r => r.arrayBuffer()).then(buf => {
      const tryDecode = (enc: string) => new TextDecoder(enc, { fatal: true }).decode(buf)
      let text = ''
      try { text = tryDecode('utf-8') }
      catch { try { text = tryDecode('euc-kr') } catch { text = new TextDecoder('utf-8', { fatal: false }).decode(buf) } }
      setRows(text.trim().split('\n').map(l => l.split(',')))
    })
  }, [url])
  if (rows === null) return <LoadingSpinnerSmall />
  return (
    <div className="flex justify-center w-full h-full overflow-auto">
      <div className="p-6 w-full max-w-6xl">
        <table className="text-[12px] border-collapse w-full">
          <thead><tr>{rows[0]?.map((h,i) => <th key={i} className="border border-apple-divider px-3 py-1.5 bg-apple-gray text-apple-dark font-semibold text-left whitespace-nowrap">{h}</th>)}</tr></thead>
          <tbody>{rows.slice(1).map((row,i) => <tr key={i} className="even:bg-apple-gray/40">{row.map((cell,j) => <td key={j} className="border border-apple-divider/60 px-3 py-1 text-apple-dark whitespace-nowrap">{cell}</td>)}</tr>)}</tbody>
        </table>
      </div>
    </div>
  )
}

function XlsxPreview({ url }: { url: string }) {
  const [html, setHtml] = useState<string | null>(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    fetch(url).then(r => r.arrayBuffer()).then(async buf => {
      const XLSX = await import('xlsx')
      const wb = XLSX.read(buf, { type: 'array', codepage: 949 })
      const ws = wb.Sheets[wb.SheetNames[0]]
      setHtml(XLSX.utils.sheet_to_html(ws, { header: '', footer: '' }))
    }).catch(() => setError(true))
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
    fetch(url).then(r => r.arrayBuffer()).then(async buf => {
      const mammoth = await import('mammoth')
      const result = await mammoth.convertToHtml({ arrayBuffer: buf })
      setHtml(result.value)
    }).catch(() => setError(true))
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
      <div className="text-center">
        <p className="text-[15px] font-semibold text-apple-dark">{name}</p>
        <p className="text-[12px] text-apple-light mt-1 leading-relaxed">압축 파일은 브라우저에서 직접 열 수 없습니다.<br />다운로드 후 압축을 해제하세요.</p>
      </div>
      <a href={storageApi.download(name, folder)} download={name}
        className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-[13px] font-medium bg-brand-600 hover:bg-brand-700 text-white transition-colors">
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
      case 'pdf': return <PdfViewer url={url} />
      case 'text':
      case 'json': return <TextPreview url={url} />
      case 'markdown': return <MarkdownPreview url={url} />
      case 'csv': return <CsvPreview url={url} />
      case 'xlsx': return <XlsxPreview url={url} />
      case 'docx': return <DocxPreview url={url} />
      case 'pptx': return <PptxPreview name={name} folder={folder} />
      case 'archive': return <ArchivePreview name={name} folder={folder} />
      default:
        return (
          <div className="flex flex-col items-center justify-center gap-3 h-full">
            <p className="text-[13px] text-apple-light">미리보기를 지원하지 않는 형식입니다.</p>
            <a href={storageApi.download(name, folder)} download={name}
              className="px-4 py-2 rounded-xl text-[13px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark transition-colors">
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
              : type === 'archive' ? '압축 파일'
              : type === 'pptx' ? 'PPTX (PDF 변환 미리보기)'
              : type.toUpperCase()}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <a href={storageApi.download(name, folder)} download={name}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[12px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark transition-colors">
            <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
              <path d="M7 2v7M4 6.5l3 3 3-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M2 10.5v1a.5.5 0 0 0 .5.5h9a.5.5 0 0 0 .5-.5v-1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
            </svg>
            다운로드
          </a>
          <button onClick={onClose}
            className="w-8 h-8 rounded-xl flex items-center justify-center text-apple-light hover:text-apple-dark hover:bg-apple-gray transition-colors">
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
