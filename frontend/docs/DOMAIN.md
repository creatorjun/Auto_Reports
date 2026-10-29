# Frontend Domain Models

문서 기준: 2026-10-21.

`src/domain`은 순수 TypeScript 모델과 필터 정책을 포함하며 React, axios, Zustand에 의존하지 않습니다.

| 파일 | 주요 모델 |
|------|-----------|
| `Auth.ts` | `LoginRequest`, `TokenResponse`, `MeResponse` |
| `Config.ts` | Jira base URL을 가진 `AppConfig` |
| `Issue.ts` | 공통 Jira `RecentIssue` |
| `IssueColumnSearch.ts` | 공통 이슈 컬럼 검색 조건과 순수 목록 필터링 |
| `IssueManagement.ts` | 전체 이슈 동기화 상태와 업무 유형·현재 상태·반기·연도 필터 |
| `Job.ts` | `TriggerParams`, `TriggerAccepted`, `JobStatus` |
| `Partner.ts` | `PartnerOrg`, `PartnerMember`, `PartnerIssue` |
| `Report.ts` | `ReportSummary`, `ReportDetail`, `WidgetResult`, `AiAnalysis` |
| `Search.ts` | Jira·Confluence 검색 표시용 `SearchResult` |
| `Site.ts` | 사이트 aggregate, 하위 이력, create/update payload |
| `SlaDashboard.ts` | 최근 이슈 활동, 본문·첨부 이미지, 댓글과 댓글 페이지 표시 계약 |
| `Storage.ts` | `StorageItem`, `StorageFile`, `StorageQuota` |
| `Dashboard.ts` | SLA·월별·상태별 widget 표시 모델 |
| `DashboardExport.ts` | PDF·Excel 형식, 문서 메타데이터, 섹션, 지표·텍스트·SVG 차트·표 블록과 차트 수치 데이터 |
| `DashboardIssueTypePolicy.ts` | 대시보드·연간 보고서의 통계 제외 및 요청 유형 선택항목 정책 |
| `DashboardStatusPolicy.ts` | 대시보드·연간 보고서·파트너사의 현재 상태 선택 및 표시 순서 정책 |
| `AuditLog.ts` | 감사 이벤트, 검색 조건과 페이지 |
| `ReportPeriod.ts` | day/week/month/year 및 별도 custom 시작·종료 날짜 요청 모델; SLA 위반은 기존 period에서 day 제외 |
| `ReportChartDetails.ts` | 현재 Jira 차트 상세 요청·응답과 저장본 비교 메타데이터 |
| `SLAStatus.ts` | 현재 수집 스냅샷, 고유 티켓·SLA 잔여율/시간·일시정지 상태·상태별 체류시간과 화면 필터/정렬 모델 |
| `SlaViolationReport.ts` | 저장 기간, 티켓·위반 이벤트·상태별 시간·경고 |
| `SlaViolationFilters.ts` | 기본 상태 제외, 유형·상태·반기 교집합 |
| `SlaViolationOverview.ts` | 고유 티켓 카드, 현재 상태 분포, KST 생성 추이와 상세 검색 |
| `SlaViolationSort.ts` | 표시 컬럼별 불변 정렬 |
| `RedeploymentReport.ts` | 독립 재배포 보고서·티켓·선택 범위 |
| `IssueTypeLabel.ts` | 업무 유형 표시와 정규화 |
| `WidgetId.ts` | 대시보드 최초 렌더 순서에 맞춘 widget ID 계약 |

## Report와 dashboard

`ReportDetail`은 summary 필드에 widget map과 선택적 AI 분석을 추가합니다. 서버 widget의 서로 다른 breakdown 구조를 React component 내부에서 즉석 추론하지 않고 `application/services/dashboardData.ts`가 `Dashboard.ts`의 표시 모델로 변환하며 `useDashboardData`는 메모이제이션과 UI 연결을 맡습니다. 대시보드와 연간 보고서는 Jira 요청 유형 `라이선스`를 항상 제외하며, 요청 유형 토글에도 표시하지 않습니다. 보고서 생성 시 라이선스를 제외한 비하위 작업 유형을 `issue_types`에 저장하며, 화면 최상단 요청 유형 토글은 이 목록의 상세·유형별 집계를 조합해 카드, 모달, 월별 차트, SLA 차트, 분석 차트와 최근 이슈 현황을 즉시 다시 계산합니다. 같은 영역의 현재 상태 토글은 보고서 생성 시 저장한 `by_status_type` 교차 집계를 사용해 요청 유형 및 반기 선택과 동시에 적용됩니다. 상태 교차 집계가 없는 기존 보고서에서는 상태 필터를 비활성화하며, 보고서를 갱신하면 사용할 수 있습니다. 파트너 관리 화면도 최신 보고서의 동일한 필터 계약을 사용해 조직·멤버 이슈 목록에 적용합니다. 기존 저장 보고서도 유형별 분해값으로 라이선스를 차감합니다. 상반기·하반기 버튼은 보고서 연도를 기준으로 월별 데이터와 상세 이슈의 생성일·해결일을 교차 필터링하며, 선택하지 않으면 12개월 전체를 표시합니다. 프로젝트 유형 목록 밖의 데이터는 `always_included` 집계 또는 상세의 미등록 유형 판별을 통해 계속 포함하지만, 라이선스는 예외로 항상 제외됩니다. 요청 유형·현재 상태·반기 중 하나를 선택한 동안에는 전체 데이터를 기준으로 생성된 AI 분석을 숨깁니다. w3 생성·완료 건수의 기간은 보고서 시작일·종료일을 포함합니다. 고정 기간 계산 안내는 화면에서 생략합니다. w7 미완료 이슈 상세는 `WorkTypeOpenWidget`으로 분류되어 지원 요청, 개선 요청, 인시던트 보고, CVE의 현재 열린 요청 건수를 제공합니다.

