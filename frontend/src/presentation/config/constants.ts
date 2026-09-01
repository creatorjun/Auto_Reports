// frontend/src/presentation/config/constants.ts

export const SLA_TARGET_RATE = 80

export const MONTHS_BACK = 6

export const CHART_HEIGHT = 360

export const CHART_TICK_FONT_SIZE = 11

export const CHART_LEGEND_ICON_SIZE = 7

export const CHART_LEGEND_COLOR = 'rgb(var(--color-chart-axis))'

export const CHART_STROKE_WIDTH = 2.5

export const CHART_DOT_RADIUS = 4

export const CHART_ACTIVE_DOT_RADIUS = 6

export const CHART_GRADIENT_STOP_START = 0.25

export const CHART_GRADIENT_STOP_END = 0.03

export const PIE_COLORS = [
  'rgb(var(--color-chart-warning))',
  'rgb(var(--color-chart-danger))',
  'rgb(var(--color-chart-created))',
  'rgb(var(--color-chart-violet))',
] as const

export const SLA_COLOR_MAP = {
  green:  { ring: 'rgb(var(--color-chart-resolved))', track: 'rgb(var(--color-green-100))', text: 'text-green-600',  badge: 'bg-green-50 text-green-700'  },
  yellow: { ring: 'rgb(var(--color-chart-warning))',  track: 'rgb(var(--color-amber-100))', text: 'text-amber-600',  badge: 'bg-amber-50 text-amber-700'  },
  red:    { ring: 'rgb(var(--color-chart-danger))',   track: 'rgb(var(--color-red-100))',   text: 'text-red-500',    badge: 'bg-red-50 text-red-700'      },
} as const

export const SLA_RING_RADIUS = 32

export const TABLE_PAGE_SIZE = 50

export const TABLE_MIN_COL_FRAC = 0.05

export const DEFAULT_JIRA_BASE_URL = 'https://seculayer.atlassian.net'

export const MONTHLY_COUNT_COLORS = {
  created:  'rgb(var(--color-chart-created))',
  resolved: 'rgb(var(--color-chart-resolved))',
} as const

export const SLA_MONTHLY_COLORS = {
  initial:    'rgb(var(--color-chart-created))',
  resolution: 'rgb(var(--color-chart-resolved))',
} as const
