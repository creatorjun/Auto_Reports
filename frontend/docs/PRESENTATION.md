# Presentation Layer

Presentation은 React UI, route 단위 page, TanStack Query hook, Zustand client state, Context, 표시 상수와 formatter를 소유합니다.

## Pages

| Page | Route | 역할 |
|------|-------|------|
| `LoginPage` | `/login` | credential 입력과 로그인 mutation |
| `DashboardPage` | `/`, `/reports/:id`, `/reports/annual/:year` | 최신·선택·연간 보고서 dashboard, 기간별 생성·완료 card, 업무 유형별 열린 요청 card, PDF 내보내기 |
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
| `useSlaDashboard` | SLA 이슈 목록 query와 펼쳐진 행의 최신 댓글 조회 범위를 5개→10개→15개로 늘리는 infinite query |

모든 서버 hook은 `useApplicationServices()`에서 gateway를 얻습니다.

SLA 티켓 행은 처음에 펼쳐져 있으며 최신 댓글 5개를 표시합니다. 데스크톱과 모바일은 같은 댓글 패널을 사용하고, `댓글 더보기`를 누를 때마다 최신 댓글을 처음부터 10개, 15개 순으로 다시 조회합니다. 조회에 성공하면 누적 범위의 최신 응답으로 목록을 갱신하고 작성 시각이 최신인 댓글부터 표시하므로, 클릭 사이에 추가된 댓글도 반영됩니다. 마지막 댓글까지 조회하면 더보기 버튼을 숨기며, 조회가 실패하면 기존 댓글을 유지하고 다시 시도할 수 있습니다.

기본 대시보드와 연간 보고서의 요청 유형 선택항목에서는 `승인된 서비스 요청`과 `케이스`를 제거하지만, 해당 유형의 이슈는 다른 유형을 선택하거나 해제해도 기존 필터 목록 밖 유형처럼 통계와 상세 목록에 기본 포함하며 선택한 반기 조건은 적용합니다.

## PDF 내보내기

내보내기는 메인 대시보드와 연간 보고서에서 지원합니다. 상단 `PDF 내보내기` 버튼을 누르면 현재 보고서와 업무 유형·반기 선택을 고정하여 PDF를 다운로드합니다. 문서에는 보고서 제목, 보고서 기간, 선택 필터와 내보낸 시각을 표시합니다. 생성 중에는 버튼이 `PDF 생성 중...`으로 바뀌고 비활성화되며, 실패하면 오류를 표시하고 다시 시도할 수 있습니다.

최근 이슈 표는 현재 필터에 해당하는 보고서 데이터의 모든 행을 포함합니다. 연간 보고서의 재배포 표도 보고서에 포함된 모든 행을 내보내며, 화면의 표 페이지 번호로 범위를 제한하지 않습니다. 재배포 품질 지표는 기존 화면과 동일하게 연간 전체 기준을 유지하므로, 업무 유형이나 반기를 선택한 경우 PDF에 이 범위를 명시합니다. AI 종합 분석의 필터 선택 시 숨김 정책도 그대로 적용합니다.

`DashboardPdfExportStage`는 별도의 라이트 테마·고정 너비 영역에서 같은 대시보드를 렌더링합니다. `DashboardExportContext`는 이 영역의 차트 애니메이션과 표 페이지 나누기를 제어하며, `dashboardPdfCapture`는 준비된 DOM을 문서 블록으로 변환합니다. 일반 화면의 테마·반응형 배치·표 페이지 상태는 유지됩니다. PDF 생성은 `useApplicationServices().dashboardExport.renderPdf`로 요청합니다.

## State와 context

`presentation/state`는 auth, report selection, trigger UI만 저장합니다. 서버 데이터는 Zustand에 복제하지 않고 TanStack Query가 소유합니다. `ApplicationServicesContext`는 gateway를, `JiraContext`는 이슈 링크 구성을 제공합니다.

## Styles

라이트·다크 실제 색상 값은 `presentation/styles/palette.css`에서 단일 관리합니다. Tailwind semantic token과 Recharts 표시 상수는 이 CSS 변수를 참조하며, 공통 CSS는 `presentation/styles`, 날짜·숫자 formatter는 `presentation/utils`에 있습니다.
