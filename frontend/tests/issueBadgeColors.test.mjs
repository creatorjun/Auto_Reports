// frontend/tests/issueBadgeColors.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import React from 'react'
import TestRenderer, { act } from 'react-test-renderer'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const sourceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')

function sourceLoader(overrides = {}) {
  const modules = new Map()
  function load(relative) {
    if (Object.hasOwn(overrides, relative)) return overrides[relative]
    const base = path.join(sourceRoot, relative)
    const filename = [base, `${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())
    assert.ok(filename, `Missing module ${relative}`)
    if (modules.has(filename)) return modules.get(filename).exports
    const module = { exports: {} }
    modules.set(filename, module)
    const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX }, fileName: filename,
    }).outputText
    new Function('require', 'module', 'exports', compiled)((dependency) => {
      if (Object.hasOwn(overrides, dependency)) return overrides[dependency]
      if (dependency.startsWith('@/')) return load(dependency.slice(2))
      if (dependency.startsWith('.')) return load(path.relative(sourceRoot, path.resolve(path.dirname(filename), dependency)).replaceAll('\\', '/'))
      return require(dependency)
    }, module, module.exports)
    return module.exports
  }
  return load
}

const load = sourceLoader({ 'presentation/context/JiraContext': { useJira: () => ({ jiraBrowse: 'https://jira.example/browse' }) } })
const { getIssueTypeBadgeStyle, getStatusBadgeStyle } = load('presentation/config/issueBadgeColors')
const { slaVisibleStatusDurations } = load('application/services/slaViolationReport')
const ISSUE_TYPES = ['개선', '서비스 요청', '인시던트', 'CVE', '라이선스', 'H/W 장애 요청', '승인된 서비스 요청', '케이스']
const STATUSES = ['할일', '재오픈', '자료요청중', '이슈리뷰중', '연구소대기중', '연구소검토중', '구현중', '처리중', '배포파일검토중', '결과대기중', '보류중', '영업본부검토중', 'QA리뷰중', '닫힘', '반려됨', '중복이슈', '취소됨']

function textOf(node) {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textOf).join(' ')
  return node?.children ? textOf(node.children) : ''
}

test('known issue types and individual workflow statuses each have distinct stable colors', () => {
  for (const [names, getStyle] of [[ISSUE_TYPES, getIssueTypeBadgeStyle], [STATUSES, getStatusBadgeStyle]]) {
    const initial = names.map((name) => getStyle(name))
    assert.equal(new Set(initial.map((style) => style.backgroundColor)).size, names.length)
    for (const name of [...names].reverse()) getStyle(name)
    assert.deepEqual(names.map((name) => getStyle(name)), initial)
  }
})

test('equivalent Jira spelling, spacing, case, and full-width aliases retain their category colors', () => {
  for (const [canonical, aliases] of [
    ['라이선스', ['라이센스', '라이선스 요청', '라이센스 요청', ' 라이센스　요청 ']],
    ['서비스 요청', ['서비스요청', ' 서비스　요청 ']],
    ['CVE', ['cve', ' ＣＶＥ ']],
    ['H/W 장애 요청', ['H/W장애요청', ' Ｈ／Ｗ 장애 요청 ']],
  ]) {
    for (const alias of aliases) assert.deepEqual(getIssueTypeBadgeStyle(alias), getIssueTypeBadgeStyle(canonical), alias)
  }
  for (const [canonical, aliases] of [
    ['닫힘', ['닫혀', 'Closed', ' CLOSED ', 'Ｃｌｏｓｅｄ']],
    ['할일', ['할 일', ' 할　일 ']],
    ['재오픈', ['재 오픈']],
    ['연구소검토중', ['연구소 검토 중']],
    ['QA리뷰중', ['QA 리뷰 중', 'ｑａ 리뷰 중']],
  ]) {
    for (const alias of aliases) assert.deepEqual(getStatusBadgeStyle(alias), getStatusBadgeStyle(canonical), alias)
  }
})

test('badge colors reference existing theme variables and unknown values use a stable neutral fallback', () => {
  const { themes } = JSON.parse(fs.readFileSync(path.join(sourceRoot, 'presentation/config/designTokens.json'), 'utf8'))
  for (const [names, getStyle] of [[ISSUE_TYPES, getIssueTypeBadgeStyle], [STATUSES, getStatusBadgeStyle]]) {
    for (const name of [...names, '', '확인 불가', '새 업무 값']) {
      const style = getStyle(name)
      for (const property of ['backgroundColor', 'color', 'borderColor']) {
        assert.equal(typeof style[property], 'string', `${name}: ${property}`)
        const references = [...style[property].matchAll(/var\((--[a-z0-9-]+)/g)].map((match) => match[1])
        assert.ok(references.length > 0, `${name}: ${property} uses the shared theme palette`)
        for (const variable of references) {
          for (const [theme, palette] of Object.entries(themes)) assert.ok(Object.hasOwn(palette, variable), `${name}: ${variable} exists in the ${theme} theme`)
        }
      }
    }
    assert.deepEqual(getStyle('새 업무 값'), getStyle('다른 새 값'))
    assert.deepEqual(getStyle(''), getStyle('확인 불가'))
  }
})

test('shared type and status badge components display the same category colors without changing labels', () => {
  const { IssueTypeBadge } = load('presentation/components/common/IssueTypeBadge')
  const { StatusBadge } = load('presentation/components/common/StatusBadge')
  for (const type of ISSUE_TYPES) {
    const element = IssueTypeBadge({ type, className: 'max-w-full whitespace-normal' })
    assert.deepEqual(element.props.style, getIssueTypeBadgeStyle(type))
    assert.equal(element.props.children, type)
    assert.match(element.props.className, /whitespace-normal/)
  }
  for (const status of [...STATUSES, '연구소 검토 중', 'Closed']) {
    const element = StatusBadge({ status })
    assert.deepEqual(element.props.style, getStatusBadgeStyle(status))
    assert.equal(element.props.children, status)
  }
})

test('visible SLA durations exclude only closed aliases while preserving source data, order, and uncertainty', () => {
  const durations = [
    { status: '할 일', hours: 3.25 }, { status: '닫힘', hours: 100 },
    { status: '닫혀', hours: 2 }, { status: ' CLOSED ', hours: 4 }, { status: 'Ｃｌｏｓｅｄ', hours: 5 },
    { status: '취소됨', hours: 6 }, { status: '반려됨', hours: 7 }, { status: '중복 이슈', hours: 8 },
    { status: 'Closed pending', hours: 9 }, { status: '닫힘 대기', hours: 10 },
  ]
  const original = structuredClone(durations)
  durations.forEach(Object.freeze)
  Object.freeze(durations)
  const visible = slaVisibleStatusDurations(durations)
  assert.notStrictEqual(visible, durations)
  assert.deepEqual(visible, [durations[0], ...durations.slice(5)])
  assert.deepEqual(durations, original)
  assert.equal(slaVisibleStatusDurations(null), null)
  assert.deepEqual(slaVisibleStatusDurations([]), [])
  assert.deepEqual(slaVisibleStatusDurations([{ status: '닫힘', hours: 123 }]), [])
})

test('both SLA lists hide closed dwell time while retaining closed current and breach statuses', (t) => {
  const { default: SlaViolationList } = load('presentation/components/sla-violations/SlaViolationList')
  const { default: SlaStatusDurations } = load('presentation/components/sla-violations/SlaStatusDurations')
  const ticket = {
    key: 'TACEA-42', summary: '닫힌 티켓', issue_type: '개선', created_at: '2026-01-01T00:00:00Z', elapsed_days: 10,
    customer: '고객사', partners: [], reporter: '보고자', assignee: '담당자', tac_assignee: 'TAC 담당자', current_status: '닫힘',
    status_durations: [{ status: '할 일', hours: 3.25 }, { status: 'Closed', hours: 8765 }, { status: '닫힘', hours: 9876 }, { status: '취소됨', hours: 6 }],
    breaches: [{ metric: 'initial_response', status: 'Closed', breached_at: '2026-01-02T00:00:00Z' }, { metric: 'resolution', status: '닫힘', breached_at: '2026-01-03T00:00:00Z' }], warnings: [],
  }
  const original = structuredClone(ticket)
  for (const metric of ['initial_response', 'resolution']) {
    let view
    act(() => { view = TestRenderer.create(React.createElement(SlaViolationList, { tickets: [ticket], metric })) })
    t.after(() => act(() => view.unmount()))
    const disclosure = view.root.findByProps({ 'aria-label': 'TACEA-42 상세 펼치기' })
    act(() => disclosure.props.onClick())
    const details = view.root.findByProps({ id: disclosure.props['aria-controls'] })
    const dwellList = details.findByType(SlaStatusDurations).findByType('dl')
    assert.ok(dwellList)
    assert.match(textOf(dwellList), /할 일 3\.25\s*시간/)
    assert.match(textOf(dwellList), /취소됨 6\s*시간/)
    assert.doesNotMatch(textOf(dwellList), /닫힘|Closed|8,765|9,876/)
    assert.match(textOf(details), /현재 체류 상태 닫힘/)
    assert.match(textOf(details.findByType('ul')), metric === 'initial_response' ? /Closed/ : /닫힘/)
    const jira = view.root.findByType('a')
    assert.equal(jira.props.href, 'https://jira.example/browse/TACEA-42')
    assert.equal(jira.props.target, '_blank')
    act(() => view.update(React.createElement(SlaViolationList, { tickets: [{ ...ticket, status_durations: null }], metric })))
    assert.match(textOf(view.toJSON()), /상태 변경 이력이 불완전하여 체류 기간을 확인할 수 없습니다/)
  }
  assert.deepEqual(ticket, original)
})
