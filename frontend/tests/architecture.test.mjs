// frontend/tests/architecture.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const source = path.join(root, 'src')

function files(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name)
    if (entry.isDirectory()) return files(target)
    return /\.(ts|tsx)$/.test(entry.name) ? [target] : []
  })
}

function projectCodeFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    if (entry.isDirectory() && ['node_modules', 'dist'].includes(entry.name)) return []
    const target = path.join(directory, entry.name)
    if (entry.isDirectory()) return projectCodeFiles(target)
    return /\.(css|js|mjs|ts|tsx)$/.test(entry.name) ? [target] : []
  })
}

function imports(content) {
  return [...content.matchAll(/from\s+['"](@\/[^'"]+)['"]/g)].map((match) => match[1])
}

test('dependency rule', () => {
  const forbidden = {
    domain: ['application', 'infrastructure', 'presentation', 'app'],
    application: ['infrastructure', 'presentation', 'app'],
    infrastructure: ['presentation', 'app'],
  }
  const violations = []
  for (const file of files(source)) {
    const relative = path.relative(source, file).replaceAll('\\', '/')
    const layer = relative.split('/')[0]
    if (!(layer in forbidden)) continue
    for (const dependency of imports(fs.readFileSync(file, 'utf8'))) {
      if (forbidden[layer].some((target) => dependency.startsWith(`@/${target}/`))) {
        violations.push(`${relative}:${dependency}`)
      }
    }
  }
  assert.deepEqual(violations, [])
})

test('presentation depends on application contracts instead of infrastructure', () => {
  const violations = files(path.join(source, 'presentation')).flatMap((file) =>
    imports(fs.readFileSync(file, 'utf8'))
      .filter((dependency) => dependency.startsWith('@/infrastructure'))
      .map((dependency) => `${path.relative(source, file)}:${dependency}`),
  )
  assert.deepEqual(violations, [])
})

test('source comments follow project rule', () => {
  const violations = []
  for (const file of projectCodeFiles(root)) {
    const relative = path.relative(root, file).replaceAll('\\', '/')
    const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/)
    const expected = file.endsWith('.css')
      ? `/* frontend/${relative} */`
      : `// frontend/${relative}`
    if (lines[0] !== expected) {
      violations.push(`${relative}:missing path header`)
    }
    lines.slice(1).forEach((line, index) => {
      const isComment = file.endsWith('.css')
        ? /^\s*\/\*/.test(line)
        : /^\s*(\/\/|\/\*)/.test(line)
      if (isComment) {
        violations.push(`${relative}:${index + 2}:extra comment`)
      }
    })
  }
  assert.deepEqual(violations, [])
})

