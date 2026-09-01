// frontend/tests/architecture.test.mjs
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'

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

function parsedSource(file) {
  return ts.createSourceFile(
    file,
    fs.readFileSync(file, 'utf8'),
    ts.ScriptTarget.Latest,
    true,
    file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  )
}

function imports(file) {
  const dependencies = []
  const visit = (node) => {
    if (
      (ts.isImportDeclaration(node) || ts.isExportDeclaration(node))
      && node.moduleSpecifier
      && ts.isStringLiteral(node.moduleSpecifier)
    ) {
      dependencies.push(node.moduleSpecifier.text)
    }
    if (
      ts.isCallExpression(node)
      && node.expression.kind === ts.SyntaxKind.ImportKeyword
      && node.arguments.length === 1
      && ts.isStringLiteral(node.arguments[0])
    ) {
      dependencies.push(node.arguments[0].text)
    }
    ts.forEachChild(node, visit)
  }
  visit(parsedSource(file))
  return dependencies
}

function dependencyLayer(file, dependency) {
  if (dependency.startsWith('@/')) return dependency.slice(2).split('/')[0]
  if (!dependency.startsWith('.')) return null
  const target = path.resolve(path.dirname(file), dependency)
  const relative = path.relative(source, target).replaceAll('\\', '/')
  return relative.startsWith('../') ? null : relative.split('/')[0]
}

function transportUsages(file) {
  const violations = []
  const visit = (node) => {
    if (
      ts.isCallExpression(node)
      && ts.isIdentifier(node.expression)
      && node.expression.text === 'fetch'
    ) {
      violations.push(`${path.relative(source, file)}:${node.getStart()}:fetch`)
    }
    if (
      ts.isNewExpression(node)
      && ts.isIdentifier(node.expression)
      && ['EventSource', 'XMLHttpRequest'].includes(node.expression.text)
    ) {
      violations.push(`${path.relative(source, file)}:${node.getStart()}:${node.expression.text}`)
    }
    ts.forEachChild(node, visit)
  }
  visit(parsedSource(file))
  return violations
}

test('dependency rule', () => {
  const forbidden = {
    domain: ['application', 'infrastructure', 'presentation', 'app'],
    application: ['infrastructure', 'presentation', 'app'],
    infrastructure: ['presentation', 'app'],
    presentation: ['infrastructure', 'app'],
    app: ['infrastructure'],
  }
  const violations = []
  for (const file of files(source)) {
    const relative = path.relative(source, file).replaceAll('\\', '/')
    const layer = relative.split('/')[0]
    if (!(layer in forbidden)) continue
    for (const dependency of imports(file)) {
      if (forbidden[layer].includes(dependencyLayer(file, dependency))) {
        violations.push(`${relative}:${dependency}`)
      }
    }
  }
  assert.deepEqual(violations, [])
})

test('presentation depends on application contracts instead of infrastructure', () => {
  const violations = files(path.join(source, 'presentation')).flatMap((file) =>
    imports(file)
      .filter((dependency) => dependencyLayer(file, dependency) === 'infrastructure')
      .map((dependency) => `${path.relative(source, file)}:${dependency}`),
  )
  assert.deepEqual(violations, [])
})

test('presentation delegates network transport to application gateways', () => {
  const violations = files(path.join(source, 'presentation')).flatMap(transportUsages)
  assert.deepEqual(violations, [])
})

test('application contracts stay independent from browser platform objects', () => {
  const services = fs.readFileSync(
    path.join(source, 'application/ports/ApplicationServices.ts'),
    'utf8',
  )
  assert.match(services, /interface BinaryContent/)
  assert.match(services, /interface UploadSource/)
  assert.doesNotMatch(services, /\b(?:AbortSignal|Blob|File)\b/)
})

test('domain and application import only internal modules', () => {
  const violations = ['domain', 'application'].flatMap((layer) =>
    files(path.join(source, layer)).flatMap((file) =>
      imports(file)
        .filter((dependency) => dependencyLayer(file, dependency) === null)
        .map((dependency) => `${path.relative(source, file)}:${dependency}`),
    ),
  )
  assert.deepEqual(violations, [])
})

