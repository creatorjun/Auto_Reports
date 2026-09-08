# Presentation Layer

Presentation은 React UI, route 단위 page, TanStack Query hook, Zustand client state, Context, 표시 상수와 formatter를 소유합니다.

## Pages

| Page | Route | 역할 |
|------|-------|------|
| `LoginPage` | `/login` | credential 입력과 로그인 mutation |
| `DashboardPage` | `/`, `/reports/:id` | 최신 또는 선택 보고서 widget dashboard, 쿼리 기간별 생성·완료 card와 업무 유형별 현재 열린 요청 숫자 card |
| `SlaDashboardPage` | `/sla-dashboard` | 최근 이슈 티켓의 활동 정보와 기본 펼침 댓글 목록·5개씩 더보기 |
| `HistoryPage` | `/history` | 보고서 pagination, 선택, 삭제 |
| `PartnerManagementPage` | `/partners` | 조직·멤버·이슈 탐색 |
| `StoragePage` | `/storage` | 폴더 탐색, 업로드, 삭제, preview |
| `StoragePreviewPage` | `/storage/preview` | 공유 가능한 preview route shell |
| `SiteManagementPage` | `/sites` | 사이트 검색, 최근·목록, 삭제 |
| `SiteCreatePage` | `/sites/new`, `/sites/:id/edit` | 생성·편집 form |
| `SiteDetailPage` | `/sites/:id` | aggregate 상세와 하위 resource 편집 |

## Hooks

| Hook | 역할 |
|------|------|
| `useAuth` | me, login, logout |
| `useConfig` | AppConfig와 Jira URL |
| `useReport` | 보고서 query·delete·refresh polling |
| `useJobStream` | SSE 우선, polling fallback |
| `useTrigger` | 전역 trigger 상태 연결 |
| `useStorage` | 파일·폴더 query와 mutation |
| `useDashboardData` | widget map을 표시 모델로 변환하고 w7 미완료 상세를 업무 유형별 열린 요청 현황으로 분류 |
| `useSlaDashboard` | SLA 이슈 목록 query와 펼쳐진 행의 댓글을 최신순으로 5개씩 누적 조회하는 infinite query |

모든 서버 hook은 `useApplicationServices()`에서 gateway를 얻습니다.

SLA 티켓 행은 처음에 펼쳐져 있으며 최근 댓글 5개를 표시합니다. 데스크톱과 모바일은 같은 댓글 패널을 사용하고, `댓글 더보기`를 누르면 다음 댓글을 최대 5개 추가합니다. 마지막 페이지에서는 더보기 버튼을 숨기며, 추가 조회가 실패해도 기존 댓글을 유지하고 다시 시도할 수 있습니다.

## State와 context

`presentation/state`는 auth, report selection, trigger UI만 저장합니다. 서버 데이터는 Zustand에 복제하지 않고 TanStack Query가 소유합니다. `ApplicationServicesContext`는 gateway를, `JiraContext`는 이슈 링크 구성을 제공합니다.

## Styles

라이트·다크 실제 색상 값은 `presentation/styles/palette.css`에서 단일 관리합니다. Tailwind semantic token과 Recharts 표시 상수는 이 CSS 변수를 참조하며, 공통 CSS는 `presentation/styles`, 날짜·숫자 formatter는 `presentation/utils`에 있습니다.
