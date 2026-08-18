# frontend/docs/ROUTING.md

# 라우팅 구조

## 라우트 테이블

| 경로 | 컴포넌트 | 인증 | 설명 |
|------|----------|------|------|
| `/login` | `LoginPage` | 불필요 | 로그인 |
| `/` | `DashboardPage` | 필요 | 최신 보고서 대시보드 |
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

보고서 생성 모달은 배포 직후 이전 chunk 참조로 핵심 기능이 중단되지 않도록 메인 번들에 포함합니다. Nginx는 `index.html`을 캐시하지 않고 해시가 포함된 `/assets/` 파일만 장기 캐시하며, 존재하지 않는 asset 요청은 SPA fallback 대신 404를 반환합니다.

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
