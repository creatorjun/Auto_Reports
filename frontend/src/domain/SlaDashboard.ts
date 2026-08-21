// frontend/src/domain/SlaDashboard.ts
export interface SlaDashboardIssue {
  key: string
  created: string
  updated: string
  status: string
}

export interface SlaDashboardComment {
  id: string
  author: string
  body: string
  created: string
  updated: string
}
