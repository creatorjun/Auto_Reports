// frontend/src/presentation/components/storage/FilePreviewModal.tsx
import { Fragment, useEffect, useRef, useState, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github.css'
import '@/presentation/styles/markdown.css'
import type {
  BinaryObjectUrl,
  StorageGateway,
} from '@/application/ports/ApplicationServices'
import { useApplicationServices } from '@/presentation/context/ApplicationServicesContext'

type PreviewType =
  | 'image' | 'video' | 'pdf'
  | 'text' | 'markdown' | 'csv' | 'json'
  | 'xlsx' | 'docx' | 'pptx'
  | 'archive' | 'unsupported'

interface ContentPreviewProps {
  name: string
  folder: string
  storage: StorageGateway
}

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

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)

const FULLSCREEN_HINT = isMac ? '⌘⇧F' : 'F11'

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M4 4l10 10M14 4L4 14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

function LoadingSpinnerSmall() {
  return (
    <div role="status" aria-label="미리보기 불러오는 중" className="flex items-center justify-center h-full bg-black/60">
      <svg className="animate-spin w-8 h-8 text-white" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeDashoffset="12" />
      </svg>
    </div>
  )
}

function previewErrorMessage(error: unknown): string {
  return error instanceof Error && error.message && error.message !== 'Request failed'
    ? error.message
    : '파일을 불러오지 못했습니다. 잠시 후 다시 열어 주세요.'
}

function PreviewError({ message }: { message: string }) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center gap-2 h-full bg-black/60 px-6 text-center">
      <p className="text-[14px] font-medium text-white">미리보기를 불러올 수 없습니다.</p>
      <p className="text-[12px] text-white/70">{message}</p>
    </div>
  )
}

function decodePreviewText(buffer: ArrayBuffer): string {
  const decode = (encoding: string) => new TextDecoder(encoding, { fatal: true }).decode(buffer)
  try { return decode('utf-8') }
  catch {
    try { return decode('euc-kr') }
    catch { return new TextDecoder('utf-8').decode(buffer) }
  }
}

function parsePreviewCsv(buffer: ArrayBuffer): string[][] {
  return decodePreviewText(buffer).trim().split('\n').map(line => line.split(','))
}

async function parsePreviewWorkbook(buffer: ArrayBuffer): Promise<{ name: string; html: string }[]> {
  const XLSX = await import('xlsx')
  const workbook = XLSX.read(buffer, { type: 'array', codepage: 949, cellStyles: true })
  if (workbook.SheetNames.length === 0) throw new Error('표시할 시트가 없습니다.')
  return workbook.SheetNames.map(name => ({
    name,
    html: XLSX.utils.sheet_to_html(workbook.Sheets[name], { header: '', footer: '' }),
  }))
}

async function parsePreviewDocument(buffer: ArrayBuffer): Promise<string> {
  const mammoth = await import('mammoth')
  return (await mammoth.convertToHtml({ arrayBuffer: buffer })).value
}

function usePreviewContent<T>(
  { name, folder, storage }: ContentPreviewProps,
  parse: (buffer: ArrayBuffer) => T | Promise<T>,
) {
  const [content, setContent] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    setContent(null)
    setError(null)
    const load = async () => {
      try {
        const binary = await storage.readPreview(name, folder)
        if (!active) return
        const buffer = await binary.read()
        if (!active) return
        const result = await parse(buffer)
        if (active) setContent(result)
      } catch (cause: unknown) {
        if (active) setError(previewErrorMessage(cause))
      }
    }
    void load()
    return () => { active = false }
  }, [folder, name, storage, parse])
  return { content, error }
}

