# Frontend Components

문서 기준: 2026-10-21.

기준 경로는 `src/presentation/components`입니다.

| 폴더 | 책임 |
|------|------|
| `auth` | 일반 route 인증 및 SuperadminRoute |
| `layout` | Header, Sidebar, MobileTabBar, Outlet layout |
| `common` | loading, error boundary, 검색, 보고서 생성, 공통 modal shell·table |
| `cards` | AI, SLA, 숫자 summary card와 업무 유형별 열린 요청 건수 card |
| `charts` | 월별, SLA, 사유, 처리시간, 유형 Recharts 시각화 |
| `tables` | 이슈 종류별 modal과 history report table |
| `history` | 일반·연간 보고서 삭제 확인 |
| `annual` | 연간 생성·비교·차트 상세·재배포 품질 분석 |
| `sla-status` | SLA 현황 위젯·필터·접힌 목록·상태별 체류시간과 목표/사용/잔여 상세 |
| `sla-violations` | SLA 위반 개요·차트·접힌 표·상태별 시간·이력 |
| `redeployments` | 재배포 상세 티켓 목록 |
| `sla` | 장기 이슈 활동과 기본 펼침 댓글 |
| `export` | PDF·Excel용 별도 렌더링 및 캡처 |
| `partner` | 조직, 멤버, 이슈 panel과 row |
| `site` | 생성 form helper와 node·patch·visit section/form |
| `storage` | table, modal, icon, preview, link 복사와 표시 utility |

## 공통 설계

- 원격 동작은 props 또는 Presentation hook을 통해 수행합니다.
- component는 axios adapter를 import하지 않습니다.
- 이슈 표는 `IssueModalShell`과 `IssueTableModal`을 재사용합니다.
- `IssueTableModal`의 컬럼별 정렬은 데스크톱 헤더와 모바일 선택 UI에서 공유하며 전체 목록을 정렬한 뒤 페이지를 나눕니다. 외부에서 검색·페이지를 관리하는 `AnnualIssueDetailsModal`은 정렬 상태도 소유하여 전체 검색 결과에 적용합니다.
- query key와 표시 상수는 `presentation/config`, formatter는 `presentation/utils`를 사용합니다.
- 큰 파일 preview renderer는 lazy loading합니다. 보고서는 대시보드 상단의 `DashboardGenerateForm`에서 일간·주간·월간·연간과 기준일을 선택해 생성합니다.

## 필터 전체 선택·해제

`IssueTypeFilter`의 일괄 선택 버튼은 선택 가능한 요청 유형과 현재 상태가 모두 선택됐으면 `전체 해제`, 하나라도 빠졌으면 `전체 선택`을 표시합니다. 버튼을 누르면 두 그룹을 한 번에 선택하거나 해제하며 개별 항목을 바꿀 때도 문구가 즉시 갱신됩니다. 현재 대시보드·과거 보고서·연간 보고서·전체 이슈·파트너 관리·SLA 위반이 같은 컴포넌트와 동작을 사용합니다. 반기와 제목·경과일·컬럼 검색은 별도 조건으로 유지하고, 선택할 항목이 없는 그룹이나 지원하지 않는 그룹은 일괄 선택 상태 판단에서 제외합니다.

## SLA 현황 위젯과 목록

`SlaStatusPage`와 `components/sla-status`는 수집 시각·새로고침, 전체·잔여 10% 미만·진행 중 SLA 포함·일시정지 SLA 포함 위젯과 고유 티켓 목록을 표시합니다. `useSlaStatus`는 조회 수명과 마지막 성공 데이터를 관리하고, `application/services/slaStatus.ts`는 위젯 건수·검색·상태·SLA 단계 교집합과 정렬을 계산합니다. 진행 중·일시정지 SLA를 함께 가진 티켓은 두 위젯에서 중복 집계될 수 있지만 목록은 티켓당 한 행입니다.

`SlaStatusOverview`는 전체 수집 결과의 위젯 건수와 선택을, `SlaStatusList`는 필터 결과와 티켓별 펼침을 담당합니다. 기본 목록은 잔여율 낮은 순으로 잔여율·시간·현재 상태·담당자·최대 체류 단계를 표시합니다. 펼친 상세는 서버의 해결시간 SLA 기준 상태별 체류시간과 해당 SLA의 목표·사용·잔여 시간을 표시합니다. 최대 체류 단계와 상세는 기존 `slaVisibleStatusDurations`·`SlaStatusDurations`를 재사용하여 닫힘·결과 대기 중·자료 요청 중·보류 중을 제외한 전체 표시 대상 상태를 사용합니다. 조회 오류는 마지막 성공 목록과 함께 표시하며 생성 폼과 저장 보고서 히스토리는 두지 않습니다.

