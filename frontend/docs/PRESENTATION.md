# Presentation Layer

Presentation은 React UI, route 단위 page, TanStack Query hook, Zustand client state, Context, 표시 상수와 formatter를 소유합니다.

앱 표시 이름은 `SecuLayer`이며 데스크톱·모바일 헤더, 로그인 화면과 브라우저 탭 제목에 동일하게 적용합니다. 헤더와 로그인 화면은 공통 `BrandLogo`를 통해 테마에 따라 투명 배경의 `src/assets/seculayer-wordmark-light.png` 또는 `seculayer-wordmark-dark.png` 원본만 표시하며 별도 텍스트를 붙이지 않습니다. 헤더 로고는 전체 브라우저 뷰포트의 가로 중앙에 고정하여 사이드바 펼침·접힘 및 좌우 컨트롤 너비에 영향을 받지 않습니다. 브라우저 탭 아이콘은 기존 `src/assets/seculayer-logo.png`를 사용합니다.

## Pages

| Page | Route | 역할 |
|------|-------|------|
| `LoginPage` | `/login` | credential 입력과 로그인 mutation |
| `DashboardPage` | `/`, `/reports/:id`, `/reports/annual/:year` | 최신·선택·연간 보고서 dashboard, 기간별 생성·완료 card, 업무 유형별 열린 요청 card, PDF·Excel 내보내기 |
| `SlaViolationPage` | `/sla-violations`, `/sla-violations/history/:id` | 최초응답·해결 SLA 위반의 기간별 생성·자동 저장, 요청 유형·현재 상태·반기 필터, 최신·저장 보고서와 접기/펼치기 |
| `IssueManagementPage` | `/issues` | 전체 이슈 조회, 공통 필터·컬럼 검색, 전체 검색 결과 PDF·Excel 내보내기 |
| `SlaDashboardPage` | `/sla-dashboard` | 장기 이슈 메뉴: 최근 이슈 티켓의 활동 정보와 기본 펼침 댓글 목록·5개씩 더보기 |
| `HistoryPage` | `/history` | 보고서 pagination, 선택, 삭제 |
| `PartnerManagementPage` | `/partners` | 조직·멤버·이슈 탐색 |
| `StoragePage` | `/storage` | 폴더 탐색, 업로드, 삭제, preview |
| `StoragePreviewPage` | `/storage/preview` | 공유 가능한 preview route shell |
| `SiteManagementPage` | `/sites` | 사이트 검색, 최근·목록, 삭제 |
| `SiteCreatePage` | `/sites/new`, `/sites/:id/edit` | 생성·편집 form |
| `SiteDetailPage` | `/sites/:id` | aggregate 상세와 하위 resource 편집 |

`/history` 페이지는 대시보드·저장 보고서·연간 보고서 상단의 `보고서 히스토리` 버튼으로 이동합니다. SLA 현황 화면의 같은 버튼은 `/history#sla-violations`로 이동합니다. 데스크톱 사이드바와 모바일 탭 메뉴에서는 히스토리 항목을 표시하지 않습니다. 대시보드 기간별 생성 폼은 PDF·Excel 내보내기 영역 다음에 배치하며, 보고서가 없는 상태에도 표시합니다. 내보내는 문서에는 이 이동 버튼과 생성 폼을 포함하지 않습니다.

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
| `useSlaDashboard` | 장기 이슈 목록 query와 펼쳐진 행의 최신 댓글 조회 범위를 5개→10개→15개로 늘리는 infinite query |
| `useSlaViolations` | SLA 현황 보고서의 최신·ID·히스토리 query, 생성 mutation과 저장 결과 캐시 갱신 |

모든 서버 hook은 `useApplicationServices()`에서 gateway를 얻습니다.

`DashboardGenerateForm`은 기존 `DashboardContent` 밖에서 주간·월간·연간과 기준일을 입력받습니다. 날짜 선택만으로 기존 데이터는 바뀌지 않으며 생성 완료 후 새 보고서를 표시합니다. 빈 이력이나 조회 실패 시에도 생성 폼을 유지합니다. KST 날짜와 기간 계산은 SLA 현황 폼과 공통 서비스를 사용하며, 생성 폼은 PDF·Excel 내보내기에 포함하지 않습니다. 좌측·모바일의 별도 생성 버튼과 헤더의 최근 7일 생성 동작은 제거했습니다.

연간 전용 화면은 해당 연도의 생성 버튼을 제공합니다. 기존 날짜 범위 API로 연간 전용 보고서를 생성하며 완료 시 해당 연간 query를 갱신하고 최신 일반 보고서 캐시와 구분합니다.

대시보드와 연간 보고서의 최초응답·해결시간 SLA 준수율 차트는 월을 `1월`, `2월` 형식으로 표시합니다. 차트 축·툴팁과 PDF·Excel에도 동일하게 적용하며 원본 연도·월과 상세 조회 기준은 유지합니다.

