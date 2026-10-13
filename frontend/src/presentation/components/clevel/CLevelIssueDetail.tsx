// frontend/src/presentation/components/clevel/CLevelIssueDetail.tsx
import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, Check, ExternalLink, Save, X } from 'lucide-react'
import type { CLevelComment, CLevelCommentInput, CLevelIssue, CLevelSlaCycle, CLevelViolation } from '@/domain/CLevelReport'
import { CLEVEL_OWNER_COLORS, cLevelDate, cLevelIssueTitle, cLevelMetricLabel, cLevelNumber, cLevelText } from '@/application/services/cLevelReport'
import { useJira } from '@/presentation/context/JiraContext'
import { CLevelNumber, CLevelOwnerDot, CLevelStatus, CLevelTypeLabel, cLevelWidth } from './CLevelShared'

interface Props {
  issue: CLevelIssue
  violation?: CLevelViolation
  comment?: CLevelComment
  readonly: boolean
  saving: boolean
  saveError: string
  onClose: () => void
  onSave: (comment: CLevelCommentInput) => Promise<boolean>
}

const EMPTY_COMMENT: CLevelCommentInput = { delay_reason: '', action_taken: '', prevention_plan: '', included: true }
const COMMENT_FIELDS = [
  { key: 'delay_reason', label: '지연 원인', placeholder: '예: 연구소 패치 일정 대기로 해결 지연' },
  { key: 'action_taken', label: '조치 내용', placeholder: '현재까지의 조치와 고객 안내 내용' },
  { key: 'prevention_plan', label: '재발 방지 · 향후 계획', placeholder: '완료 예정일, 프로세스 개선 사항' },
] as const

function commentInput(comment: CLevelComment | undefined): CLevelCommentInput {
  return comment ? { delay_reason: comment.delay_reason, action_taken: comment.action_taken, prevention_plan: comment.prevention_plan, included: comment.included } : { ...EMPTY_COMMENT }
}