function MediaPreview({ url, name, type }: { url: string; name: string; type: 'image' | 'video' }) {
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const timerRef = useRef<number | null>(null)
  const finish = (next: 'ready' | 'error') => {
    if (timerRef.current !== null) window.clearTimeout(timerRef.current)
    timerRef.current = null
    setStatus(next)
  }
  useEffect(() => {
    setStatus('loading')
    timerRef.current = window.setTimeout(() => finish('error'), 30_000)
    return () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [url])
  if (status === 'error') return <PreviewError message="파일을 불러오지 못했습니다. 잠시 후 다시 열거나 다운로드 후 확인해 주세요." />
  return (
    <div className="relative flex items-center justify-center w-full h-full bg-black/60">
      {status === 'loading' && <div className="absolute inset-0"><LoadingSpinnerSmall /></div>}
      {type === 'image' ? (
        <img src={url} alt={name} onLoad={() => finish('ready')} onError={() => finish('error')}
          className="max-w-full max-h-full object-contain shadow-2xl" style={{ width: 'auto', height: 'auto', visibility: status === 'loading' ? 'hidden' : 'visible' }} />
      ) : (
        <video src={url} controls autoPlay onLoadedData={() => finish('ready')} onError={() => finish('error')}
          className="max-w-full max-h-full" style={{ visibility: status === 'loading' ? 'hidden' : 'visible' }} />
      )}
    </div>
  )
}

let _pdfjsLib: any = null

async function getPdfjsLib() {
  if (_pdfjsLib) return _pdfjsLib
  const lib = await import('pdfjs-dist')
  const version: string = (lib as any).version ?? lib.GlobalWorkerOptions.workerSrc ?? ''
  if (version) {
    lib.GlobalWorkerOptions.workerSrc =
      `https://cdn.jsdelivr.net/npm/pdfjs-dist@${version}/build/pdf.worker.min.mjs`
  } else {
    lib.GlobalWorkerOptions.workerSrc = new URL(
      'pdfjs-dist/build/pdf.worker.min.mjs',
      import.meta.url,
    ).href
  }
  _pdfjsLib = lib
  return lib
}

interface PdfViewerProps {
  url: string
  onPageChange?: (page: number, total: number) => void
}

function PdfViewer({ url, onPageChange }: PdfViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [totalPages, setTotalPages] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pdfRef = useRef<any>(null)
  const renderTaskRef = useRef<any>(null)
  const renderGenerationRef = useRef(0)

  useEffect(() => {
    let cancelled = false
    let loadingTask: any = null
    setLoading(true)
    setError(null)
    setTotalPages(0)
    setCurrentPage(1)
    pdfRef.current = null
    const timer = window.setTimeout(() => {
      cancelled = true
      setLoading(false)
      setError('파일을 불러오는 시간이 초과되었습니다. 잠시 후 다시 열어 주세요.')
      void loadingTask?.destroy().catch(() => {})
    }, 30_000)

    const load = async () => {
      try {
        const pdfjsLib = await getPdfjsLib()
        if (cancelled) return
        const version: string = (pdfjsLib as any).version ?? ''
        const cMapUrl = version
          ? `https://cdn.jsdelivr.net/npm/pdfjs-dist@${version}/cmaps/`
          : 'https://cdn.jsdelivr.net/npm/pdfjs-dist/cmaps/'
        loadingTask = pdfjsLib.getDocument({
          url,
          cMapUrl,
          cMapPacked: true,
          withCredentials: false,
        })
        const pdf = await loadingTask.promise
        if (cancelled) return
        if (pdf.numPages === 0) throw new Error('표시할 PDF 페이지가 없습니다.')
        pdfRef.current = pdf
        setTotalPages(pdf.numPages)
        setCurrentPage(1)
        setLoading(false)
      } catch (cause: unknown) {
        if (!cancelled) {
          setLoading(false)
          setError(previewErrorMessage(cause))
        }
      } finally {
        window.clearTimeout(timer)
      }
    }
    load()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
      renderGenerationRef.current++
      renderTaskRef.current?.cancel()
      renderTaskRef.current = null
      pdfRef.current = null
      void loadingTask?.destroy().catch(() => {})
    }
  }, [url])

  useEffect(() => {
    if (!loading && !error && onPageChange) {
      onPageChange(currentPage, totalPages)
    }
  }, [loading, error, currentPage, totalPages, onPageChange])

  const renderPage = useCallback(async (pageNum: number) => {
    const pdf = pdfRef.current
    if (!pdf || !canvasRef.current) return
    const generation = ++renderGenerationRef.current
    renderTaskRef.current?.cancel()
    renderTaskRef.current = null
    try {
      const page = await pdf.getPage(pageNum)
      if (pdfRef.current !== pdf || generation !== renderGenerationRef.current) return
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
      if (!ctx) throw new Error('이 브라우저에서 PDF를 표시할 수 없습니다. 다운로드 후 확인해 주세요.')
      ctx.scale(dpr, dpr)
      const task = page.render({ canvasContext: ctx, viewport: scaledViewport })
      renderTaskRef.current = task
      await task.promise
      if (renderTaskRef.current === task) renderTaskRef.current = null
    } catch (e: any) {
      if (e?.name !== 'RenderingCancelledException' && pdfRef.current === pdf && generation === renderGenerationRef.current) {
        setError(previewErrorMessage(e))
      }
    }
  }, [])

  useEffect(() => {
    if (!loading && !error) renderPage(currentPage)
  }, [loading, error, currentPage, renderPage])

  useEffect(() => {
    if (loading || error || totalPages <= 1) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        e.stopPropagation()
        setCurrentPage(p => Math.max(1, p - 1))
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        e.stopPropagation()
        setCurrentPage(p => Math.min(totalPages, p + 1))
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [loading, error, totalPages])

  if (error) {
    return <PreviewError message={error} />
  }

  return (
    <div ref={containerRef} className="flex flex-col w-full h-full overflow-hidden">
      {loading && <LoadingSpinnerSmall />}
      <div className="flex-1 overflow-auto flex justify-center bg-black/60 p-6">
        <canvas ref={canvasRef} className="shadow-2xl rounded" style={{ display: loading ? 'none' : 'block' }} />
      </div>
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 py-2 border-t border-apple-divider/60 bg-apple-surface flex-shrink-0">
          <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage <= 1}
            className="px-3 py-1 rounded-lg text-[12px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark disabled:opacity-40 transition-colors">
            ← 이전
          </button>
          <span className="text-[12px] text-apple-light tabular-nums">{currentPage} / {totalPages}</span>
          <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage >= totalPages}
            className="px-3 py-1 rounded-lg text-[12px] font-medium bg-apple-gray hover:bg-apple-divider/40 text-apple-dark disabled:opacity-40 transition-colors">
            다음 →
          </button>
        </div>
      )}
    </div>
  )
}

