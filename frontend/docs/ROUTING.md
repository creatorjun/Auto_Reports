# 라우팅과 메뉴

문서 기준: 2026-10-16.

원본은 [router.tsx](../src/app/router.tsx), [Sidebar](../src/presentation/components/layout/Sidebar.tsx), [MobileTabBar](../src/presentation/components/layout/MobileTabBar.tsx)입니다.

## 메뉴

대시보드 → 전체 이슈 → 집중 관리 항목 → 연간 보고서 → 파트너 관리 → 사이트 관리 → 장기 이슈 → 파일 보관함 순서입니다. 집중 관리 하위는 SLA 현황 → 재배포 현황, 연간 하위는 2024·2025·2026입니다. 감사로그는 관리자에게만 추가 표시합니다. 히스토리와 별도의 보고서 생성 버튼은 대메뉴에 두지 않습니다.

데스크톱에서는 하위 메뉴 버튼에 pointer가 진입할 때 펼칩니다. 하위 영역까지 열린 상태를 유지하고 벗어나면 접습니다. 접힌 사이드바는 그동안 임시 확장하며 빈 공간·일반 메뉴 hover로 확장하지 않습니다. 클릭과 Escape를 지원합니다. 모바일은 클릭으로 열고 선택·바깥 영역·Escape로 닫습니다.

## 라우트

| 경로 | 컴포넌트 | 보호 | 역할 |
|---|---|---|---|
| `/login` | LoginPage | 없음 | Jira 로그인 |
| `/admin` | AdminLoginPage | 없음 | URL 직접 접속으로만 제공하는 기존 관리자 로그인 |
| `/admin/jira-privacy` | AdminJiraPrivacyPage | 페이지 내부 세션·최고 관리자 확인 | 앱 소유자의 개인정보 정기 보고 연결·상태 확인 |
| `/privacy` | PrivacyPage | 없음 | 로그인 없이 확인하는 개인정보처리방침 |
| `/terms` | TermsPage | 없음 | 로그인 없이 확인하는 이용약관 |
| `/storage/preview` | StoragePreviewPage | Layout 밖 | 파일별 API 인증을 적용하는 공유 preview |
| `/` | DashboardPage | ProtectedRoute | 최신 일반 대시보드 |
| `/issues` | IssueManagementPage | ProtectedRoute | 전체 이슈 |
| `/redeployments` | RedeploymentPage | ProtectedRoute | 재배포 현황 |
| `/sla-violations` | SlaViolationPage | ProtectedRoute | 최신 SLA 및 수동 생성 |
| `/sla-violations/history/:id` | SlaViolationPage | ProtectedRoute | 저장 SLA 이력 |
| `/reports/annual/:year` | DashboardPage | ProtectedRoute | 연간 전용 보고서 |
| `/reports/:id` | DashboardPage | ProtectedRoute | 저장 일반/연간 보고서 |
| `/history` | HistoryPage | ProtectedRoute | 일반/연간 및 SLA 히스토리 |
| `/partners` | PartnerManagementPage | ProtectedRoute | 파트너 관리 |
| `/sites` | SiteManagementPage | ProtectedRoute | 사이트 목록 |
| `/sites/new` | SiteCreatePage | ProtectedRoute | 사이트 생성 |
| `/sites/:id` | SiteDetailPage | ProtectedRoute | 사이트 상세 |
| `/sites/:id/edit` | SiteCreatePage | ProtectedRoute | 사이트 편집 |
| `/sla-dashboard` | SlaDashboardPage | ProtectedRoute | 장기 이슈·댓글 |
| `/storage` | StoragePage | ProtectedRoute | 파일 보관함 |
| `/audit-logs` | AuditLogPage | ProtectedRoute + SuperadminRoute | 관리자 감사로그 |
| `*` | Navigate | — | `/login`으로 이동 |

로그인·정책·관리자 연결·storage preview를 제외한 실제 페이지는 `ProtectedRoute → Layout → Outlet` 아래에 있습니다. 대시보드 버튼은 `/history`, SLA 버튼은 `/history#sla-violations`로 이동합니다. 메뉴명 변경 후에도 내부 `/sla-dashboard`, `/sla-violations` 등의 주소는 유지합니다. C-Level 경로는 없습니다.

## 인증과 로딩

`/admin/jira-privacy`는 메뉴에 표시하지 않는 최고 관리자 전용 연결 화면입니다. 미인증 상태는 `/admin`으로 이동하고 일반 관리자·Jira 사용자는 권한 안내만 표시합니다. `/auth/me`에서 최고 관리자임을 확인한 뒤에만 개인정보 보고 상태를 요청합니다. 소유자 승인 시작은 기존 관리자 세션을 유지하며, callback은 이 화면으로 돌아옵니다. 서버에서도 상태·연결 API의 최고 관리자 권한을 검사합니다.

`/privacy`와 `/terms`는 인증 경로 밖에 있으며 로그인·API 요청 없이 문서를 표시합니다. `/login` 하단에서 두 문서로 이동할 수 있고, 문서 페이지에는 상호 링크와 로그인 복귀 링크를 제공합니다. 관리자 로그인 링크는 표시하지 않습니다.

`ProtectedRoute`, `LoginPage`, `AdminLoginPage`는 `useAuthSession`으로 세션 복원을 공유합니다. access token이 없으면 refresh cookie를 사용하고, `/login`과 `/admin` 직접 접속도 자동 로그인합니다. `/login`은 Jira 로그인만 표시하고 기존 admin·superadmin 입력 폼은 `/admin`에서만 제공합니다. `/admin`으로 이동하는 링크나 메뉴는 표시하지 않습니다. 보호 경로는 `/auth/me`로 세션을 확인하며 복원 전에는 로딩을 표시합니다. `LOGIN=false`에서는 guest 접근을 허용합니다. `SuperadminRoute`와 서버 API 모두 관리자 권한을 확인하며 Jira 로그인은 superadmin 권한을 얻지 않습니다. OAuth callback은 백엔드가 처리한 뒤 `/login`으로 돌아옵니다.

각 page는 `React.lazy`와 `LazyErrorBoundary`·`Suspense`로 로드합니다. `Layout`의 `ReportGenerationProvider`가 일반 보고서 job을 추적하여 메뉴 이동 중에도 진행 상태를 유지합니다. SLA·재배포는 별도 HTTP 생성 mutation입니다.

nginx는 일반 경로에 `index.html` fallback을 적용하며 HTML은 no-store입니다. 해시 `/assets/`는 장기 캐시하고 없는 asset은 404로 반환합니다. 라우트 추가 시 서버 fallback과 API 경로를 함께 확인합니다.
