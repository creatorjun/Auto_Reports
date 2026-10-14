// frontend/src/presentation/config/ui.ts
export const STAGE_TOTAL = 7

export const STAGE_MAP: Record<string, number> = {
  '할 일':            0,
  '재오픈':           0,
  '자료 요청 중':    1,
  '이슈 리뷰 중':    2,
  '연구소 대기 중':   3,
  '연구소 검토 중':   3,
  '구현 중':         4,
  '배포 파일 검토 중':  5,
  '결과 대기 중':    6,
}

export const CHART_COLORS = {
  slaTarget: 'rgb(var(--color-chart-target))',
  axisText:  'rgb(var(--color-chart-axis))',
  grid:      'rgb(var(--color-chart-grid))',
  tooltipBorder: 'rgb(var(--color-apple-divider))',
} as const

export type ModalSize = 'md' | 'lg'

const MODAL_SIZE_CLS: Record<ModalSize, string> = {
  md: 'max-w-5xl',
  lg: 'max-w-7xl',
}

export const MODAL_CLS = {
  overlay:       'fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4',
  containerBase: 'bg-apple-surface rounded-2xl shadow-2xl w-full max-h-[85vh] flex flex-col',
  containerSize: MODAL_SIZE_CLS,
  header:        'flex items-center justify-between px-6 py-4 border-b border-apple-divider/60 shrink-0',
  title:         'text-page-title font-semibold text-apple-dark',
  subtitle:      'text-label text-apple-light mt-0.5',
  closeBtn:      'w-8 h-8 flex items-center justify-center rounded-full hover:bg-apple-gray text-apple-light hover:text-apple-dark transition-colors',
  body:          'overflow-y-auto flex-1 px-6 py-4',
  footer:        'px-6 py-3 border-t border-apple-divider/60 flex justify-end shrink-0',
  closeText:     'px-4 py-1.5 rounded-lg text-control font-medium bg-apple-gray hover:bg-apple-divider text-apple-dark transition-colors',
  thCell:        'border-r border-apple-divider/90 px-4 py-3 text-center text-label font-semibold text-apple-mid uppercase tracking-wider whitespace-nowrap last:border-r-0',
  keyCell:       'py-2.5 pr-4 text-label font-mono font-medium text-brand-600 whitespace-nowrap',
  bodyCell:      'py-2.5 text-body text-apple-dark/80 pr-4 min-w-0 whitespace-nowrap',
  metaCell:      'py-2.5 text-label text-apple-light whitespace-nowrap pr-4',
  elapsedCell:   'text-label font-medium text-red-500 tabular-nums',
} as const