export default function CLevelIssueDetail({ issue, violation, comment, readonly, saving, saveError, onClose, onSave }: Props) {
  const [input, setInput] = useState(() => commentInput(comment))
  const [baseline, setBaseline] = useState(() => commentInput(comment))
  const [discarding, setDiscarding] = useState(false)
  const [saved, setSaved] = useState(false)
  const initialCycle = issue.sla_cycles.find((cycle) => cycle.cycle_id === violation?.cycle_id && cycle.metric === violation?.metric) ?? issue.sla_cycles.find((cycle) => cycle.breached) ?? issue.sla_cycles[0]
  const [cycleId, setCycleId] = useState(initialCycle ? `${initialCycle.metric}:${initialCycle.cycle_id}` : '')
  const cycle = issue.sla_cycles.find((entry) => `${entry.metric}:${entry.cycle_id}` === cycleId)
  const panel = useRef<HTMLDivElement>(null)
  const closeButton = useRef<HTMLButtonElement>(null)
  const close = useRef(onClose)
  const dirty = JSON.stringify(input) !== JSON.stringify(baseline)
  close.current = () => { if (!saving) { if (dirty) setDiscarding(true); else onClose() } }
  const { jiraBrowse } = useJira()
  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    closeButton.current?.focus()
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close.current() }
      if (event.key !== 'Tab' || !panel.current) return
      const elements = Array.from(panel.current.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], textarea:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex="0"]'))
      const first = elements[0]
      const last = elements[elements.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
    }
    document.addEventListener('keydown', keydown, true)
    return () => { document.removeEventListener('keydown', keydown, true); previousFocus?.focus() }
  }, [])
  const events = useMemo(() => {
    const rows: Array<{ key: string; at: number; kind: 'segment'; index: number } | { key: string; at: number; kind: 'deadline'; cycle: CLevelSlaCycle }> = issue.timeline.map((segment, index) => ({ key: `segment-${segment.id}`, at: new Date(segment.start_at).getTime(), kind: 'segment', index }))
    for (const entry of issue.sla_cycles) {
      if (!entry.breach_at || entry.breached !== true) continue
      rows.push({ key: `deadline-${entry.metric}-${entry.cycle_id}`, at: new Date(entry.breach_at).getTime(), kind: 'deadline', cycle: entry })
    }
    return rows.sort((a, b) => a.at - b.at || (a.kind === 'deadline' ? -1 : 1))
  }, [issue])
  const totalHours = Object.values(issue.owner_hours).reduce<number>((sum, hours) => sum + (hours ?? 0), 0)
  const maxSegmentHours = Math.max(1, ...issue.timeline.map((segment) => segment.duration_hours ?? 0))
  const save = async () => {
    setSaved(false)
    if (await onSave(input)) { setBaseline({ ...input }); setSaved(true); setDiscarding(false) }
  }
  return <div className="cl-detail-overlay" onMouseDown={(event) => { if (event.currentTarget === event.target) close.current() }}>
    <div className="cl-detail" ref={panel} role="dialog" aria-modal="true" aria-labelledby="cl-detail-title">
      <div className="cl-detail-toolbar"><button type="button" className="cl-back" onClick={() => close.current()} ref={closeButton}><ArrowLeft size={16} />C-Level 보고로 돌아가기</button><div><a className="cl-button" href={`${jiraBrowse}/${encodeURIComponent(issue.key)}`} target="_blank" rel="noopener noreferrer">Jira에서 열기 <ExternalLink size={14} /></a><button type="button" className="cl-button cl-icon-button" aria-label="상세 닫기" onClick={() => close.current()}><X size={18} /></button></div></div>
      <div className="cl-detail-content">
        <div className="cl-detail-labels"><a href={`${jiraBrowse}/${encodeURIComponent(issue.key)}`} target="_blank" rel="noopener noreferrer">{issue.key}</a><CLevelTypeLabel type={issue.type} label={issue.type_label} />{cycle?.breached === true && <span className="cl-metric-badge is-resolution">{cLevelMetricLabel(cycle.metric)} SLA 위반</span>}<CLevelStatus status={issue.status} /></div>
        <h2 id="cl-detail-title">{cLevelIssueTitle(issue.customer_name, issue.summary)}</h2>
        {issue.sla_cycles.length > 1 && <label className="cl-cycle-select">SLA 측정 주기<select value={cycleId} onChange={(event) => setCycleId(event.target.value)}>{issue.sla_cycles.map((entry, index) => <option key={`${entry.metric}:${entry.cycle_id}`} value={`${entry.metric}:${entry.cycle_id}`}>{cLevelMetricLabel(entry.metric)} · {issue.sla_cycles.slice(0, index + 1).filter((prior) => prior.metric === entry.metric).length}번째 측정 · {cLevelDate(entry.start_at)}</option>)}</select></label>}
        <div className="cl-detail-metrics">{[{ label: 'SLA 목표', value: cycle?.goal_hours, suffix: 'h' }, { label: '실제 소요', value: cycle?.elapsed_hours, suffix: 'h' }, { label: '초과', value: cycle?.excess_hours, suffix: 'h' }, { label: '재오픈', value: issue.reopen_count, suffix: '회' }].map((metric) => <div className={`cl-panel ${metric.label === '초과' ? 'cl-metric-excess' : ''}`} key={metric.label}><span>{metric.label}</span><strong>{metric.label === '초과' && metric.value != null && metric.value > 0 ? '+' : ''}<CLevelNumber value={metric.value} unit={metric.suffix} digits={1} /></strong></div>)}</div>
        {cycle?.paused && <p className="cl-warning">선택한 SLA 측정은 일시 중지 상태입니다.</p>}
        {cycle && !cycle.historical_elapsed_known && <p className="cl-warning">선택한 기준 시점의 실제 SLA 소요·초과 시간은 확인 불가입니다.</p>}
        <dl className="cl-panel cl-detail-facts">{[
          ['고객사', cLevelText(issue.customer_name)], ['파트너사', issue.partner_names.join(', ') || '확인 불가'],
          ['보고자', cLevelText(issue.reporter)], ['담당자', cLevelText(issue.assignee)],
          ['TAC 담당자', cLevelText(issue.tac_assignee)], ['생성일', cLevelDate(issue.created_at)],
          ['최초응답', cLevelDate(issue.first_response_at)], ['SLA 기한', cLevelDate(cycle?.breach_at)],
        ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>

        <section className="cl-detail-section"><div className="cl-section-heading"><h3>처리 과정</h3><div className="cl-owner-legend">{(['TAC', '고객·파트너', '연구소', '기타'] as const).map((owner) => <CLevelOwnerDot key={owner} owner={owner} />)}</div></div>
          <div className="cl-panel cl-owner-summary"><p>책임 구간별 체류 합계</p><div className="cl-owner-bar">{Object.entries(issue.owner_hours).map(([owner, hours]) => <span key={owner} style={{ ...cLevelWidth(hours ?? 0, totalHours), background: CLEVEL_OWNER_COLORS[owner] }} title={`${owner} ${cLevelNumber(hours, 'h', 1)}`} />)}</div><div className="cl-owner-totals">{Object.entries(issue.owner_hours).map(([owner, hours]) => <span key={owner}>{owner} <CLevelNumber value={hours} unit="h" digits={1} /></span>)}</div><small>상태별 체류 시간은 경과 시간이며 SLA 영업시간 계산과 다를 수 있습니다.</small></div>
          {!issue.history_complete && <p className="cl-warning">상태 이력이 완전하지 않아 일부 처리 과정과 재오픈 횟수는 확인 불가입니다.</p>}
          <div className="cl-timeline">{events.map((event) => event.kind === 'deadline' ? <div className="cl-deadline" key={event.key}><i /><div /><span>{cLevelMetricLabel(event.cycle.metric)} SLA 기한 도래 · {cLevelDate(event.cycle.breach_at)}</span></div> : (() => { const segment = issue.timeline[event.index]; return <div className="cl-timeline-item" key={event.key} style={{ '--cl-owner': CLEVEL_OWNER_COLORS[segment.owner] } as React.CSSProperties}><i className="cl-timeline-dot" /><div className="cl-timeline-header"><div><CLevelStatus status={segment.status} /><span>{segment.owner}</span>{segment.breached_metrics.length > 0 && <span className="cl-breach-tag">기한 도래 구간</span>}{segment.is_current && <span className="cl-current-tag">현재</span>}</div><time>{cLevelDate(segment.start_at)}</time></div><div className="cl-duration-row"><div className="cl-duration-track"><span style={cLevelWidth(segment.duration_hours ?? 0, maxSegmentHours)} /></div><span>{cLevelNumber(segment.duration_hours, 'h', 1)}</span></div><small>종료 {cLevelDate(segment.end_at)}</small></div> })())}{events.length === 0 && <p className="cl-empty">처리 과정 확인 불가</p>}</div>
        </section>

        {issue.warnings.length > 0 && <details className="cl-coverage"><summary>데이터 확인 사항 ({issue.warnings.length})</summary><ul>{issue.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></details>}
        <section className="cl-detail-section cl-comment-section"><div className="cl-section-heading"><h3>보고용 코멘트</h3><label className="cl-checkbox"><input type="checkbox" checked={input.included} disabled={readonly || saving} onChange={(event) => { setInput({ ...input, included: event.target.checked }); setSaved(false) }} />C-Level 보고서에 포함</label></div>
          {readonly && <p className="cl-help">저장 시점의 보고 내용입니다. 수정하려면 새 보고서를 조회해 주세요.</p>}
          {COMMENT_FIELDS.map((field) => <label className="cl-comment-field" key={field.key}>{field.label}<textarea value={input[field.key]} disabled={readonly || saving} maxLength={10000} placeholder={field.placeholder} onChange={(event) => { setInput({ ...input, [field.key]: event.target.value }); setSaved(false) }} /><small>{input[field.key].length.toLocaleString()} / 10,000</small></label>)}
          {comment?.updated_at && <p className="cl-help">{cLevelText(comment.updated_by)} · {cLevelDate(comment.updated_at)} 저장</p>}
          {saveError && <p className="cl-error" role="alert">{saveError}</p>}
          {saved && <p className="cl-success" role="status"><Check size={15} />보고용 코멘트를 저장했습니다.</p>}
          {dirty && !saving && <p className="cl-help">아직 저장하지 않은 변경 사항이 있습니다.</p>}
          {discarding && <div className="cl-discard" role="alert"><span>저장하지 않은 변경 사항을 버리고 닫으시겠습니까?</span><button type="button" className="cl-button" onClick={() => setDiscarding(false)}>계속 편집</button><button type="button" className="cl-button" onClick={onClose}>변경 취소 후 닫기</button></div>}
          <div className="cl-comment-actions"><button type="button" className="cl-button" disabled={saving} onClick={() => close.current()}>{readonly ? '닫기' : '취소'}</button>{!readonly && <button type="button" className="cl-button cl-button-primary" disabled={saving || !dirty} onClick={() => void save()}><Save size={15} />{saving ? '저장 중…' : '저장'}</button>}</div>
        </section>
      </div>
    </div>
  </div>
}