## SLA 위반 개요와 표

`SlaViolationReportContent`가 공통 필터와 상세 선택을 소유하고 `SlaViolationOverview`에 저장 데이터 집계를 전달합니다. 네 카드·현재 상태 분포·생성 추이는 순수 Domain 계산을 사용합니다. 카드의 SLA 범위와 상태·날짜·검색은 `SLA 위반 티켓` 통합 목록에 교집합으로 적용합니다. 목록은 티켓당 한 행이며 상단 최초응답·해결 카드에는 동시 위반 티켓이 각각 포함되므로 두 카드의 합을 전체 고유 티켓 수로 사용하지 않습니다.

`SlaViolationList`는 번호·제목·유형·위반 항목·생성일·경과일의 접힌 행, Jira 링크와 펼침, 정렬·인접 열 너비 조절을 담당합니다. `위반 항목`은 최초응답 위반·해결시간 위반 배지이며 동시 위반은 같은 행에 두 배지를 표시합니다. `SlaTicketTargets`는 상세의 두 SLA 목표·사용·초과 시간과 반복 주기를 표시합니다. `SlaStatusDurations`는 닫힘을 뺀 시간 합계의 비율 막대와 상태명·시간·비율 tooltip을 표시합니다. 통합 목록의 영속 설정은 `useTablePreferences`의 `sla-violations:combined` 키를 사용하며 이전 분리 목록의 설정을 재사용하지 않습니다. [SLA 계약](../../backend/docs/08_sla_violation_report.md)을 참고하세요.

`BrandLogo`, `IssueTypeBadge`, `StatusBadge`는 공통 브랜드와 의미별 하이라이트를 담당합니다. 스타일 값을 개별 위젯에서 추가하지 않고 [디자인 토큰](SHARED.md)을 사용합니다.

## 이슈 컬럼 검색

전체 이슈와 대시보드·과거 보고서·연간 보고서의 `RecentIssuesWidget`은 모든 이슈 컬럼에서 같은 검색 기능을 제공합니다. 데스크톱은 컬럼명 아래에, 모바일은 표 위에 검색창을 표시하며 입력 즉시 전체 목록을 검색합니다. 여러 컬럼의 검색 조건은 AND로 결합하고 기존 경과일·업무 유형·현재 상태·반기 필터와 함께 적용합니다.

제목 옆의 `티켓 타입`은 Jira `type`을 사용합니다. `서비스 요청`은 `서비스요청`으로 표시하고 인시던트·개선 및 다른 유형은 원래 이름을 유지합니다. 값이 없으면 `확인 불가`로 표시합니다. 모바일 카드와 PDF·Excel에도 포함하며 컬럼 검색은 서비스요청의 띄어쓰기 유무를 구분하지 않습니다.

`domain/IssueColumnSearch.ts`는 검색 조건과 순수 필터링을, `useIssueColumnSearch`는 위젯별 검색 상태를, `ColumnSearchInput`은 공통 입력 UI를 담당합니다. 컬럼명은 `presentation/config/issueColumns.ts`에서 공유합니다. 검색 조건이 바뀌면 첫 페이지로 이동하며 정렬과 컬럼 너비는 유지합니다. 데이터 갱신은 검색 조건과 현재 페이지를 유지합니다.

PDF와 Excel에는 내보내기 시작 시 복사한 검색 조건과 일치하는 전체 행을 포함하고 검색 입력 UI는 제외합니다. 내보내기 중 화면의 검색 조건을 바꿔도 파일의 결과는 바뀌지 않습니다.

대시보드의 최근 이슈 현황은 댓글 컬럼 대신 각 행과 모바일 카드에 SLA 현황과 같은 작은 화살표 상세 버튼을 표시합니다. 버튼을 누르면 `IssueDetailsPanel`에서 본문, 최근 댓글 5개, `댓글 더보기` 순서로 표시합니다. 본문과 댓글은 펼칠 때 조회하고 각각 로딩·빈 내용·실패 재시도를 처리하며 첨부 이미지를 표시합니다. `댓글 더보기`는 최신순 댓글 목록을 5개씩 늘립니다. 상세 버튼은 Jira 이동과 분리되며 펼친 상태는 이슈 키를 기준으로 정렬·검색 중 유지됩니다. 댓글 영역은 장기 이슈 화면과 같은 `IssueCommentsPanel`을 사용합니다. 현재·과거·연간 보고서의 ID를 함께 전달하여 해당 보고서의 최근 이슈인지 확인하며, 본문과 댓글은 조회 시점의 Jira 내용입니다. PDF·Excel에는 펼친 본문·댓글과 상세 버튼을 포함하지 않습니다.