function PptxPreview({ name, folder, storage, onPageChange }: { name: string; folder: string; storage: StorageGateway; onPageChange?: (page: number, total: number) => void }) {
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [errMsg, setErrMsg] = useState('')

  useEffect(() => {
    let active = true
    let objectUrl: BinaryObjectUrl | null = null
    setStatus('loading')
    setPdfUrl(null)
    setErrMsg('')

    storage.convertPreview(name, folder)
      .then((content) => {
        if (!active) return
        objectUrl = content.createObjectUrl()
        setPdfUrl(objectUrl.url)
        setStatus('ready')
      })
      .catch((error: unknown) => {
        if (!active) return
        setErrMsg(error instanceof Error ? error.message : '알 수 없는 오류')
        setStatus('error')
      })

    return () => {
      active = false
      objectUrl?.close()
    }
  }, [folder, name, storage])

  if (status === 'loading') {
    return (
      <div className="flex flex-col items-center justify-center gap-3 h-full bg-black/60">
        <svg className="animate-spin w-8 h-8 text-white" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeDashoffset="12" />
        </svg>
        <p className="text-[13px] text-white/70">PPTX → PDF 변환 중...</p>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="flex flex-col items-center justify-center gap-4 h-full bg-black/60 px-6">
        <div className="text-center">
          <p className="text-[14px] font-medium text-white">변환 실패</p>
          <p className="text-[12px] text-white/60 mt-1">{errMsg || '서버에서 PDF 변환에 실패했습니다.'}</p>
        </div>
        <a href={storage.download(name, folder)} download={name}
          className="px-4 py-2 rounded-xl text-[13px] font-medium bg-white/20 hover:bg-white/30 text-white transition-colors">
          다운로드
        </a>
      </div>
    )
  }

  return <PdfViewer url={pdfUrl!} onPageChange={onPageChange} />
}

