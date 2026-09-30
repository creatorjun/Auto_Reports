// frontend/src/presentation/config/issueColumns.ts
import type { IssueColumn } from '@/domain/IssueColumnSearch'

export const ISSUE_COLUMNS: readonly { key: IssueColumn; label: string }[] = [
  { key: 'key', label: '이슈' },
  { key: 'summary', label: '제목' },
  { key: 'status', label: '진행 상태' },
  { key: 'reporter', label: '보고자' },
  { key: 'tac', label: '담당자' },
  { key: 'tac_assignee', label: 'TAC 담당자' },
  { key: 'elapsed', label: '생성일 (경과)' },
]
