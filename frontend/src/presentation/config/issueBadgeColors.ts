// frontend/src/presentation/config/issueBadgeColors.ts
import type { CSSProperties } from 'react'

type BadgeTone =
  | 'steel' | 'sage' | 'coral' | 'amber' | 'orange' | 'mauve'
  | 'teal' | 'pink' | 'indigo' | 'brown' | 'cyan' | 'slate'
  | 'violet' | 'mint' | 'rose' | 'sand' | 'gray'

const ISSUE_TYPE_TONES: Readonly<Record<string, BadgeTone>> = {
  개선: 'sage',
  서비스요청: 'steel',
  인시던트: 'coral',
  cve: 'mauve',
  라이선스: 'amber',
  라이선스요청: 'amber',
  라이센스: 'amber',
  라이센스요청: 'amber',
  'h/w장애요청': 'orange',
  승인된서비스요청: 'mint',
  케이스: 'indigo',
}

const STATUS_TONES: Readonly<Record<string, BadgeTone>> = {
  할일: 'slate',
  재오픈: 'orange',
  자료요청중: 'steel',
  이슈리뷰중: 'amber',
  연구소대기중: 'mauve',
  연구소검토중: 'violet',
  구현중: 'sage',
  처리중: 'mint',
  배포파일검토중: 'cyan',
  결과대기중: 'coral',
  보류중: 'sand',
  영업본부검토중: 'brown',
  qa리뷰중: 'pink',
  closed: 'teal',
  닫힘: 'teal',
  닫혀: 'teal',
  반려됨: 'rose',
  중복이슈: 'indigo',
  취소됨: 'gray',
}

function normalizeBadgeLabel(value: string): string {
  return value.normalize('NFKC').trim().replace(/\s+/g, '').toLowerCase()
}

function getBadgeTone(tones: Readonly<Record<string, BadgeTone>>, label: string): BadgeTone {
  const key = normalizeBadgeLabel(label)
  return Object.prototype.hasOwnProperty.call(tones, key) ? tones[key] : 'gray'
}

function getBadgeStyle(tone: BadgeTone): CSSProperties {
  const color = `var(--color-issue-badge-${tone})`
  return {
    backgroundColor: `rgb(${color} / 0.12)`,
    color: `rgb(${color})`,
    borderColor: `rgb(${color} / 0.28)`,
  }
}

export function getIssueTypeBadgeStyle(issueType: string): CSSProperties {
  return getBadgeStyle(getBadgeTone(ISSUE_TYPE_TONES, issueType))
}

export function getStatusBadgeStyle(status: string): CSSProperties {
  return getBadgeStyle(getBadgeTone(STATUS_TONES, status))
}