function TextPreview({ name, folder, storage }: ContentPreviewProps) {
  const { content, error } = usePreviewContent({ name, folder, storage }, decodePreviewText)
  if (error) return <PreviewError message={error} />
  if (content === null) return <LoadingSpinnerSmall />
  return (
    <div className="w-full h-full overflow-auto bg-black/60">
      <pre className="text-[12px] leading-relaxed text-white/90 whitespace-pre-wrap break-all font-mono p-8 min-h-full">{content}</pre>
    </div>
  )
}

function MarkdownPreview({ name, folder, storage }: ContentPreviewProps) {
  const { content, error } = usePreviewContent({ name, folder, storage }, decodePreviewText)
  if (error) return <PreviewError message={error} />
  if (content === null) return <LoadingSpinnerSmall />
  return (
    <div className="overflow-auto h-full bg-apple-bg">
      <div className="max-w-3xl mx-auto my-8 px-10 py-10 bg-apple-surface rounded-2xl shadow-xl markdown-body">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[[rehypeHighlight, { detect: true }]]}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  )
}

function CsvPreview({ name, folder, storage }: ContentPreviewProps) {
  const { content: rows, error } = usePreviewContent({ name, folder, storage }, parsePreviewCsv)
  if (error) return <PreviewError message={error} />
  if (rows === null) return <LoadingSpinnerSmall />
  return (
    <div className="flex justify-center w-full h-full overflow-auto bg-black/60">
      <div className="p-6 w-full max-w-6xl">
        <table className="text-[12px] border-collapse w-full bg-apple-surface rounded-xl overflow-hidden shadow-2xl">
          <thead><tr>{rows[0]?.map((h,i)=><th key={i} className="border border-apple-divider px-3 py-1.5 bg-apple-gray text-apple-dark font-semibold text-left whitespace-nowrap">{h}</th>)}</tr></thead>
          <tbody>{rows.slice(1).map((row,i)=><tr key={i} className="even:bg-apple-gray/40">{row.map((cell,j)=><td key={j} className="border border-apple-divider/60 px-3 py-1 text-apple-dark whitespace-nowrap">{cell}</td>)}</tr>)}</tbody>
        </table>
      </div>
    </div>
  )
}

const XLSX_TABLE_STYLE = `
  .xlsx-preview table {
    border-collapse: collapse;
    width: 100%;
    font-size: 12px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  .xlsx-preview td, .xlsx-preview th {
    border: 1px solid rgb(var(--color-gray-300));
    padding: 4px 8px;
    white-space: nowrap;
    vertical-align: middle;
    max-width: 320px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .xlsx-preview tr:first-child td,
  .xlsx-preview tr:first-child th {
    background: rgb(var(--color-gray-100));
    font-weight: 600;
    position: sticky;
    top: 0;
    z-index: 1;
  }
  .xlsx-preview tr:nth-child(even) td {
    background: rgb(var(--color-gray-50));
  }
  .xlsx-preview tr:hover td {
    background: rgb(var(--color-blue-50));
  }
`

function XlsxPreview({ name, folder, storage }: ContentPreviewProps) {
  const { content: sheets, error } = usePreviewContent({ name, folder, storage }, parsePreviewWorkbook)
  const [activeSheet, setActiveSheet] = useState(0)
  useEffect(() => { setActiveSheet(0) }, [folder, name, storage])
  if (error) return <PreviewError message={error} />
  if (sheets === null) return <LoadingSpinnerSmall />

  return (
    <div className="flex flex-col w-full h-full bg-black/60">
      <style>{XLSX_TABLE_STYLE}</style>
      {sheets.length > 1 && (
        <div className="flex gap-1 px-4 pt-3 pb-0 flex-shrink-0 overflow-x-auto">
          {sheets.map((s, i) => (
            <button key={i} onClick={() => setActiveSheet(i)}
              className={`px-3 py-1.5 rounded-t-lg text-[12px] font-medium transition-colors whitespace-nowrap ${
                i === activeSheet
                  ? 'bg-white text-apple-dark shadow'
                  : 'bg-white/20 text-white/70 hover:bg-white/30'
              }`}>
              {s.name}
            </button>
          ))}
        </div>
      )}
      <div className="flex-1 overflow-auto bg-apple-surface text-apple-dark rounded-xl shadow-2xl m-4 mt-0">
        <div className="p-2 xlsx-preview" dangerouslySetInnerHTML={{ __html: sheets[activeSheet]?.html ?? '' }} />
      </div>
    </div>
  )
}

