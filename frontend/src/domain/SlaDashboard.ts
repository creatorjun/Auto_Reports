// frontend/src/domain/SlaDashboard.ts
export interface SlaDashboardIssue {
  key: string
  type: string
  summary: string
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
  images: SlaDashboardCommentImage[]
}

export interface SlaDashboardCommentImage {
  attachment_id: string
  alt: string
}
