// frontend/src/shared/constants.ts

export const SLA_TARGET_RATE = 80

export const MONTHS_BACK = 6

export const CHART_HEIGHT = 360

export const CHART_TICK_FONT_SIZE = 11

export const CHART_LEGEND_ICON_SIZE = 7

export const CHART_LEGEND_COLOR = '#86868b'

export const CHART_STROKE_WIDTH = 2.5

export const CHART_DOT_RADIUS = 4

export const CHART_ACTIVE_DOT_RADIUS = 6

export const CHART_GRADIENT_STOP_START = 0.25

export const CHART_GRADIENT_STOP_END = 0.03

export const PIE_COLORS = ['#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6'] as const

export const SLA_COLOR_MAP = {
  green:  { ring: '#22c55e', track: '#dcfce7', text: 'text-green-600',  badge: 'bg-green-50 text-green-700'  },
  yellow: { ring: '#f59e0b', track: '#fef3c7', text: 'text-amber-600',  badge: 'bg-amber-50 text-amber-700'  },
  red:    { ring: '#ef4444', track: '#fee2e2', text: 'text-red-500',    badge: 'bg-red-50 text-red-700'      },
} as const

export const SLA_RING_RADIUS = 32

export const TABLE_PAGE_SIZE = 50

export const TABLE_MIN_COL_FRAC = 0.05

export const DEFAULT_JIRA_BASE_URL = 'https://seculayer.atlassian.net'

export const MONTHLY_COUNT_COLORS = {
  created:  '#3b82f6',
  resolved: '#22c55e',
} as const

export const SLA_MONTHLY_COLORS = {
  initial:    '#3b82f6',
  resolution: '#22c55e',
} as const