function DocxPreview({ name, folder, storage }: ContentPreviewProps) {
  const { content: html, error } = usePreviewContent({ name, folder, storage }, parsePreviewDocument)
  if (error) return <PreviewError message={error} />
  if (html === null) return <LoadingSpinnerSmall />
  return (
    <div className="overflow-auto h-full bg-apple-bg">
      <div className="max-w-3xl mx-auto my-8 px-10 py-10 bg-apple-surface rounded-2xl shadow-xl prose prose-sm text-apple-dark" dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  )
}

function ArchivePreview({ name, folder, storage }: { name: string; folder: string; storage: StorageGateway }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 h-full bg-black/60 px-6">
      <div className="text-center">
        <p className="text-[15px] font-semibold text-white">{name}</p>
        <p className="text-[12px] text-white/60 mt-1 leading-relaxed">압축 파일은 브라우저에서 직접 열 수 없습니다.<br />다운로드 후 압축을 해제하세요.</p>
      </div>
      <a href={storage.download(name, folder)} download={name}
        className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-[13px] font-medium bg-white/20 hover:bg-white/30 text-white transition-colors">
        다운로드
      </a>
    </div>
  )
}

interface Props {
  name: string
  folder: string
  fileList?: string[]
  onNavigate?: (name: string) => void
  onClose: () => void
}

