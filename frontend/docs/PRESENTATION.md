# frontend/docs/PRESENTATION.md

# Presentation 레이어

## Pages

### LoginPage

**경로**: `/login`  
**파일**: `src/presentation/pages/LoginPage.tsx`

- `react-hook-form` + `zod` 유효성 검사
- `useLogin()` 뮤테이션으로 인증 후 `/` 리디렉션
- 로그인 불필요(`loginRequired: false`) 시 자동 통과

---

### DashboardPage

**경로**: `/` 및 `/reports/:id`  
**파일**: `src/presentation/pages/DashboardPage.tsx` (약 16.5KB — 가장 큰 페이지)

- `useLatestReport()` 또는 `useReportById(id)` 로 보고서 로드
- **위젯 렌더링**: 보고서 `widgets` 맵을 순회하며 카드·차트·테이블 모달 조합 렌더
- 상단: `SummaryCard` 군 + `AiSummaryCard`
- 중단: `SlaRateCard`, `SlaDonutChart`, `SlaMonthlyLineChart`, `MonthlyCountChart`
- 하단: `ResolutionTimeChart`, `ReasonPieChart`, `TypeBarChart`, `TrendLineChart`
- 이슈 목록 모달: `WeeklyCreatedModal`, `WeeklyResolvedModal`, `SlaViolationModal`, `SlaOverdueModal`, `SlaDelayModal`, `DataRequestModal`, `IssueReviewModal`, `ResultPendingModal`, `IncompleteIssueModal`

---

### HistoryPage

**경로**: `/history`  
**파일**: `src/presentation/pages/HistoryPage.tsx`

- `useAllReports()` 로 보고서 목록 페이지네이션
- `sentiment` 컬러 뱃지 표시
- 보고서 선택 → `reportStore`에 ID 저장 → DashboardPage로 이동
- 보고서 삭제 기능 (`useDeleteReport()`)

---

### PartnerManagementPage

**경로**: `/partners`  
**파일**: `src/presentation/pages/PartnerManagementPage.tsx`

- 파트너 조직 선택 → 해당 조직의 미처리 이슈 테이블 표시
- `SearchWidget` 통합 — Jira 이슈 직접 검색
- 이슈 스테이지 프로그레스 바 시각화

---

### StoragePage

**경로**: `/storage`  
**파일**: `src/presentation/pages/StoragePage.tsx` (약 36.5KB — 최대 파일)

- 파일 브라우저 UI (트리 + 파일 목록)
- 업로드/다운로드/삭제/이름변경/폴더생성
- `FilePreviewModal`로 파일 인라인 미리보기
- 지원 미리보기 형식: PDF, Word(.docx), Excel(.xlsx), Markdown, 이미지, 텍스트

---

### StoragePreviewPage

**경로**: `/storage/preview`  
**파일**: `src/presentation/pages/StoragePreviewPage.tsx`

- 쿼리 파라미터로 파일 경로를 받아 `FilePreviewModal` 전용 렌더

---

### SiteManagementPage

**경로**: `/sites`  
**파일**: `src/presentation/pages/SiteManagementPage.tsx`

- 사이트 요약 목록 테이블
- 상태 뱃지(SiteStatus) 표시
- 사이트 삭제, 상세/편집 라우팅

---

### SiteCreatePage

**경로**: `/sites/new` (생성) 및 `/sites/:id/edit` (수정)  
**파일**: `src/presentation/pages/SiteCreatePage.tsx` (약 20KB)

- `react-hook-form` + `zod` 다단계 폼
- 섹션: 기본정보 / 계약정보 / 연락처 / 접근 자격증명 / 노드 목록 / 패치 이력 / 방문 이력
- 편집 모드: `siteId` 파라미터 존재 시 기존 데이터 프리필

---

### SiteDetailPage

**경로**: `/sites/:id`  
**파일**: `src/presentation/pages/SiteDetailPage.tsx` (약 36KB — 최대 파일 중 하나)

- 사이트 전체 정보 뷰
- 탭: 개요 / 노드 / 패치 이력 / 방문 이력 / 접근 정보
- 노드·패치·방문 인라인 추가/수정/삭제
- 접근 자격증명 마스킹 토글

---

## Components

### layout/Layout.tsx

`Header` + `Sidebar` (데스크톱) 또는 `MobileTabBar` (모바일) + `<Outlet />` 구조.  
`useMe()` 로 현재 사용자 확인 후 헤더에 표시.

### layout/Header.tsx

- 좌: 로고 + 현재 페이지 타이틀
- 중: `SearchWidget` (Jira 이슈 검색 드롭다운)
- 우: `TriggerButton` + 사용자명 + 로그아웃

### layout/Sidebar.tsx

- 네비게이션 메뉴: 대시보드 / 히스토리 / 파트너 / 사이트 / 스토리지
- 축소/확장 토글 (`uiStore.sidebarOpen`)
- `NavLink`로 active 상태 스타일

### layout/MobileTabBar.tsx

- 하단 고정 탭 바 (5개 메뉴)
- 모바일 전용 (`md:hidden`)

### common/ProtectedRoute.tsx (auth/)

```tsx
// useAuthStore의 accessToken 없으면 /login으로 Navigate
<ProtectedRoute> → <Layout /> </ProtectedRoute>
```

### common/TriggerButton.tsx

- 클릭 → `LazyGenerateReportModal` 열기
- 잡 실행 중 로딩 스피너 표시

### common/GenerateReportModal.tsx

- 날짜 범위 선택 (선택 사항, 미선택 시 이번 주 자동)
- `useTrigger()` 를 통해 잡 시작
- 진행 상태 실시간 표시

### common/SearchWidget.tsx

- 검색어 디바운스 (300ms)
- `searchApi.search()` 로 Jira 이슈 검색
- 결과 드롭다운 + 이슈 클릭 시 Jira 링크 오픈

### cards/SlaRateCard.tsx

- SLA 달성률(%) + SVG 도넛 링 시각화
- `SLA_TARGET_RATE(80%)` 기준 green/yellow/red 컬러

### charts/ (7개 차트 컴포넌트)

모두 `recharts` 기반. `shared/constants.ts` 의 상수로 스타일 통일.

| 컴포넌트 | 차트 종류 | 데이터 키 |
|---|---|---|
| `MonthlyCountChart` | BarChart | created / resolved |
| `ReasonPieChart` | PieChart | 지연 사유별 건수 |
| `ResolutionTimeChart` | BarChart (분포) | 처리 시간 구간 |
| `SlaDonutChart` | PieChart (도넛) | SLA 준수/위반 |
| `SlaMonthlyLineChart` | LineChart | initial / resolution SLA % |
| `TrendLineChart` | LineChart | 주간 이슈 트렌드 |
| `TypeBarChart` | BarChart | 이슈 유형별 건수 |

### tables/ (9개 이슈 모달)

모두 `MODAL_CLS` 토큰(`shared/ui.ts`) 으로 통일된 스타일.  
`IssueModalShell` 을 기반으로 헤더·바디·푸터 구조 공유.

### storage/FilePreviewModal.tsx

지원 형식별 렌더러:
- **PDF**: `pdfjs-dist` 캔버스 렌더
- **Word**: `mammoth` → HTML 변환
- **Excel**: `xlsx` → 테이블 변환
- **Markdown**: `react-markdown` + `remark-gfm` + `rehype-highlight`
- **이미지**: `<img>` 태그
- **텍스트**: `<pre>` 태그
