// frontend/src/presentation/utils/dashboardPdfCapture.ts
import type { DashboardPdfBlock, DashboardPdfCell, DashboardPdfDocument } from '@/domain/DashboardExport'

const SVG_PROPERTIES = [
  'fill', 'stroke', 'stroke-width', 'fill-opacity', 'stroke-opacity', 'opacity',
  'stroke-dasharray', 'stroke-linecap', 'stroke-linejoin', 'text-anchor',
  'dominant-baseline', 'font-size', 'font-weight', 'stop-color', 'stop-opacity',
] as const

function text(element: Element | null): string {
  return element?.textContent?.replace(/\s+/g, ' ').trim() ?? ''
}

function title(element: Element): string {
  return (element.getAttribute('data-pdf-title') || text(element.querySelector('h3')))
    .replace(/[\p{Extended_Pictographic}\uFE0F]/gu, '').trim()
}

function color(value: string): string {
  const values = value.match(/[\d.]+/g)?.map(Number)
  if (!values || values.length < 3) return '#64748b'
  const alpha = values[3] ?? 1
  return `#${values.slice(0, 3).map((channel) => Math.round(channel * alpha + 255 * (1 - alpha)).toString(16).padStart(2, '0')).join('')}`
}

function chartSvg(svg: SVGSVGElement): string {
  const copy = svg.cloneNode(true) as SVGSVGElement
  const originals = [svg, ...svg.querySelectorAll('*')]
  const copies = [copy, ...copy.querySelectorAll('*')]
  originals.forEach((original, index) => {
    const target = copies[index]
    const styles = getComputedStyle(original)
    target.removeAttribute('style')
    target.removeAttribute('class')
    for (const property of SVG_PROPERTIES) {
      const value = styles.getPropertyValue(property)
      if (value) target.setAttribute(property, value)
    }
    target.setAttribute('font-family', 'NanumGothic')
    const clip = original.getAttribute('clip-path')
    if (clip) target.setAttribute('clip-path', clip.replace(/url\([^#]*#([^)'"\s]+)[^)]*\)/g, 'url(#$1)'))
    for (const attribute of Array.from(target.attributes)) {
      if (attribute.value.includes('url(')) {
        target.setAttribute(attribute.name, attribute.value.replace(/url\([^#]*#([^)'"\s]+)[^)]*\)/g, 'url(#$1)'))
      }
    }
  })
  copy.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  return new XMLSerializer().serializeToString(copy)
}

function tableBlock(element: HTMLElement): DashboardPdfBlock {
  const table = element.querySelector('table')
  if (!table) return { kind: 'text', title: title(element), paragraphs: [text(element)] }
  const headers = Array.from(table.querySelectorAll('thead tr:last-child th')).map((cell) => cell.getAttribute('data-pdf-header') || text(cell))
  const rows = Array.from(table.querySelectorAll('tbody tr')).map((row) => Array.from(row.querySelectorAll('th, td')).map((cell): DashboardPdfCell => {
    const background = color(getComputedStyle(cell).backgroundColor)
    const href = cell.getAttribute('data-pdf-link') || cell.querySelector('a')?.getAttribute('href')
    return {
      text: cell.getAttribute('data-pdf-value') || text(cell),
      ...(background !== '#ffffff' ? { fillColor: background } : {}),
      ...(href && /^https?:\/\//i.test(href) ? { link: href } : {}),
    }
  }))
  const layout = table.getAttribute('data-pdf-table-layout')
  return {
    kind: 'table', title: title(element), headers, rows,
    ...(layout === 'recent' ? { widths: [10, 28, 12, 11, 11, 13, 15] } : {}),
    ...(layout === 'redeployment' ? { widths: [9, 13, 13, 34, 10, 21] } : {}),
  }
}

function block(element: HTMLElement): DashboardPdfBlock {
  const kind = element.getAttribute('data-pdf-kind')
  if (kind === 'metrics') {
    return {
      kind, items: Array.from(element.querySelectorAll('[data-pdf-metric]')).map((metric) => ({
        label: metric.getAttribute('data-pdf-label') || '',
        value: metric.getAttribute('data-pdf-value') || '0',
      })),
    }
  }
  if (kind === 'table') return tableBlock(element)
  if (kind === 'chart') {
    const svg = element.querySelector<SVGSVGElement>('svg.recharts-surface')
    if (svg) {
      const bounds = svg.getBoundingClientRect()
      const legend = Array.from(element.querySelectorAll('.recharts-legend-item')).map((item) => ({
        label: text(item),
        color: color(getComputedStyle(item.querySelector('svg path, svg circle') || item).fill),
      }))
      const subtitle = Array.from(element.querySelectorAll(':scope > div > div > p, :scope > div > p, :scope > div > span, :scope > p'))
        .filter((item) => !item.hasAttribute('data-pdf-ignore'))
        .map(text).filter(Boolean).join(' · ')
      return { kind, title: title(element), subtitle, svg: chartSvg(svg), width: bounds.width, height: bounds.height, legend }
    }
  }
  const paragraphs = Array.from(element.querySelectorAll('p, li, [data-pdf-paragraph]'))
    .filter((item) => !item.closest('[data-pdf-ignore]'))
    .map((item) => `${item.getAttribute('data-pdf-prefix') || ''}${text(item)}`).filter(Boolean)
  return { kind: 'text', title: title(element), paragraphs: paragraphs.length ? paragraphs : [text(element)] }
}

export function captureDashboardPdf(root: HTMLElement, metadata: Omit<DashboardPdfDocument, 'sections'>): DashboardPdfDocument {
  const sections = Array.from(root.querySelectorAll<HTMLElement>('[data-pdf-section]')).map((section) => ({
    title: section.getAttribute('data-pdf-section') || '',
    blocks: [...(section.hasAttribute('data-pdf-kind') ? [section] : []), ...section.querySelectorAll<HTMLElement>('[data-pdf-kind]')]
      .filter((item) => item.closest('[data-pdf-section]') === section).map(block),
  })).filter((section) => section.blocks.length > 0)
  if (!sections.length) throw new Error('Dashboard export is empty')
  return { ...metadata, sections }
}

export async function waitForDashboardPdf(root: HTMLElement, active: () => boolean): Promise<void> {
  const deadline = Date.now() + 15_000
  let stableSince = 0
  let lastSignature = ''
  while (active() && root.isConnected && Date.now() < deadline) {
    const svgs = Array.from(root.querySelectorAll<SVGSVGElement>('svg.recharts-surface'))
    const ready = !root.querySelector('[data-pdf-pending]')
      && document.fonts.status === 'loaded'
      && svgs.every((svg) => svg.getBoundingClientRect().width > 0)
    const signature = svgs.map((svg) => svg.outerHTML).join('')
    if (ready && signature === lastSignature) {
      if (!stableSince) stableSince = Date.now()
      if (Date.now() - stableSince >= 350) return
    } else stableSince = 0
    lastSignature = signature
    await new Promise((resolve) => window.setTimeout(resolve, 80))
  }
  throw new Error('Dashboard export preparation did not finish')
}