모든 페이지에서 집계 기간·시간대·자동 저장·자동 갱신 안내, 페이지 소개와 차트 클릭·필터 사용법 같은 고정 설명 문구를 표시하지 않습니다. 제목, 필드 라벨, 데이터·단위·조회 범위, 오류·처리 상태와 실제 데이터 누락 알림은 유지합니다. 보고서 생성, 자동 저장, 정기 갱신과 차트 상세 조회 동작은 그대로 유지합니다.

SLA 현황 화면도 `IssueTypeFilter`를 사용합니다. 요청 유형·현재 상태·반기를 함께 적용한 저장 티켓 목록을 최초응답·해결 위반 목록에 전달하며, 각 목록은 필터 결과로 건수를 계산합니다. 기본 상태 선택은 닫힘·반려됨·보류 중을 제외합니다. 같은 보고서를 보는 동안 사용자의 선택을 유지하며 메뉴 재진입이나 다른 보고서에서는 기본값을 적용합니다. 개별 상태나 전체 선택으로 제외 상태도 다시 포함할 수 있습니다. 필터 선택은 서버 저장 값과 히스토리 건수를 바꾸지 않습니다. 유형 누락은 `확인 불가`로 선택할 수 있으며 반기는 KST 생성월을 기준으로 합니다. 자세한 기존 보고서 호환 방식은 [SLA 현황 문서](../../backend/docs/08_sla_violation_report.md)를 참고하세요.

`SlaViolationOverview`는 공통 필터 결과를 전체 위반 티켓·최초응답 위반·해결 위반·동시 위반 카드로 요약합니다. 같은 SLA를 여러 번 위반해도 카드에서는 티켓당 한 번만 계산하며, 두 SLA 위반은 동시 위반에 포함합니다. 카드 선택은 현재 상태별 분포와 생성 추이를 함께 좁히고, 상태·날짜 막대 선택과 검색은 교집합으로 상세 목록에 적용합니다. 연간은 생성월, 주간·월간은 KST 생성일별로 집계하며 위반 발생일 추이와 구분합니다. 차트는 선택한 SLA 범위의 분포를 유지하고 선택 상태를 강조합니다. 활성 조건은 목록 위에서 개별 해제하거나 `상세 필터 초기화`로 해제합니다. 상세 필터 초기화는 공통 요청 유형·상태·반기 선택을 유지하며, 공통 필터 변경 시 차트의 상태·날짜 선택을 해제합니다. 기존 두 목록의 컬럼 정렬·너비 저장과 상세 펼치기, Jira 링크는 그대로 사용합니다. 집계·검색 계산은 `domain/SlaViolationOverview.ts`가 담당하며 추가 Jira 요청이나 DB 변경 없이 저장 보고서에서 계산합니다.

`SlaViolationList`는 목록별 정렬·컬럼 너비를 관리합니다. `SlaViolationSort`의 순수 정렬 함수로 필터 결과를 정렬하며 원본 스냅샷은 유지합니다. 데스크톱 컬럼명 클릭은 오름·내림차순을 전환하고 경계 드래그는 인접 열 너비를 조정합니다. 모바일 카드에서도 정렬 조건을 선택할 수 있습니다. 행 링크와 상세 펼치기는 정렬·너비 조절과 독립적으로 동작합니다. 티켓 유형과 상태는 대시보드 최신 이슈·상세 표와 같은 `IssueTypeBadge`·`StatusBadge`를 사용합니다. `issueBadgeColors.ts`에서 업무 유형별·상태별 고유 색상을 지정하고, `designTokens.json`의 전용 토큰으로 화면 범위 재정의와 무관하게 라이트·다크 색상을 통일합니다. 띄어쓰기·라이선스 표기·닫힘 별칭은 같은 색상이며, 미등록 값은 중립색입니다. 유형 배지는 좁은 컬럼에서 줄바꿈하여 인접 컬럼을 가리지 않습니다.

SLA의 상태별 체류 기간은 `slaVisibleStatusDurations`에서 닫힘(`닫힘`, `닫혀`, `Closed`) 항목만 표시 대상에서 제외합니다. 현재 상태와 위반 당시 상태는 그대로 표시하며, 보고서 원본·SLA 판정·경과일은 바꾸지 않습니다. 나머지 체류 기간이 없으면 빈 목록 안내를, 원본 이력이 불완전하면 기존 경고를 표시합니다.

