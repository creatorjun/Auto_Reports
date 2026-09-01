// frontend/src/domain/WidgetId.ts
export const WIDGET_ID = {
  YEARLY_CREATED: 'w1',
  YEARLY_RESOLVED: 'w2',
  CREATED_VS_RESOLVED: 'w3',
  ISSUE_REVIEW: 'w4',
  DATA_REQUEST: 'w5',
  RESULT_PENDING: 'w6',
  RECENT_ISSUES: 'w7',
  MONTHLY_CREATED: 'w8',
  MONTHLY_RESOLVED: 'w9',
  SLA_INITIAL_RESPONSE: 'w10',
  SLA_RESOLUTION_MONTHLY: 'w11',
  SLA_MET_VS_VIOLATED: 'w12',
  SLA_DELAY_REASON: 'w13',
  AVG_RESOLUTION_TYPE: 'w14',
  REDEPLOYMENT_ANALYTICS: 'w15',
} as const

export type WidgetId = (typeof WIDGET_ID)[keyof typeof WIDGET_ID]

export const DASHBOARD_WIDGET_ORDER: readonly WidgetId[] = Object.values(WIDGET_ID)
