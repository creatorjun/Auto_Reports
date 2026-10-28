// frontend/src/presentation/components/cve/CveInventoryResults.tsx
import { Fragment, useState } from 'react'
import { ChevronDown, ChevronUp, ExternalLink, ShieldAlert } from 'lucide-react'
import type { CveInventoryFinding } from '@/domain/CveInventory'
import { cveImpactLabels, cveSafeReferences } from '@/application/services/cveInventory'
import { cveReferenceUrl } from '@/application/services/securityNews'
import { securityDateLabel, securitySeverityClasses, securitySeverityLabels } from '@/presentation/components/security/securityNewsFormatting'

function Impact({ row }: { row: CveInventoryFinding }) {
  const classes = row.inventory_impact === 'affected' ? 'badge-warning' : row.inventory_impact === 'not_affected' ? 'badge-good' : 'badge-neutral'
  return <span className={classes}>{cveImpactLabels[row.inventory_impact]}</span>
}

function Severity({ row }: { row: CveInventoryFinding }) {
  return <span className="inline-flex flex-wrap items-center gap-2"><span className={securitySeverityClasses[row.severity]}>{securitySeverityLabels[row.severity]}</span><span className="text-control tabular-nums text-apple-mid" title={row.cvss_version ? `CVSS ${row.cvss_version}` : undefined}>{row.cvss_score === null ? '—' : row.cvss_score.toFixed(1)}</span></span>
}

function CveLink({ row }: { row: CveInventoryFinding }) {
  const href = cveReferenceUrl(row.cve_id)
  return href ? <a href={href} target="_blank" rel="noopener noreferrer" className="break-words font-medium text-brand-600 hover:underline focus-visible:outline-brand-500">{row.cve_id}</a> : <span>{row.cve_id}</span>
}

function VersionPreview({ values, empty }: { values: readonly string[]; empty: string }) {
  return <span className={`block break-words text-control ${values.length ? 'text-apple-dark' : 'text-apple-light'}`}>{values.length ? values.slice(0, 2).join(' · ') : empty}{values.length > 2 && <span className="ml-1 whitespace-nowrap text-caption text-apple-mid">외 {values.length - 2}개</span>}</span>
}

function affectedPreview(row: CveInventoryFinding): string[] {
  return row.ranges.length ? row.ranges.map((range) => range.affected ? `${range.type === 'GIT' ? '커밋 ' : ''}${range.affected}` : '').filter(Boolean) : row.affected_versions
}

function Details({ row }: { row: CveInventoryFinding }) {
  const references = cveSafeReferences(row.references)
  return <div className="space-y-4 rounded-xl bg-apple-gray p-4 text-control text-apple-mid">
    <p className="break-words font-medium text-apple-dark">{row.title}</p>
    <div className="grid gap-4 lg:grid-cols-2">
      <div><p className="mb-1 text-caption font-medium">파일에 기록된 버전</p><p className="break-words text-apple-dark">{row.inventory_versions.join(' · ') || '버전 미확인'}</p>{row.affected_inventory_versions.length > 0 && <p className="mt-2 break-words">영향받는 기록 버전: {row.affected_inventory_versions.join(' · ')}</p>}</div>
      <div><p className="mb-1 text-caption font-medium">연결된 제품</p><p className="break-words text-apple-dark">{row.product_names.join(' · ') || row.package_name}</p><p className="mt-2 text-caption">{row.categories.join(' · ')}</p></div>
    </div>
    {row.ranges.length > 0 && <div className="space-y-2"><p className="text-caption font-medium">버전 범위별 수정 정보</p>{row.ranges.map((range, index) => <div key={index} className="grid gap-2 rounded-xl border border-apple-divider bg-apple-surface px-3 py-2 sm:grid-cols-2"><p className="break-words"><span className="mr-2 text-caption text-apple-light">영향</span>{range.affected || '범위 미확인'}</p><p className="break-words"><span className="mr-2 text-caption text-apple-light">{range.type === 'GIT' ? '수정 커밋' : '해결'}</span>{range.fixed || '해결 버전 미확인'}</p></div>)}</div>}
    {row.affected_versions.length > 0 && <details><summary className="cursor-pointer rounded text-caption font-medium focus-visible:outline-brand-500">영향 버전 전체 보기 ({row.affected_versions.length.toLocaleString('ko-KR')})</summary><p className="mt-2 break-words">{row.affected_versions.join(' · ')}</p></details>}
    {row.fixed_versions.length > 0 && <p className="break-words"><span className="mr-2 font-medium">해결된 버전</span>{row.fixed_versions.join(' · ')}</p>}
    <div className="flex flex-wrap gap-x-5 gap-y-2 text-caption"><span>출처 {row.source}</span>{row.severity_source && <span>위험도 근거 {row.severity_source}</span>}<span>수정일 {securityDateLabel(row.modified_at)}</span><span>최초 수집 {securityDateLabel(row.first_seen_at, true)}</span></div>
    {row.source_ids.length > 0 && <p className="break-words text-caption">연결된 공지: {row.source_ids.join(' · ')}</p>}
    {references.length > 0 && <div className="flex flex-wrap gap-3">{references.map((url, index) => <a key={url} href={url} target="_blank" rel="noopener noreferrer" className="inline-flex max-w-full items-center gap-1 rounded text-caption text-brand-600 hover:underline focus-visible:outline-brand-500"><span className="truncate">근거 {index + 1} · {new URL(url).hostname}</span><ExternalLink size={12} className="shrink-0" aria-hidden="true" /></a>)}</div>}
    <p className="text-caption text-apple-light">해결 버전은 이 CVE에 대한 수정 정보입니다. 파일 버전 영향 상태는 실제 실행 여부와 구분합니다.</p>
  </div>
}

