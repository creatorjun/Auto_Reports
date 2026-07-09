// frontend/src/shared/ui.ts
export const STATUS_STYLE: Record<string, { bg: string; text: string }> = {
  '할 일':              { bg: 'bg-status-todo',    text: 'text-white' },
  '재오픈':             { bg: 'bg-status-todo',    text: 'text-white' },
  '자료 요청 중':       { bg: 'bg-status-data',    text: 'text-white' },
  '이슈 리뷰 중':       { bg: 'bg-status-review',  text: 'text-white' },
  '연구소 대기 중':     { bg: 'bg-status-lab',     text: 'text-white' },
  '연구소 검토 중':     { bg: 'bg-status-lab',     text: 'text-white' },
  '구현 중':           { bg: 'bg-status-impl',    text: 'text-white' },
  '배포 파일 검토 중':  { bg: 'bg-status-deploy',  text: 'text-white' },
  '결과 대기 중':       { bg: 'bg-status-pending', text: 'text-white' },
  '보류 중':           { bg: 'bg-status-todo',    text: 'text-white' },
  '영업본부 검토중':   { bg: 'bg-status-lab',     text: 'text-white' },
}

export const STATUS_LEGEND = [
  { label: '할 일 / 재오픈',       color: 'bg-status-todo'    },
  { label: '자료 요청 중',         color: 'bg-status-data'    },
  { label: '이슈 리뷰 중',         color: 'bg-status-review'  },
  { label: '연구소 대기/검토 중',  color: 'bg-status-lab'     },
  { label: '구현 중',              color: 'bg-status-impl'    },
  { label: '배포 파일 검토 중',    color: 'bg-status-deploy'  },
  { label: '결과 대기 중',         color: 'bg-status-pending' },
]

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
  slaTarget: '#e5e7eb',
  axisText:  '#8e8e93',
  grid:      '#f0f0f0',
  tooltipBorder: '#d2d2d7',
} as const

export type ModalSize = 'md' | 'lg'

const MODAL_SIZE_CLS: Record<ModalSize, string> = {
  md: 'max-w-4xl',
  lg: 'max-w-6xl',
}

export const MODAL_CLS = {
  overlay:     'fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm',
  containerBase: 'bg-white rounded-2xl shadow-2xl w-full mx-4 max-h-[85vh] flex flex-col',
  containerSize: MODAL_SIZE_CLS,
  header:      'flex items-center justify-between px-6 py-4 border-b border-apple-divider/60',
  title:       'text-ui-lg font-semibold text-apple-dark',
  subtitle:    'text-ui-sm text-apple-light mt-0.5',
  closeBtn:    'w-8 h-8 flex items-center justify-center rounded-full hover:bg-apple-gray text-apple-light hover:text-apple-dark transition-colors',
  body:        'overflow-y-auto flex-1 px-6 py-4',
  footer:      'px-6 py-3 border-t border-apple-divider/60 flex justify-end',
  closeText:   'px-4 py-1.5 rounded-lg text-ui-base font-medium bg-apple-gray hover:bg-apple-divider text-apple-dark transition-colors',
  thCell:      'text-left pb-3 text-ui-xs font-semibold text-apple-light uppercase tracking-wider whitespace-nowrap pr-4',
  keyCell:     'py-2.5 pr-4 text-ui-sm font-mono font-medium text-brand-600 whitespace-nowrap',
  bodyCell:    'py-2.5 text-ui-sm text-apple-dark/80 max-w-xs truncate pr-4',
  metaCell:    'py-2.5 text-ui-sm text-apple-light whitespace-nowrap pr-4',
  elapsedCell: 'text-ui-sm font-medium text-red-500 tabular-nums',
} as const