전체 이슈의 컬럼 검색 상태는 `IssueManagementPage`가 소유하고 `RecentIssuesWidget`에 전달합니다. 상단에서 PDF 또는 Excel (.xlsx)을 선택하면 업무 유형·현재 상태·반기·제목·적용된 경과일과 이슈·제목·티켓 타입·진행 상태·보고자·담당자·TAC 담당자·생성일 (경과) 컬럼 검색을 함께 적용해 모든 페이지의 일치 행을 내보냅니다. 목록도 항목별로 복사하여 자동 동기화와 분리하고 적용 조건 및 마지막 동기화 시각을 기록합니다. 최초 수집이 끝나기 전에는 내보내기를 비활성화하며 빈 검색 결과도 그대로 내보냅니다.

전체 이슈에서는 `경과일` 드롭다운으로 생성일 기준과 각 상태의 전이일 기준을 선택합니다. 상태를 선택하면 현재 상태와 관계없이 해당 상태로 가장 최근 전이한 날짜부터 오늘까지 한국 시간의 날짜 차이로 비교합니다. 예를 들어 어제 닫혔다가 오늘 재오픈한 이슈도 `닫힘 · 1일 이하`에 포함됩니다. 실제 전이 이력이 없는 상태는 제외하고, 0일은 오늘 전이한 이슈를 뜻합니다. 별도의 현재 상태·유형·제목·컬럼 필터는 AND로 적용됩니다. 드롭다운·일수·이상/이하는 검색 버튼을 눌렀을 때 함께 적용되며 초기화하면 생성일 기준으로 돌아갑니다. 상태 이력 수집 전에는 상태 기준 검색을 기다리고, 내보내기는 적용된 상태와 전이 경과일을 복사하여 자동 갱신 중에도 같은 결과를 유지합니다.

전체 이슈도 같은 상세 화살표와 `IssueDetailsPanel`을 사용합니다. `detailsSource="issue-management"`가 본문·댓글·이미지 조회에 전파되며 `useIssueContent`가 전체 이슈 gateway와 별도 캐시 키를 선택합니다. 서버는 저장된 전체 이슈 목록에 포함된 티켓인지 확인하고 공통 `IssueDetailsService`로 내용을 조회하므로, 최근 보고서에 없는 이전·완료 티켓도 펼칠 수 있습니다. 목록을 열거나 내보낼 때 전체 본문·댓글을 미리 조회하지 않습니다.

## 대시보드 다운로드

현재 대시보드·과거 보고서·연간 보고서에서 다운로드 형식을 PDF 또는 Excel (.xlsx)로 선택할 수 있습니다. 기간·업무 유형·현재 상태·경과일·컬럼 검색 조건을 동일한 스냅샷으로 고정합니다. 생성 중에는 형식 선택과 내보내기 버튼을 비활성화하며 실패하면 다시 시도할 수 있습니다.

Excel은 `내보내기 정보` 시트에 기간과 적용 필터를, 각 데이터 시트에 지표·분석·차트 수치·표 전체를 담습니다. 차트 수치는 숫자 셀로 저장하고 데이터가 없는 값은 빈 셀로 유지합니다. 티켓 링크와 긴 제목은 보존하며 이슈 문자열은 수식으로 해석하지 않습니다. 연간 재배포 지표의 기존 전체 연도 기준도 필터 설명에 포함합니다.

`DashboardPdfExportStage`가 두 형식의 준비·캡처·다운로드 수명을 공유합니다. Presentation은 Application의 `DashboardExportGateway`만 호출하고 `main.tsx`가 PDF 및 Excel adapter를 조립합니다. Excel 직렬화는 Infrastructure에서 기존 `xlsx` 의존성을 지연 로딩하여 수행합니다.

## File preview

`FilePreviewModal`은 PDF, Word, Excel, Markdown, 이미지와 텍스트를 표시합니다. Storage gateway를 주입받아 preview·download URL을 생성하며 token과 API base URL의 세부사항을 직접 구성하지 않습니다.
