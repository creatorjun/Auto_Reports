# frontend/docs/ROUTING.md

# 라우팅 구조

## 집중 관리 메뉴

`전체 이슈`는 `대시보드` 바로 다음의 두 번째 대메뉴이며, `장기 이슈`는 `파일 보관함` 바로 위에 둡니다. `집중 관리 항목`은 `전체 이슈` 다음에 배치하고 하위 메뉴는 `재배포 현황`, `SLA 현황` 순서로 표시합니다. 경로는 아래 표의 기존 주소를 유지합니다. 데스크톱은 하위 메뉴가 있는 대메뉴 버튼에 마우스가 진입할 때만 펼칩니다. 대메뉴에서 하위 메뉴로 이동하면 열린 상태를 유지하고, 두 영역을 벗어나면 접습니다. 사이드바 빈 공간과 일반 메뉴는 마우스 진입으로 펼쳐지지 않습니다. 접힌 사이드바에서는 해당 대메뉴를 가리키는 동안만 임시 확장하고 영역 이탈 시 원래 너비로 돌아갑니다. 클릭·Escape 조작도 지원합니다. 모바일은 버튼을 눌러 하위 목록을 열고 선택·바깥 영역 클릭·Escape로 닫습니다.

## 라우트 테이블

| 경로 | 컴포넌트 | 인증 | 설명 |
|------|----------|------|------|
| `/login` | `LoginPage` | 불필요 | 로그인 |
| `/` | `DashboardPage` | 필요 | 최신 보고서 대시보드 |
| `/redeployments` | `RedeploymentPage` | 필요 | 재배포 현황·원인, 매일 08시 KST 갱신 |
| `/sla-violations` | `SlaViolationPage` | 필요 | SLA 현황: 마지막 저장본과 기간별 생성 |
| `/sla-violations/history/:id` | `SlaViolationPage` | 필요 | 저장된 SLA 현황 보고서 |
| `/issues` | `IssueManagementPage` | 필요 | 전체 이슈 |
| `/sla-dashboard` | `SlaDashboardPage` | 필요 | 장기 이슈: 최근 이슈 활동과 최근 댓글 |
| `/history` | `HistoryPage` | 필요 | 보고서 목록 |
| `/reports/:id` | `DashboardPage` | 필요 | 특정 보고서 대시보드 |
| `/partners` | `PartnerManagementPage` | 필요 | 파트너 관리 |
| `/storage` | `StoragePage` | 필요 | 파일 스토리지 |
| `/storage/preview` | `StoragePreviewPage` | route guard 없음 | token URL 기반 파일 미리보기 |
| `/sites` | `SiteManagementPage` | 필요 | 사이트 목록 |
| `/sites/new` | `SiteCreatePage` | 필요 | 사이트 생성 |
| `/sites/:id` | `SiteDetailPage` | 필요 | 사이트 상세 |
| `/sites/:id/edit` | `SiteCreatePage` | 필요 | 사이트 수정 |
| `*` | — | — | `/login` 리디렉션 |

## 인증 가드 (`ProtectedRoute`)

```tsx
// accessToken 없을 시 /login으로 Navigate (replace)
export default function ProtectedRoute({ children }) {
  const { accessToken } = useAuthStore()
  if (!accessToken) return <Navigate to="/login" replace />
  return children
}
```

## Code Splitting (Lazy Loading)

모든 페이지 컴포넌트는 `React.lazy()` 로 동적 임포트됩니다.  
`LazyErrorBoundary` + `Suspense` 조합으로 로드 실패·로딩 상태를 처리합니다.

보고서 생성 폼은 대시보드 안에 표시합니다. `Layout`의 `ReportGenerationProvider`가 생성 작업을 추적하므로 다른 메뉴로 이동해도 완료·실패 상태를 반영하며, 대시보드를 보고 있을 때 새 보고서로 전환합니다. Nginx는 `index.html`을 캐시하지 않고 해시가 포함된 `/assets/` 파일만 장기 캐시하며, 존재하지 않는 asset 요청은 SPA fallback 대신 404를 반환합니다.

```tsx
const Wrap = ({ children }) => (
  <LazyErrorBoundary>
    <Suspense fallback={<LoadingSpinner text="페이지 로딩 중..." />}>
      {children}
    </Suspense>
  </LazyErrorBoundary>
)
```

## 중첩 라우트 구조

```
/ (ProtectedRoute → Layout)
├── index           → DashboardPage
├── redeployments   → RedeploymentPage
├── sla-violations  → SlaViolationPage
├── sla-violations/history/:id → SlaViolationPage
├── sla-dashboard   → SlaDashboardPage
├── history         → HistoryPage
├── reports/:id     → DashboardPage
├── partners        → PartnerManagementPage
├── storage         → StoragePage
├── sites           → SiteManagementPage
├── sites/new       → SiteCreatePage
├── sites/:id       → SiteDetailPage
└── sites/:id/edit  → SiteCreatePage
```

`/login`과 `/storage/preview`는 protected layout 밖의 독립 route이고 나머지는 `ProtectedRoute → Layout` 아래의 중첩 route입니다.