`useTablePreferences`는 SLA 최초응답·해결 목록과 대시보드 최근 이슈 표의 정렬·너비를 각각 별도 키로 브라우저 `localStorage`에 저장합니다. 보고서 ID와 무관하게 새로고침, 메뉴 재진입, 다른 보고서 조회 후에도 복원합니다. 같은 브라우저·사이트에서 사용하는 표시 설정이며 티켓 데이터, 필터와 페이지 번호는 저장하지 않습니다. 저장된 버전·정렬 컬럼·방향·열 최소 너비·너비 합계를 검증하고 저장소 접근 실패는 화면 동작을 중단하지 않습니다. `DashboardContent`가 `tablePreferenceKey`를 전달하므로 일반·저장·연간 보고서의 최근 이슈 표는 같은 설정을 사용하고 전체 이슈 표와는 분리됩니다. PDF·Excel용 숨김 렌더링은 이 설정을 읽거나 덮어쓰지 않습니다.

SLA 티켓 행은 처음에 펼쳐져 있으며 최신 댓글 5개를 표시합니다. 데스크톱과 모바일은 같은 댓글 패널을 사용하고, `댓글 더보기`를 누를 때마다 최신 댓글을 처음부터 10개, 15개 순으로 다시 조회합니다. 조회에 성공하면 누적 범위의 최신 응답으로 목록을 갱신하고 작성 시각이 최신인 댓글부터 표시하므로, 클릭 사이에 추가된 댓글도 반영됩니다. 마지막 댓글까지 조회하면 더보기 버튼을 숨기며, 조회가 실패하면 기존 댓글을 유지하고 다시 시도할 수 있습니다.

기본 대시보드와 연간 보고서의 요청 유형 선택항목에서는 `승인된 서비스 요청`과 `케이스`를 제거하지만, 해당 유형의 이슈는 다른 유형을 선택하거나 해제해도 기존 필터 목록 밖 유형처럼 통계와 상세 목록에 기본 포함하며 선택한 반기 조건은 적용합니다.

## PDF·Excel 내보내기

내보내기는 메인 대시보드·과거 보고서·연간 보고서에서 지원합니다. 상단 다운로드 형식에서 PDF 또는 Excel (.xlsx)을 선택한 뒤 내보내기 버튼을 누르면 현재 보고서와 업무 유형·현재 상태·반기·경과일·컬럼 검색 조건을 고정하여 파일을 다운로드합니다. 문서에는 보고서 제목, 보고서 기간, 선택 필터와 내보낸 시각을 표시합니다. 생성 중에는 해당 형식의 생성 상태를 표시하고 형식 선택과 버튼을 비활성화하며, 실패하면 오류를 표시하고 다시 시도할 수 있습니다.

전체 이슈도 같은 형식 선택과 내보내기 수명을 사용합니다. `IssueManagementPage`는 전체 이슈 캐시에서 공통 필터를 적용한 목록을 복사하고 제목·경과일·컬럼 검색 상태를 고정하여 별도의 `RecentIssuesWidget`을 렌더링합니다. 페이지 번호는 다운로드 범위를 제한하지 않으며 자동 동기화나 이후 검색 변경은 생성 중인 파일에 반영하지 않습니다. 최초 수집 완료 후 다운로드를 활성화하고 적용 조건과 마지막 동기화 시각을 파일에 포함합니다.

최근 이슈 표는 현재 필터에 해당하는 보고서 데이터의 모든 행을 포함합니다. 연간 보고서의 재배포 표도 보고서에 포함된 모든 행을 내보내며, 화면의 표 페이지 번호로 범위를 제한하지 않습니다. 재배포 품질 지표는 기존 화면과 동일하게 연간 전체 기준을 유지하므로, 업무 유형이나 반기를 선택한 경우 PDF와 Excel에 이 범위를 명시합니다. AI 종합 분석의 필터 선택 시 숨김 정책도 그대로 적용합니다.

`DashboardPdfExportStage`는 두 형식 모두 별도의 라이트 테마·고정 너비 영역에서 같은 대시보드를 렌더링합니다. `DashboardExportContext`는 이 영역의 차트 애니메이션과 표 페이지 나누기를 제어하며, `dashboardPdfCapture`는 준비된 DOM을 문서 블록으로 변환하고 차트가 제공한 원본 수치도 보존합니다. 일반 화면의 테마·반응형 배치·표 페이지 상태는 유지됩니다. 선택 형식에 따라 `useApplicationServices().dashboardExport.renderPdf` 또는 `renderExcel`로 생성하며, Excel에는 차트 수치를 숫자 셀로 저장합니다.

## State와 context

`presentation/state`는 auth, report selection, trigger UI만 저장합니다. 서버 데이터는 Zustand에 복제하지 않고 TanStack Query가 소유합니다. `ApplicationServicesContext`는 gateway를, `JiraContext`는 이슈 링크 구성을 제공합니다.

## Styles

라이트·다크 실제 색상 값은 `presentation/config/designTokens.json`에서 단일 관리합니다. Tailwind semantic token과 Recharts 표시 상수는 이 CSS 변수를 참조하며, 공통 CSS는 `presentation/styles`, 날짜·숫자 formatter는 `presentation/utils`에 있습니다.