test('infrastructure owns job streaming and file preview transport', () => {
  const reportApi = fs.readFileSync(
    path.join(source, 'infrastructure/api/reportApi.ts'),
    'utf8',
  )
  const jobHook = fs.readFileSync(
    path.join(source, 'presentation/hooks/useJobStream.ts'),
    'utf8',
  )
  const storageApi = fs.readFileSync(
    path.join(source, 'infrastructure/api/storageApi.ts'),
    'utf8',
  )
  const preview = fs.readFileSync(
    path.join(source, 'presentation/components/storage/FilePreviewModal.tsx'),
    'utf8',
  )
  const binaryContent = fs.readFileSync(
    path.join(source, 'infrastructure/api/binaryContent.ts'),
    'utf8',
  )
  const reportHook = fs.readFileSync(
    path.join(source, 'presentation/hooks/useReport.ts'),
    'utf8',
  )
  assert.match(reportApi, /new EventSource\(/)
  assert.match(reportApi, /setTimeout\(tick, delay\)/)
  assert.match(reportApi, /deadlineTimer = setTimeout\(/)
  assert.match(reportApi, /clearTimeout\(deadlineTimer\)/)
  assert.match(jobHook, /reports\.watchJob\(/)
  assert.doesNotMatch(jobHook, /EventSource|getJobStreamUrl|getJobStatus/)
  assert.match(reportHook, /REFRESH_TIMEOUT_MS = 180_000/)
  assert.match(storageApi, /readPreview:/)
  assert.match(storageApi, /convertPreview:/)
  assert.match(preview, /storage\.readPreview\(/)
  assert.match(preview, /storage\.convertPreview\(/)
  assert.match(binaryContent, /URL\.createObjectURL\(data\)/)
  assert.match(binaryContent, /if \(!active\) return/)
  assert.match(binaryContent, /URL\.revokeObjectURL\(url\)/)
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

test('desktop sidebar starts expanded', () => {
  const layout = fs.readFileSync(
    path.join(source, 'presentation/components/layout/Layout.tsx'),
    'utf8',
  )

  assert.match(layout, /useState\(false\)/)
})

test('annual report menus and refresh policy stay explicit', () => {
  const sidebar = fs.readFileSync(
    path.join(source, 'presentation/components/layout/Sidebar.tsx'),
    'utf8',
  )
  const annualConfig = fs.readFileSync(
    path.join(source, 'presentation/config/annualReports.ts'),
    'utf8',
  )
  const reportHook = fs.readFileSync(
    path.join(source, 'presentation/hooks/useReport.ts'),
    'utf8',
  )
  const router = fs.readFileSync(path.join(source, 'app/router.tsx'), 'utf8')

  assert.match(annualConfig, /ANNUAL_REPORT_YEARS = \[2024, 2025, 2026\]/)
  assert.match(annualConfig, /REFRESHABLE_ANNUAL_REPORT_YEAR = 2026/)
  assert.match(annualConfig, /1000 \* 60 \* 5/)
  assert.match(sidebar, /`\$\{year\} 연간 보고서`/)
  assert.match(sidebar, /`\/reports\/annual\/\$\{year\}`/)
  assert.match(router, /reports\/annual\/:year/)
  assert.match(reportHook, /staleTime: refreshable \? REPORT_REFRESH_INTERVAL_MS : Infinity/)
  assert.match(reportHook, /refetchInterval: refreshable \? REPORT_REFRESH_INTERVAL_MS : false/)
})

test('annual reports render every redeployment dashboard view', () => {
  const section = fs.readFileSync(
    path.join(source, 'presentation/components/annual/RedeploymentAnnualSection.tsx'),
    'utf8',
  )
  const palette = fs.readFileSync(
    path.join(source, 'presentation/styles/palette.css'),
    'utf8',
  )
  const page = fs.readFileSync(
    path.join(source, 'presentation/pages/DashboardPage.tsx'),
    'utf8',
  )

  for (const label of [
    '전체 해결 이슈',
    '재배포 이슈',
    '재배포율',
    '월별 재배포 추이',
    '재배포 원인',
    '담당자별 재배포',
    '파트너사별 재배포 히트맵',
    '최근 완료 재배포 이슈',
    '집계 불가',
    '원천 데이터가 기록되지 않았습니다',
  ]) {
    assert.match(section, new RegExp(label))
  }
  assert.doesNotMatch(section, /dashboard_id/)
  assert.doesNotMatch(section, /Quality analytics/)
  assert.doesNotMatch(section, /연도 고정형 지표/)
  assert.doesNotMatch(section, /원본 JQL과 동일하게/)
  assert.doesNotMatch(section, /적용된 JQL 보기/)
  assert.doesNotMatch(section, /source_jqls/)
  assert.match(section, /REDEPLOYMENT_PAGE_SIZE = 5/)
  assert.match(section, /latest_issues\.filter/)
  assert.match(section, /issues\.slice/)
  assert.match(section, /isDashboardExcludedIssueType/)
  assert.match(section, /Array\.from\(\{ length: totalPages \}\)/)
  assert.match(section, /onClick=\{\(\) => setPage\(pageNumber\)\}/)
  assert.match(section, /classification_complete/)
  assert.match(section, /REDEPLOYMENT_CHART_COLORS/)
  assert.match(section, /<Pie data=\{data\} dataKey="value" nameKey="name" outerRadius=\{118\}/)
  assert.doesNotMatch(section, /PIE_COLORS/)
  assert.doesNotMatch(section, /innerRadius=/)
  assert.doesNotMatch(section, /rgba\(37, 99, 235/)
  assert.match(palette, /--color-chart-muted-steel:/)
  assert.match(palette, /--color-chart-muted-sage:/)
  assert.match(palette, /--color-chart-muted-taupe:/)
  assert.match(page, /WIDGET_ID\.REDEPLOYMENT_ANALYTICS/)
  assert.match(
    page,
    /<RedeploymentAnnualSection[\s\S]*?<SectionTitle icon={Pin} title="최근 이슈 현황"/,
  )
})

test('w3 and w4 cards omit only the recent prefix', () => {
  const page = fs.readFileSync(
    path.join(source, 'presentation/pages/DashboardPage.tsx'),
    'utf8',
  )

  assert.match(page, /label={`\$\{rangeDays\}일 생성`}/)
  assert.match(page, /label={`\$\{rangeDays\}일 완료`}/)
  assert.doesNotMatch(page, /label={`최근 \$\{rangeDays\}일 (?:생성|완료)`}/)
})

test('theme palette and persisted mode stay centralized in presentation', () => {
  const palette = fs.readFileSync(
    path.join(source, 'presentation/styles/palette.css'),
    'utf8',
  )
  const tailwind = fs.readFileSync(path.join(root, 'tailwind.config.js'), 'utf8')
  const store = fs.readFileSync(
    path.join(source, 'presentation/state/themeStore.ts'),
    'utf8',
  )
  const toggle = fs.readFileSync(
    path.join(source, 'presentation/components/layout/ThemeToggle.tsx'),
    'utf8',
  )
  const sidebar = fs.readFileSync(
    path.join(source, 'presentation/components/layout/Sidebar.tsx'),
    'utf8',
  )
  const header = fs.readFileSync(
    path.join(source, 'presentation/components/layout/Header.tsx'),
    'utf8',
  )
  const main = fs.readFileSync(path.join(source, 'main.tsx'), 'utf8')

  assert.match(palette, /:root\[data-theme='dark'\]/)
  assert.match(palette, /--color-apple-surface:/)
  assert.match(palette, /--color-chart-grid:/)
  assert.match(tailwind, /paletteColor\('apple-surface'\)/)
  assert.match(tailwind, /var\(--shadow-apple\)/)
  assert.match(store, /theme: 'light'/)
  assert.match(store, /name: 'auto-reports-theme'/)
  assert.match(store, /document\.documentElement\.dataset\.theme = theme/)
  assert.match(toggle, /role="switch"/)
  assert.match(toggle, /aria-checked=\{isDark\}/)
  assert.match(sidebar, /<ThemeToggle collapsed=\{collapsed\} \/>/)
  assert.match(header, /<ThemeToggle collapsed \/>/)
  assert.match(main, /import '.\/presentation\/styles\/palette\.css'/)
  assert.match(main, /applyTheme\(useThemeStore\.getState\(\)\.theme\)/)
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

test('partner management filters organizations members and issues independently', () => {
  const page = fs.readFileSync(
    path.join(source, 'presentation/pages/PartnerManagementPage.tsx'),
    'utf8',
  )
  const searchInput = fs.readFileSync(
    path.join(source, 'presentation/components/partner/PartnerSearchInput.tsx'),
    'utf8',
  )
  const orgPanel = fs.readFileSync(
    path.join(source, 'presentation/components/partner/PartnerOrgPanel.tsx'),
    'utf8',
  )
  const memberPanel = fs.readFileSync(
    path.join(source, 'presentation/components/partner/PartnerMemberPanel.tsx'),
    'utf8',
  )
  const issuePanel = fs.readFileSync(
    path.join(source, 'presentation/components/partner/PartnerIssuePanel.tsx'),
    'utf8',
  )
  const partner = fs.readFileSync(path.join(source, 'domain/Partner.ts'), 'utf8')

  assert.match(searchInput, /placeholder: string/)
  assert.match(searchInput, /ariaLabel: string/)
  assert.match(searchInput, /disabled\?: boolean/)
  assert.match(page, /organizationQuery/)
  assert.match(page, /memberQuery/)
  assert.match(page, /issueQuery/)
  assert.match(page, /searchQuery=\{organizationQuery\}/)
  assert.match(page, /searchQuery=\{memberQuery\}/)
  assert.match(page, /searchQuery=\{issueQuery\}/)
  assert.doesNotMatch(page, /파트너사명과 직원명을 한 번에/)
  assert.match(orgPanel, /placeholder="파트너 조직 필터"/)
  assert.match(orgPanel, /matchesPartnerSearch\(org\.name, normalizedQuery\)/)
  assert.doesNotMatch(orgPanel, /useQueries|member\.display_name/)
  assert.match(orgPanel, /visibleOrgs\.map/)
  assert.match(memberPanel, /placeholder="멤버 필터"/)
  assert.match(memberPanel, /visibleMembers\.map/)
  assert.match(memberPanel, /matchesPartnerSearch\(member\.display_name, normalizedQuery\)/)
  assert.match(memberPanel, /matchesPartnerSearch\(member\.email, normalizedQuery\)/)
  assert.match(issuePanel, /placeholder="이슈 번호·제목 필터"/)
  assert.match(issuePanel, /matchesPartnerSearch\(issue\.key, normalizedQuery\)/)
  assert.match(issuePanel, /matchesPartnerSearch\(issue\.summary, normalizedQuery\)/)
  assert.match(issuePanel, /visibleIssues\.map/)
  assert.match(partner, /normalize\('NFKC'\)/)
  assert.match(partner, /toLocaleLowerCase\('ko-KR'\)/)
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
    ['REDEPLOYMENT_ANALYTICS', 'w15'],
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
  assert.match(commonModal, /size = 'lg'/)
  assert.match(commonModal, /width\?: 'wide' \| 'date'/)
  assert.match(commonModal, /col\.width === 'date' \? 'w-48'/)
  assert.match(commonModal, /w-48 min-w-48 whitespace-nowrap px-4 text-center align-middle/)
  assert.match(commonModal, /col\.width === 'date'[\s\S]*\? 'whitespace-nowrap text-center \[&>\*\]:pr-0'/)
  assert.match(commonModal, /<td[\s\S]*px-4 text-center align-middle/)
  assert.match(commonModal, /: 'min-w-0 truncate text-center \[&>\*\]:pr-0'/)
  assert.match(commonModal, /column\.mobile\.slot === 'primary'/)
  assert.match(commonModal, /column\.mobile\.slot === 'secondary'/)
  assert.match(commonModal, /column\.mobile\.slot === 'summary'/)
  assert.match(commonModal, /column\.mobile\.slot === 'detail'/)
  assert.match(commonModal, /cursor-pointer flex flex-col gap-1 rounded-lg/)
  assert.match(commonModal, /flex items-center justify-center gap-3/)
  assert.match(commonModal, /flex flex-wrap items-center justify-center gap-2/)
  assert.doesNotMatch(commonModal, /renderMobileRow/)
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
    'SlaOverdueModal.tsx',
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
    assert.match(modal, /header: '(?:생성|해결)일시', width: 'date'/)
    assert.match(modal, /mobile: \{ slot: 'primary'/)
    assert.match(modal, /mobile: \{ slot: 'summary'/)
    assert.doesNotMatch(modal, /renderMobileRow|md:hidden|justify-between/)
    assert.doesNotMatch(modal, /window\.open|jiraBrowse/)
  }
})

test('recent issue list centers body content without cell dividers', () => {
  const table = fs.readFileSync(
    path.join(source, 'presentation/components/charts/ResolutionTimeChart.tsx'),
    'utf8',
  )
  const tbody = table.match(/<tbody>([\s\S]*?)<\/tbody>/)?.[1] ?? ''
  const mobileCard = table.match(/function MobileIssueCard[\s\S]*?\n}\n\nexport default/)?.[0] ?? ''
  const tableCells = [...tbody.matchAll(/<td className="([^"]+)"/g)]

  assert.equal(tableCells.length, 6)
  for (const cell of tableCells) assert.match(cell[1], /\btext-center\b/)
  assert.doesNotMatch(tbody, /\bborder-r\b|\bborder-b\b/)
  assert.match(table, /className="flex flex-col items-center[^\"]*text-center/)
  assert.doesNotMatch(table, /md:hidden[^\n]*divide-y/)
  assert.doesNotMatch(mobileCard, /\bborder-b\b/)
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
  const issueTypePolicy = fs.readFileSync(
    path.join(source, 'domain/DashboardIssueTypePolicy.ts'),
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
  assert.doesNotMatch(filter, /라이선스|라이센스/)
  assert.match(issueTypePolicy, /'라이선스'/)
  assert.match(issueTypePolicy, /'라이센스 요청'/)
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
  assert.match(dashboardData, /isDashboardExcludedIssueType/)
  assert.match(dashboardData, /if \(!byType\) return fallback/)
  assert.doesNotMatch(dashboardData, /!byType \|\| selectedTypes === null/)
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
  const api = fs.readFileSync(
    path.join(source, 'infrastructure/api/slaDashboardApi.ts'),
    'utf8',
  )
  const issueTypeIcon = fs.readFileSync(
    path.join(source, 'presentation/components/common/IssueTypeIcon.tsx'),
    'utf8',
  )

  assert.match(page, /useSlaDashboardIssues/)
  for (const label of [
    '티켓 번호',
    '티켓 제목',
    '생성일',
    '진행상태',
  ]) {
    assert.match(table, new RegExp(label))
  }
  assert.doesNotMatch(table, /issue\.updated/)
  assert.doesNotMatch(table, /댓글 포함 마지막 업데이트 시간/)
  assert.match(table, /aria-expanded=/)
  assert.match(table, /useState<Set<string>>\(\(\) => new Set\(\)\)/)
  assert.match(table, /expanded=\{!collapsedKeys\.has\(issue\.key\)\}/)
  assert.match(table, /useSlaIssueComments/)
  assert.match(table, /최근 작성된 댓글/)
  assert.match(table, /최대 5개/)
  assert.match(table, /comment\.images\.map/)
  assert.match(table, /<IssueTypeIcon type=\{issue\.type\} \/>/)
  assert.match(api, /getCommentImage/)
  for (const filename of [
    'cve.svg',
    'hardware-replacement.svg',
    'improvement.svg',
    'incident.png',
    'license-request.png',
    'service-request.png',
  ]) {
    const asset = path.join(source, 'presentation/assets/issue-types', filename)
    assert.equal(fs.statSync(asset).size > 0, true)
    assert.match(issueTypeIcon, new RegExp(filename.replace('.', '\\.')))
  }
  assert.match(issueTypeIcon, /<img[^>]*className="h-4 w-4 object-contain"/)
  assert.doesNotMatch(issueTypeIcon, /AlertTriangle|Headset|KeyRound|Lightbulb|ShieldAlert/)
  assert.match(api, /responseType: 'blob'/)
  assert.match(api, /createBinaryContent\(response\.data\)/)
  assert.match(table, /content\.createObjectUrl\(\)/)
})

test('portrait displays use the compact navigation and SLA card layout', () => {
  const layout = fs.readFileSync(
    path.join(source, 'presentation/components/layout/Layout.tsx'),
    'utf8',
  )
  const header = fs.readFileSync(
    path.join(source, 'presentation/components/layout/Header.tsx'),
    'utf8',
  )
  const mobileTabs = fs.readFileSync(
    path.join(source, 'presentation/components/layout/MobileTabBar.tsx'),
    'utf8',
  )
  const table = fs.readFileSync(
    path.join(source, 'presentation/components/sla/SlaIssueActivityTable.tsx'),
    'utf8',
  )

  assert.match(layout, /hidden xl:flex/)
  assert.match(header, /xl:hidden/)
  assert.match(header, /xl:flex/)
  assert.match(mobileTabs, /xl:hidden/)
  assert.match(table, /SLA_DESKTOP_MEDIA_QUERY = '\(min-width: 1280px\)'/)
  assert.match(table, /window\.matchMedia\(SLA_DESKTOP_MEDIA_QUERY\)/)
  assert.match(table, /\{isDesktopLayout \? \(/)
  assert.doesNotMatch(table, /hidden overflow-x-auto xl:block/)
  assert.doesNotMatch(table, /divide-y[^\n]+xl:hidden/)
})

test('site management uses the available width across responsive breakpoints', () => {
  const page = fs.readFileSync(
    path.join(source, 'presentation/pages/SiteManagementPage.tsx'),
    'utf8',
  )

  assert.doesNotMatch(page, /max-w-xl/)
  assert.match(page, /max-w-content/)
  assert.match(page, /3xl:max-w-none/)
  for (const columns of [
    'grid-cols-1',
    'sm:grid-cols-2',
    'xl:grid-cols-3',
    '2xl:grid-cols-4',
    '3xl:grid-cols-5',
  ]) {
    assert.match(page, new RegExp(columns))
  }
  assert.match(page, /xl:hidden/)
  assert.match(page, /hidden[^\n]+xl:flex/)
  assert.match(page, /xl:bottom-8/)
  assert.match(page, /aria-label="사이트명 검색"/)
  assert.match(page, /aria-label="새 사이트 등록"/)
})

test('site detail and inline forms adapt to narrow and wide screens', () => {
  const page = fs.readFileSync(
    path.join(source, 'presentation/pages/SiteDetailPage.tsx'),
    'utf8',
  )
  const shared = fs.readFileSync(
    path.join(source, 'presentation/components/site/detail/SiteDetailShared.tsx'),
    'utf8',
  )
  const sections = fs.readFileSync(
    path.join(source, 'presentation/components/site/detail/SiteDetailSections.tsx'),
    'utf8',
  )
  const nodeForm = fs.readFileSync(
    path.join(source, 'presentation/components/site/detail/NodeForm.tsx'),
    'utf8',
  )
  const patchForm = fs.readFileSync(
    path.join(source, 'presentation/components/site/detail/PatchForm.tsx'),
    'utf8',
  )
  const visitForm = fs.readFileSync(
    path.join(source, 'presentation/components/site/detail/VisitForm.tsx'),
    'utf8',
  )

  assert.doesNotMatch(page, /max-w-2xl/)
  assert.match(page, /max-w-content/)
  assert.match(page, /3xl:max-w-none/)
  assert.match(page, /sm:flex-row/)
  assert.match(page, /aria-label="사이트 목록으로 돌아가기"/)
  assert.match(shared, /sm:w-36/)
  assert.match(shared, /sm:flex-row/)
  assert.match(shared, /break-words/)
  assert.match(sections, /md:grid-cols-2/)
  assert.match(sections, /2xl:grid-cols-4/)
  assert.match(sections, /xl:grid-cols-2/)
  assert.match(sections, /3xl:grid-cols-3/)
  for (const form of [nodeForm, patchForm, visitForm]) {
    assert.doesNotMatch(form, /grid grid-cols-2/)
    assert.match(form, /grid grid-cols-1/)
    assert.match(form, /sm:grid-cols-2/)
    assert.match(form, /flex-col-reverse/)
  }
  assert.match(nodeForm, /xl:grid-cols-3/)
  assert.match(patchForm, /xl:grid-cols-4/)
  assert.match(visitForm, /xl:grid-cols-4/)
})
