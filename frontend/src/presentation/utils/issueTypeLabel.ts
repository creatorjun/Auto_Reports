// frontend/src/presentation/utils/issueTypeLabel.ts
export function getIssueTypeLabel(issueType: string): string {
  return issueType.normalize('NFKC').trim().replace(/^라이선스(?= 요청$|$)/, '라이센스')
}