test('deployment keeps critical report generation available across releases', () => {
  const modal = fs.readFileSync(
    path.join(source, 'presentation/components/common/LazyGenerateReportModal.tsx'),
    'utf8',
  )
  const nginx = fs.readFileSync(path.join(root, 'nginx.conf'), 'utf8')
  assert.match(modal, /import GenerateReportModal from ['"]\.\/GenerateReportModal['"]/)
  assert.doesNotMatch(modal, /lazy\s*\(|import\s*\(\s*['"]\.\/GenerateReportModal['"]\s*\)/)
  assert.match(nginx, /location = \/index\.html\s*\{[^}]*no-cache, no-store, must-revalidate/s)
  assert.match(nginx, /location \/assets\/\s*\{[^}]*try_files \$uri =404;/s)
  assert.match(nginx, /location \/assets\/\s*\{[^}]*max-age=31536000, immutable/s)
})

test('desktop sidebar starts collapsed', () => {
  const layout = fs.readFileSync(
    path.join(source, 'presentation/components/layout/Layout.tsx'),
    'utf8',
  )

  assert.match(layout, /useState\(true\)/)
})

test('partner issue rows open configured Jira tickets in a new tab', () => {
  const panel = fs.readFileSync(
    path.join(source, 'presentation/components/partner/PartnerIssuePanel.tsx'),
    'utf8',
  )
  const row = fs.readFileSync(
    path.join(source, 'presentation/components/partner/PartnerIssueRow.tsx'),
    'utf8',
  )

  assert.match(panel, /const \{ jiraBrowse \} = useJira\(\)/)
  assert.match(panel, /<PartnerIssueRow[^>]+jiraBrowse=\{jiraBrowse\}/)
  assert.match(row, /href=\{`\$\{jiraBrowse\}\/\$\{issue\.key\}`\}/)
  assert.match(row, /target="_blank"/)
  assert.match(row, /rel="noopener noreferrer"/)
  assert.match(row, /issue\.stage_index/)
  assert.doesNotMatch(row, /issue\.(url|stage)\b/)
})

test('dashboard widget ids follow first render order', () => {
  const contract = fs.readFileSync(path.join(source, 'domain/WidgetId.ts'), 'utf8')
  const entries = [...contract.matchAll(/^\s+([A-Z_]+): '(w\d+)',$/gm)]
    .map((match) => [match[1], match[2]])
  assert.deepEqual(entries, [
    ['YEARLY_CREATED', 'w1'],
    ['YEARLY_RESOLVED', 'w2'],
    ['CREATED_VS_RESOLVED', 'w3'],
    ['ISSUE_REVIEW', 'w4'],
    ['DATA_REQUEST', 'w5'],
    ['RESULT_PENDING', 'w6'],
    ['RECENT_ISSUES', 'w7'],
    ['MONTHLY_CREATED', 'w8'],
    ['MONTHLY_RESOLVED', 'w9'],
    ['SLA_INITIAL_RESPONSE', 'w10'],
    ['SLA_RESOLUTION_MONTHLY', 'w11'],
    ['SLA_MET_VS_VIOLATED', 'w12'],
    ['SLA_DELAY_REASON', 'w13'],
    ['AVG_RESOLUTION_TYPE', 'w14'],
  ])

  for (const relative of [
    'presentation/pages/DashboardPage.tsx',
    'presentation/hooks/useDashboardData.ts',
  ]) {
    const content = fs.readFileSync(path.join(source, relative), 'utf8')
    assert.doesNotMatch(content, /\bw(?:\.w\d+|\[['"]w\d+['"]\])/)
  }
})

test('status badges style closed and unrecognized Jira states', () => {
  const component = fs.readFileSync(
    path.join(source, 'presentation/components/common/StatusBadge.tsx'),
    'utf8',
  )
  const styles = fs.readFileSync(
    path.join(source, 'presentation/styles/index.css'),
    'utf8',
  )

  assert.match(component, /const CLOSED = new Set\(\[[\s\S]*?'닫힘'/)
  assert.match(component, /CLOSED\.has\(status\).*className="badge-good"/)
  assert.match(styles, /\.badge-neutral\s*\{/)
})

test('resolved issues modal omits the current status field', () => {
  const modal = fs.readFileSync(
    path.join(source, 'presentation/components/tables/WeeklyResolvedModal.tsx'),
    'utf8',
  )

  assert.doesNotMatch(modal, /StatusBadge|현재 상태|d\.status/)
})

test('dashboard issue modals share accessible Jira new-tab row behavior', () => {
  const commonModal = fs.readFileSync(
    path.join(source, 'presentation/components/common/IssueTableModal.tsx'),
    'utf8',
  )
  const uiConfig = fs.readFileSync(
    path.join(source, 'presentation/config/ui.ts'),
    'utf8',
  )

  assert.match(commonModal, /window\.open\(`\$\{jiraBrowse\}\/\$\{key\}`, '_blank', 'noopener,noreferrer'\)/)
  assert.match(commonModal, /role="link"/)
  assert.match(commonModal, /tabIndex=\{0\}/)
  assert.match(commonModal, /event\.key !== 'Enter' && event\.key !== ' '/)
  assert.match(commonModal, /w-full table-fixed border-collapse/)
  assert.match(commonModal, /className="min-w-0 truncate"/)
  assert.match(commonModal, /border-b-2 border-apple-divider/)
  assert.match(uiConfig, /thCell:[^\n]*text-center/)
  assert.match(uiConfig, /thCell:[^\n]*border-r border-apple-divider\/90/)
  assert.match(uiConfig, /bodyCell:[^\n]*whitespace-nowrap/)
  assert.doesNotMatch(uiConfig, /bodyCell:[^\n]*break-words/)
  assert.doesNotMatch(commonModal, /<tbody[^>]*divide-y/)
  assert.doesNotMatch(commonModal, /<td[^>]*border-r/)
  assert.doesNotMatch(commonModal, /className="md:hidden divide-y/)

  for (const filename of [
    'DataRequestModal.tsx',
    'IncompleteIssueModal.tsx',
    'IssueReviewModal.tsx',
    'ResultPendingModal.tsx',
    'SlaDelayModal.tsx',
    'SlaViolationModal.tsx',
    'WeeklyCreatedModal.tsx',
    'WeeklyResolvedModal.tsx',
  ]) {
    const modal = fs.readFileSync(
      path.join(source, 'presentation/components/tables', filename),
      'utf8',
    )
    assert.match(modal, /<IssueTableModal/)
    assert.match(modal, /header: '제목', width: 'wide'/)
    assert.match(modal, /className="truncate[^\"]*"[^>]*>\{d\.summary\}<\/p>/)
    assert.doesNotMatch(modal, /leading-snug[^\n]*d\.summary/)
    assert.doesNotMatch(modal, /window\.open|jiraBrowse/)
  }
})

test('dashboard request type and semester filters drive every widget view', () => {
  const page = fs.readFileSync(
    path.join(source, 'presentation/pages/DashboardPage.tsx'),
    'utf8',
  )
  const filter = fs.readFileSync(
    path.join(source, 'presentation/components/common/IssueTypeFilter.tsx'),
    'utf8',
  )
  const dashboardData = fs.readFileSync(
    path.join(source, 'presentation/hooks/useDashboardData.ts'),
    'utf8',
  )

  assert.match(page, /useState<Set<string> \| null>\(null\)/)
  assert.match(page, /useState<Semester \| null>\(null\)/)
  assert.match(page, /<IssueTypeFilter/)
  assert.match(filter, /aria-pressed=\{selected\}/)
  assert.match(filter, /상반기/)
  assert.match(filter, /하반기/)
  assert.match(filter, /초기화/)
  assert.doesNotMatch(filter, /ListFilter|현재 Jira에 등록된 모든 요청 유형/)
  assert.match(filter, /'라이선스': '라이센스 요청'/)
  for (const section of [
    'yearly',
    'weekly',
    'slaMonthly',
    'monthlyCount',
    'slaDonut',
    'slaDelay',
    'resolutionByType',
    'recentAndIncomplete',
    'statusIssues',
  ]) {
    assert.match(dashboardData, new RegExp(`\\b${section}\\b`))
  }
  assert.match(dashboardData, /supportsIssueTypeFiltering/)
  assert.match(dashboardData, /supportsSemesterFiltering/)
  assert.match(dashboardData, /semesterIncludesMonth/)
  assert.match(dashboardData, /dateIsInSemester/)
  assert.match(dashboardData, /sumSelectedTypes/)
  assert.match(dashboardData, /filterIssues/)
  assert.match(dashboardData, /!controlledTypes\.has\(issueType\)/)
  assert.match(dashboardData, /always_included/)
})

test('SLA dashboard exposes issue activity and expandable recent comments', () => {
  const page = fs.readFileSync(
    path.join(source, 'presentation/pages/SlaDashboardPage.tsx'),
    'utf8',
  )
  const table = fs.readFileSync(
    path.join(source, 'presentation/components/sla/SlaIssueActivityTable.tsx'),
    'utf8',
  )

  assert.match(page, /useSlaDashboardIssues/)
  for (const label of [
    '티켓 번호',
    '이슈 최초 생성 시간',
    '댓글 포함 마지막 업데이트 시간',
    '진행 상태',
  ]) {
    assert.match(table, new RegExp(label))
  }
  assert.match(table, /aria-expanded=/)
  assert.match(table, /useState<Set<string>>\(\(\) => new Set\(\)\)/)
  assert.match(table, /expanded=\{!collapsedKeys\.has\(issue\.key\)\}/)
  assert.match(table, /useSlaIssueComments/)
  assert.match(table, /최근 작성된 댓글/)
  assert.match(table, /최대 5개/)
})