export default function CveInventoryResults({ rows }: { rows: readonly CveInventoryFinding[] }) {
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set())
  const toggle = (id: string) => setExpanded((current) => { const next = new Set(current); if (next.has(id)) next.delete(id); else next.add(id); return next })
  const detailButton = (row: CveInventoryFinding) => <button type="button" onClick={() => toggle(row.id)} aria-expanded={expanded.has(row.id)} aria-label={`${row.package_name} ${row.cve_id} 상세 정보`} className="inline-flex items-center gap-1 rounded px-2 py-1 text-caption font-medium text-brand-600 hover:bg-brand-50 focus-visible:outline-brand-500">상세{expanded.has(row.id) ? <ChevronUp size={15} aria-hidden="true" /> : <ChevronDown size={15} aria-hidden="true" />}</button>
  const flags = (row: CveInventoryFinding) => <>{row.known_exploited && <span className="inline-flex items-center gap-1 text-caption text-red-600"><ShieldAlert size={13} aria-hidden="true" />실제 악용</span>}{row.collection_status === 'stale' && <span className="badge-warning">이전 자료</span>}</>
  return <>
    <div className="hidden overflow-hidden rounded-2xl border border-apple-divider/70 bg-apple-surface shadow-apple-sm xl:block">
      <div role="region" aria-label="패키지별 CVE 목록" tabIndex={0} className="overflow-x-auto focus-visible:outline-brand-500">
        <table className="w-full min-w-[1000px] text-left text-control">
          <caption className="sr-only">등록한 패키지의 모든 버전 CVE, 패키지와 CVE별 한 행</caption>
          <thead className="border-b border-apple-divider bg-apple-gray text-caption text-apple-mid"><tr>{['패키지 / CVE', '위험도', '영향받는 버전', '해결된 버전', '파일 버전 영향', '공개일', '상세'].map((label) => <th scope="col" key={label} className="px-4 py-3 font-medium">{label}</th>)}</tr></thead>
          <tbody className="divide-y divide-apple-divider/60">{rows.map((row) => <Fragment key={row.id}><tr className="align-top hover:bg-apple-gray/50">
            <th scope="row" className="max-w-72 px-4 py-4 font-normal"><p className="break-words font-medium text-apple-dark">{row.package_name}</p><p className="mt-0.5 text-caption text-apple-light">{row.ecosystem}</p><div className="mt-2"><CveLink row={row} /></div><div className="mt-2 flex flex-wrap gap-2">{flags(row)}</div></th>
            <td className="px-4 py-4"><Severity row={row} /></td>
            <td className="max-w-64 px-4 py-4"><VersionPreview values={affectedPreview(row)} empty="영향 범위 미확인" /></td>
            <td className="max-w-52 px-4 py-4"><VersionPreview values={row.fixed_versions} empty="해결 버전 미확인" /></td>
            <td className="px-4 py-4"><Impact row={row} /></td><td className="whitespace-nowrap px-4 py-4 text-caption tabular-nums text-apple-mid">{securityDateLabel(row.published_at)}</td><td className="px-3 py-3">{detailButton(row)}</td>
          </tr>{expanded.has(row.id) && <tr><td colSpan={7} className="px-4 pb-4"><Details row={row} /></td></tr>}</Fragment>)}</tbody>
        </table>
      </div>
    </div>
    <div className="space-y-3 xl:hidden">{rows.map((row) => <article key={row.id} className="min-w-0 rounded-2xl border border-apple-divider/70 bg-apple-surface p-4 shadow-apple-sm">
      <div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0 flex-1"><h3 className="break-words text-control font-semibold text-apple-dark">{row.package_name}</h3><p className="mt-1 text-caption text-apple-light">{row.ecosystem}</p></div><Severity row={row} /></div>
      <div className="mt-3 flex flex-wrap items-center gap-3"><CveLink row={row} />{flags(row)}</div>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2"><div><dt className="mb-1 text-caption text-apple-mid">영향받는 버전</dt><dd><VersionPreview values={affectedPreview(row)} empty="영향 범위 미확인" /></dd></div><div><dt className="mb-1 text-caption text-apple-mid">해결된 버전</dt><dd><VersionPreview values={row.fixed_versions} empty="해결 버전 미확인" /></dd></div></dl>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-apple-divider/60 pt-3"><span className="inline-flex flex-wrap items-center gap-2 text-caption text-apple-mid">파일 버전<Impact row={row} /></span>{detailButton(row)}</div>
      {expanded.has(row.id) && <div className="mt-3"><Details row={row} /></div>}
    </article>)}</div>
  </>
}