widget ID는 화면에서 데이터가 처음 렌더링되는 순서를 따릅니다.

`DashboardPdfDocument`는 PDF와 Excel이 공유하는 보고서 제목·기간·내보낸 시각·선택 필터와 섹션 목록을 표현합니다. 섹션은 `DashboardPdfBlock`의 지표, 텍스트, SVG 차트, 표 모델로 구성하고 차트의 원본 수치는 `DashboardExportTableData`로 보존합니다. `DashboardExportFormat`은 `pdf`와 `xlsx`를 구분합니다. DOM 탐색과 다운로드 수명 관리는 이 타입에 포함하지 않으며, Presentation이 문서를 구성하고 Application gateway를 통해 Infrastructure의 해당 생성기로 전달합니다.

`SlaDashboardIssue`는 최신 보고서의 최근 이슈 티켓 번호, 최초 생성 시각, 댓글을 포함한 마지막 업데이트 시각, 진행 상태를 표현합니다. `SlaDashboardComment`는 댓글의 작성자, 본문, 작성·수정 시각을 표현합니다. `SlaDashboardCommentPage`는 요청한 `limit`(기본값 5) 이내의 최신순 댓글을 담은 `comments`와 다음 조회 위치인 `next_offset`을 표현하며, 마지막 댓글까지 조회한 응답의 `next_offset`은 `null`입니다. 장기 이슈 화면은 `offset=0`에서 조회 개수를 5개씩 늘리며, 가장 최근에 성공한 누적 응답을 표시합니다.

| ID | 데이터 |
|----|--------|
| w1 | 연간 생성 |
| w2 | 연간 해결 |
| w3 | 기간 생성·해결 |
| w4 | 이슈 리뷰 중 |
| w5 | 자료 요청 중 |
| w6 | 결과 대기 중 |
| w7 | 미완료·최근 이슈 |
| w8 | 월별 등록 |
| w9 | 월별 해결 |
| w10 | 최초응답 SLA 월별 |
| w11 | 해결시간 SLA 월별 |
| w12 | SLA 위반 분포 |
| w13 | SLA 지연 사유 |
| w14 | 유형별 평균 처리일 및 상태별 평균 소요 시간 |
| w15 | 연간 전용 재배포 품질 분석 |

## 보고서 범위와 SLA·재배포

`ReportSummary.scope`는 standard/annual, `report_year`는 연간 전용 연도입니다. 대시보드의 연간 생성도 standard이며 annual 전용 메뉴와 별도입니다. `ReportChartDetails`는 현재 Jira 상세(`source=current_jira`)를 표현하므로 저장 차트와 다른 시점일 수 있습니다.

`SlaStatusSnapshot`은 수집 시각과 잔여율 `0 <= x < 30%`인 미위반 티켓의 현재 값을 전달합니다. 기간·보고서 ID·저장 이력 계약은 없으며 이미 위반한 티켓은 수집 대상에서 제외합니다. `SlaStatusTicket`은 고유 티켓당 하나이고 조건에 맞는 SLA들을 포함합니다. 진행 중·일시정지 SLA가 함께 있는 티켓은 두 범위에 모두 포함될 수 있습니다. `application/services/slaStatus.ts`가 위젯 건수, 검색·현재 상태·SLA 단계의 교집합과 정렬을 순수 함수로 계산합니다. 기본 정렬은 표시 대상 SLA의 최소 잔여율이 낮은 순서입니다. 상태별 체류시간은 서버가 제공한 해결시간 SLA 기준 값을 사용하며 프런트엔드에서 실제 경과시간으로 대체하지 않습니다.

`SlaViolationReport`는 티켓 생성일이 선택 기간에 속하고 생성 시점에 위반 이력이 확인된 티켓의 스냅샷입니다. 같은 SLA 반복 위반은 카드·목록에서 한 티켓으로 계산하고 동시 위반은 교집합입니다. 상태 분포는 저장 현재 상태, 추이는 KST 생성월/일입니다. 닫힘 체류 구간 제외는 표시 정책이며 저장값을 지우지 않습니다.

`RedeploymentReport`는 독립된 2026-01-01 이후 완료 재배포·현재 진행 중 집합입니다. 월별 분류는 `completion_month`이며 `resolved_at`으로 대체하지 않습니다. 연간 보고서 w15의 집계 범위와 혼합하지 않습니다.

## Site aggregate

`SiteDetail`은 contact, access credential, node, patch history, visit history를 포함합니다. 하위 resource 변경 API도 서버 계약에 맞춰 갱신된 전체 `SiteDetail`을 반환합니다. payload 타입은 Domain에 위치하지만 전송 자체는 Application gateway와 Infrastructure adapter가 담당합니다.

## Storage

`StorageItem`은 파일과 폴더를 `is_dir`로 구분하고, `StorageQuota`는 used, limit, available, percent를 표현합니다. 브라우저 `File`이나 download URL 생성은 Domain 책임이 아닙니다.

## 경계 규칙

Domain에 HTTP status, axios response, React props, query key, CSS token을 추가하지 않습니다. 외부 동작은 `application/ports`, 화면 전용 모델과 상수는 `presentation`이 소유합니다.
