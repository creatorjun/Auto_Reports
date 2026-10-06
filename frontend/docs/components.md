# Frontend Components

기준 경로는 `src/presentation/components`입니다.

| 폴더 | 책임 |
|------|------|
| `auth` | route 인증 가드 |
| `layout` | Header, Sidebar, MobileTabBar, Outlet layout |
| `common` | loading, error boundary, 검색, 보고서 생성, 공통 modal shell·table |
| `cards` | AI, SLA, 숫자 summary card와 업무 유형별 열린 요청 건수 card |
| `charts` | 월별, SLA, 사유, 처리시간, 유형 Recharts 시각화 |
| `tables` | 이슈 종류별 modal과 history report table |
| `history` | 보고서 삭제 확인 |
| `partner` | 조직, 멤버, 이슈 panel과 row |
| `site` | 생성 form helper와 node·patch·visit section/form |
| `storage` | table, modal, icon, preview, link 복사와 표시 utility |

## 공통 설계

- 원격 동작은 props 또는 Presentation hook을 통해 수행합니다.
- component는 axios adapter를 import하지 않습니다.
- 이슈 표는 `IssueModalShell`과 `IssueTableModal`을 재사용합니다.
- query key와 표시 상수는 `presentation/config`, formatter는 `presentation/utils`를 사용합니다.
- 큰 파일 preview renderer는 lazy loading하고 보고서 생성 modal은 배포 안정성을 위해 메인 bundle에 포함합니다.

## 이슈 컬럼 검색

이슈 관리와 대시보드·과거 보고서·연간 보고서의 `RecentIssuesWidget`은 모든 이슈 컬럼에서 같은 검색 기능을 제공합니다. 데스크톱은 컬럼명 아래에, 모바일은 표 위에 검색창을 표시하며 입력 즉시 전체 목록을 검색합니다. 여러 컬럼의 검색 조건은 AND로 결합하고 기존 경과일·업무 유형·현재 상태·반기 필터와 함께 적용합니다.

`domain/IssueColumnSearch.ts`는 검색 조건과 순수 필터링을, `useIssueColumnSearch`는 위젯별 검색 상태를, `ColumnSearchInput`은 공통 입력 UI를 담당합니다. 컬럼명은 `presentation/config/issueColumns.ts`에서 공유합니다. 검색 조건이 바뀌면 첫 페이지로 이동하며 정렬과 컬럼 너비는 유지합니다. 데이터 갱신은 검색 조건과 현재 페이지를 유지합니다.

PDF와 Excel에는 내보내기 시작 시 복사한 검색 조건과 일치하는 전체 행을 포함하고 검색 입력 UI는 제외합니다. 내보내기 중 화면의 검색 조건을 바꿔도 파일의 결과는 바뀌지 않습니다.

이슈 관리의 컬럼 검색 상태는 `IssueManagementPage`가 소유하고 `RecentIssuesWidget`에 전달합니다. 상단에서 PDF 또는 Excel (.xlsx)을 선택하면 업무 유형·현재 상태·반기·제목·적용된 경과일과 이슈·제목·진행 상태·보고자·담당자·TAC 담당자·생성일 (경과) 컬럼 검색을 함께 적용해 모든 페이지의 일치 행을 내보냅니다. 목록도 항목별로 복사하여 자동 동기화와 분리하고 적용 조건 및 마지막 동기화 시각을 기록합니다. 최초 수집이 끝나기 전에는 내보내기를 비활성화하며 빈 검색 결과도 그대로 내보냅니다.

## 대시보드 다운로드

현재 대시보드·과거 보고서·연간 보고서에서 다운로드 형식을 PDF 또는 Excel (.xlsx)로 선택할 수 있습니다. 기간·업무 유형·현재 상태·경과일·컬럼 검색 조건을 동일한 스냅샷으로 고정합니다. 생성 중에는 형식 선택과 내보내기 버튼을 비활성화하며 실패하면 다시 시도할 수 있습니다.

Excel은 `내보내기 정보` 시트에 기간과 적용 필터를, 각 데이터 시트에 지표·분석·차트 수치·표 전체를 담습니다. 차트 수치는 숫자 셀로 저장하고 데이터가 없는 값은 빈 셀로 유지합니다. 티켓 링크와 긴 제목은 보존하며 이슈 문자열은 수식으로 해석하지 않습니다. 연간 재배포 지표의 기존 전체 연도 기준도 필터 설명에 포함합니다.

`DashboardPdfExportStage`가 두 형식의 준비·캡처·다운로드 수명을 공유합니다. Presentation은 Application의 `DashboardExportGateway`만 호출하고 `main.tsx`가 PDF 및 Excel adapter를 조립합니다. Excel 직렬화는 Infrastructure에서 기존 `xlsx` 의존성을 지연 로딩하여 수행합니다.

## File preview

`FilePreviewModal`은 PDF, Word, Excel, Markdown, 이미지와 텍스트를 표시합니다. Storage gateway를 주입받아 preview·download URL을 생성하며 token과 API base URL의 세부사항을 직접 구성하지 않습니다.
