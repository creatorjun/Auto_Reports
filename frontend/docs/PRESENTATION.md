# Presentation Layer

Presentation은 React UI, route 단위 page, TanStack Query hook, Zustand client state, Context, 표시 상수와 formatter를 소유합니다.

## Pages

| Page | Route | 역할 |
|------|-------|------|
| `LoginPage` | `/login` | credential 입력과 로그인 mutation |
| `DashboardPage` | `/`, `/reports/:id` | 최신 또는 선택 보고서 widget dashboard, 쿼리 기간별 생성·완료 card와 업무 유형별 현재 열린 요청 숫자 card |
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

모든 서버 hook은 `useApplicationServices()`에서 gateway를 얻습니다.

## State와 context

`presentation/state`는 auth, report selection, trigger UI만 저장합니다. 서버 데이터는 Zustand에 복제하지 않고 TanStack Query가 소유합니다. `ApplicationServicesContext`는 gateway를, `JiraContext`는 이슈 링크 구성을 제공합니다.

## Styles

Recharts·table·modal 표시 상수는 `presentation/config/constants.ts`와 `ui.ts`에 있습니다. CSS는 `presentation/styles`, 날짜·숫자 formatter는 `presentation/utils`에 있습니다.
