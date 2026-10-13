// frontend/src/presentation/components/clevel/CLevelHistory.tsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useCLevelSnapshots } from '@/presentation/hooks/useCLevelReport'
import { cLevelDate } from '@/application/services/cLevelReport'
import { cLevelError } from './CLevelShared'

export default function CLevelHistory() {
  const [page, setPage] = useState(0)
  const query = useCLevelSnapshots(page)
  return <section className="rounded-2xl border border-apple-divider bg-apple-surface p-5">
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><h2 className="text-base font-semibold text-apple-dark">C-Level 보고서</h2><Link to="/c-level-report" className="text-sm text-brand-600">새 보고서 조회</Link></div>
    <p className="mb-3 text-xs text-apple-light">저장 당시의 수치, 처리 이력, 보고용 코멘트를 함께 보관합니다.</p>
    {query.isLoading && <p role="status" className="py-6 text-sm text-apple-light">저장된 보고서를 불러오고 있습니다.</p>}
    {query.isError && <div role="alert" className="text-sm text-red-600">{cLevelError(query.error)} <button type="button" onClick={() => void query.refetch()} className="underline">다시 시도</button></div>}
    {query.data && <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-apple-divider text-xs text-apple-light">{['제목', '주기 · 기간', '저장자', '저장 시각', ''].map((label, index) => <th className="whitespace-nowrap px-2 py-3" key={index}>{label}</th>)}</tr></thead><tbody>{query.data.map((item) => <tr key={item.id} className="border-b border-apple-divider/40 text-apple-dark"><td className="min-w-48 px-2 py-4">{item.title}</td><td className="whitespace-nowrap px-2 py-4 text-xs">{item.period === 'week' ? '주간' : '월간'} · {item.start_date} ~ {item.end_date}</td><td className="px-2 py-4">{item.saved_by}</td><td className="whitespace-nowrap px-2 py-4 text-xs">{cLevelDate(item.saved_at)}</td><td className="whitespace-nowrap px-2 py-4"><Link to={`/c-level-report/history/${item.id}`} className="font-medium text-brand-600">상세 · 내보내기</Link></td></tr>)}</tbody></table>{query.data.length === 0 && <p className="py-8 text-center text-sm text-apple-light">저장된 C-Level 보고서가 없습니다.</p>}</div>}
    {(page > 0 || (query.data?.length ?? 0) >= 20) && <div className="mt-4 flex items-center justify-between text-xs"><button type="button" disabled={page === 0 || query.isFetching} onClick={() => setPage(page - 1)} className="rounded-lg bg-apple-gray px-3 py-2 disabled:opacity-40">이전</button><span>{page + 1} 페이지</span><button type="button" disabled={(query.data?.length ?? 0) < 20 || query.isFetching} onClick={() => setPage(page + 1)} className="rounded-lg bg-apple-gray px-3 py-2 disabled:opacity-40">다음</button></div>}
  </section>
}