export default function FilePreviewModal({ name, folder, fileList = [], onNavigate, onClose }: Props) {
  const { storage } = useApplicationServices()
  const type = detectType(name)
  const url = storage.preview(name, folder)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [pdfPageInfo, setPdfPageInfo] = useState<{ current: number; total: number } | null>(null)
  useEffect(() => { setPdfPageInfo(null) }, [folder, name])

  const currentIndex = fileList.indexOf(name)
  const hasPrev = currentIndex > 0
  const hasNext = currentIndex >= 0 && currentIndex < fileList.length - 1

  const isPdf = type === 'pdf' || type === 'pptx'
  const isPdfMultiPage = isPdf && pdfPageInfo !== null && pdfPageInfo.total > 1

  const handlePrev = useCallback(() => {
    if (hasPrev && onNavigate) onNavigate(fileList[currentIndex - 1])
  }, [hasPrev, onNavigate, fileList, currentIndex])

  const handleNext = useCallback(() => {
    if (hasNext && onNavigate) onNavigate(fileList[currentIndex + 1])
  }, [hasNext, onNavigate, fileList, currentIndex])

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {})
    } else {
      document.exitFullscreen().catch(() => {})
    }
  }, [])

  useEffect(() => {
    const onFsChange = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', onFsChange)
    return () => document.removeEventListener('fullscreenchange', onFsChange)
  }, [])

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (document.fullscreenElement) {
          document.exitFullscreen().catch(() => {})
        } else {
          onClose()
        }
        return
      }
      const isFullscreenKey = isMac
        ? (e.metaKey && e.shiftKey && e.key === 'f')
        : (e.key === 'F11')
      if (isFullscreenKey) {
        e.preventDefault()
        toggleFullscreen()
        return
      }
      if (isPdfMultiPage) return
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        handlePrev()
        return
      }
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        handleNext()
        return
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose, toggleFullscreen, handlePrev, handleNext, isPdfMultiPage])

  const handlePdfPageChange = useCallback((current: number, total: number) => {
    setPdfPageInfo({ current, total })
  }, [])

  const renderContent = () => {
    switch (type) {
      case 'image':
      case 'video':
        return <MediaPreview url={url} name={name} type={type} />
      case 'pdf': return <PdfViewer url={url} onPageChange={handlePdfPageChange} />
      case 'text':
      case 'json': return <TextPreview name={name} folder={folder} storage={storage} />
      case 'markdown': return <MarkdownPreview name={name} folder={folder} storage={storage} />
      case 'csv': return <CsvPreview name={name} folder={folder} storage={storage} />
      case 'xlsx': return <XlsxPreview name={name} folder={folder} storage={storage} />
      case 'docx': return <DocxPreview name={name} folder={folder} storage={storage} />
      case 'pptx': return <PptxPreview name={name} folder={folder} storage={storage} onPageChange={handlePdfPageChange} />
      case 'archive': return <ArchivePreview name={name} folder={folder} storage={storage} />
      default:
        return (
          <div className="flex flex-col items-center justify-center gap-3 h-full bg-black/60">
            <p className="text-[13px] text-white/60">미리보기를 지원하지 않는 형식입니다.</p>
            <a href={storage.download(name, folder)} download={name}
              className="px-4 py-2 rounded-xl text-[13px] font-medium bg-white/20 hover:bg-white/30 text-white transition-colors">
              다운로드
            </a>
          </div>
        )
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-apple-surface">
      <div className="flex items-center justify-between px-5 py-3 border-b border-apple-divider/60 flex-shrink-0 bg-apple-surface">
        <div className="flex items-center gap-3 min-w-0">
          {fileList.length > 1 && (
            <div className="flex items-center gap-1 flex-shrink-0">
              <button
                onClick={handlePrev}
                disabled={!hasPrev}
                className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-apple-dark hover:bg-apple-gray transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                title="이전 파일 (←)">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
              <span className="text-[11px] text-apple-light tabular-nums">{currentIndex + 1} / {fileList.length}</span>
              <button
                onClick={handleNext}
                disabled={!hasNext}
                className="w-7 h-7 rounded-lg flex items-center justify-center text-apple-light hover:text-apple-dark hover:bg-apple-gray transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                title="다음 파일 (→)">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
          )}
          <div className="flex flex-col min-w-0">
            <p className="text-[14px] font-semibold text-apple-dark truncate">{name}</p>
            <p className="text-[11px] text-apple-light capitalize">
              {type === 'unsupported' ? '미지원 형식'
                : type === 'archive' ? '압축 파일'
                : type === 'pptx' ? 'PPTX (PDF 변환 미리보기)'
                : type.toUpperCase()}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={toggleFullscreen}
            className="w-8 h-8 rounded-xl flex items-center justify-center text-apple-light hover:text-apple-dark hover:bg-apple-gray transition-colors"
            title={isFullscreen ? `전체화면 종료 (${FULLSCREEN_HINT})` : `전체화면 (${FULLSCREEN_HINT})`}>
            {isFullscreen ? (
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                <path d="M5.5 1.5v4h-4M9.5 1.5v4h4M5.5 13.5v-4h-4M9.5 13.5v-4h4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : (
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                <path d="M1.5 5.5v-4h4M13.5 5.5v-4h-4M1.5 9.5v4h4M13.5 9.5v4h-4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </button>
          <a href={storage.download(name, folder)} download={name}
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
        <Fragment key={JSON.stringify([folder, name])}>{renderContent()}</Fragment>
        {fileList.length > 1 && !isPdfMultiPage && (
          <>
            {hasPrev && (
              <button
                onClick={handlePrev}
                className="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/40 hover:bg-black/60 flex items-center justify-center text-white transition-colors shadow-lg"
                title="이전 파일 (←)">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path d="M11 4L6 9l5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            )}
            {hasNext && (
              <button
                onClick={handleNext}
                className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/40 hover:bg-black/60 flex items-center justify-center text-white transition-colors shadow-lg"
                title="다음 파일 (→)">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path d="M7 4l5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}
