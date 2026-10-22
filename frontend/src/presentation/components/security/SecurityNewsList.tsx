// frontend/src/presentation/components/security/SecurityNewsList.tsx
import { memo } from 'react'
import { ExternalLink, ShieldAlert } from 'lucide-react'
import type { SecurityNewsItem, SecurityNewsLanguage } from '@/domain/SecurityNews'
import { cveReferenceUrl, safeSecurityNewsUrl, securityNewsDisplayText } from '@/application/services/securityNews'
import { securityDateLabel, securitySeverityClasses, securitySeverityLabels } from './securityNewsFormatting'

const kindLabels = { cve: 'CVE 취약점', advisory: '보안 권고', news: '보안 뉴스' }

const SecurityNewsRow = memo(function SecurityNewsRow({ item, sourceName, language }: { item: SecurityNewsItem; sourceName: string; language: SecurityNewsLanguage }) {
  const url = safeSecurityNewsUrl(item.url)
  const display = securityNewsDisplayText(item, language)
  const cves = item.cve_ids.filter((id) => cveReferenceUrl(id))
  const cve = cves[0]
  return <tr className="text-apple-mid hover:bg-apple-gray/60">
    <td className="px-4 py-3 text-caption">{kindLabels[item.kind]}</td>
    <th scope="row" className="px-4 py-3 text-left font-medium text-apple-dark">
      <span className="block truncate" title={display.text}>{url ? <a href={url} target="_blank" rel="noopener noreferrer" className="rounded hover:text-brand-600 focus-visible:outline-brand-500" aria-label={`${display.text} 원문 보기 (새 창)`}>{display.text}</a> : display.text}</span>
    </th>
    <td className="px-4 py-3"><span className={securitySeverityClasses[item.severity]} title={item.cvss_score !== null ? `CVSS ${item.cvss_score.toFixed(1)}${item.cvss_version ? ` (v${item.cvss_version})` : ''}` : undefined}>{securitySeverityLabels[item.severity]}</span></td>
    <td className="px-4 py-3 text-caption"><span className="inline-flex max-w-full items-center gap-1.5" title={cves.join(', ') || undefined}>{cve ? <><a href={cveReferenceUrl(cve)!} target="_blank" rel="noopener noreferrer" className="truncate rounded hover:text-brand-600 focus-visible:outline-brand-500" aria-label={`${cve} NVD 상세`}>{cve}</a>{cves.length > 1 && <span className="shrink-0 text-apple-light">+{cves.length - 1}</span>}</> : <span className="text-apple-light">—</span>}</span></td>
    <td className="px-4 py-3">{item.known_exploited ? <span className="inline-flex items-center gap-1.5 text-red-600"><ShieldAlert size={13} aria-hidden="true" />확인</span> : <span className="text-apple-light">—</span>}</td>
    <td className="px-4 py-3 text-caption"><span className="block truncate" title={sourceName}>{sourceName}</span></td>
    <td className="px-4 py-3 text-caption tabular-nums" title={item.published_at ? '게시일' : '수정일'}>{securityDateLabel(item.published_at ?? item.updated_at)}</td>
    <td className="px-4 py-3">{url ? <a href={url} target="_blank" rel="noopener noreferrer" aria-label={`${display.text} 원문 확인`} className="inline-flex items-center gap-1 rounded text-caption text-brand-600 hover:underline focus-visible:outline-brand-500">원문<ExternalLink size={12} aria-hidden="true" /></a> : <span className="text-apple-light" title="원문 링크 없음">—</span>}</td>
  </tr>
})

export default function SecurityNewsList({ items, sources, language = 'ko' }: { items: SecurityNewsItem[]; sources: ReadonlyMap<string, string>; language?: SecurityNewsLanguage }) {
  return <div className="overflow-hidden rounded-2xl border border-apple-divider/70 bg-apple-surface shadow-apple-sm">
    <div role="region" aria-label="보안 뉴스 목록 · 가로 스크롤" tabIndex={0} className="overflow-x-auto focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500">
      <table className="w-full min-w-[1160px] table-fixed whitespace-nowrap text-left text-control">
        <caption className="sr-only">보안 이슈별 한 행으로 표시하는 뉴스 목록</caption>
        <colgroup><col className="w-24" /><col /><col className="w-24" /><col className="w-52" /><col className="w-24" /><col className="w-40" /><col className="w-32" /><col className="w-20" /></colgroup>
        <thead className="border-b border-apple-divider bg-apple-gray text-caption text-apple-mid"><tr>
          {['유형', language === 'ko' ? '한 줄 요약' : '원문 제목', '위험도', '관련 CVE', '실제 악용', '출처', '게시일', '원문'].map((label) => <th key={label} scope="col" className="px-4 py-3 font-medium">{label}</th>)}
        </tr></thead>
        <tbody className="divide-y divide-apple-divider/60">{items.map((item) => <SecurityNewsRow key={item.id} item={item} sourceName={sources.get(item.source_id) ?? item.source_id} language={language} />)}</tbody>
      </table>
    </div>
  </div>
}
