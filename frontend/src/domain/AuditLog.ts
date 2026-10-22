// frontend/src/domain/AuditLog.ts
export interface AuditLogEntry {
  timestamp: string
  event: string
  username: string | null
  display_name?: string | null
  email_address?: string | null
  ip: string | null
  details: Record<string, string>
}

export interface AuditLogQuery {
  start_date?: string
  end_date?: string
  event?: string
  username?: string
  ip?: string
  search?: string
  limit: number
  offset: number
}

export interface AuditLogPage {
  items: AuditLogEntry[]
  total: number
  limit: number
  offset: number
  events: string[]
  warnings: string[]
}
