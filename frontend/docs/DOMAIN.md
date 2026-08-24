# Frontend Domain Models

`src/domain`은 순수 TypeScript 타입만 포함하며 React, axios, Zustand에 의존하지 않습니다.

| 파일 | 주요 모델 |
|------|-----------|
| `Auth.ts` | `LoginRequest`, `TokenResponse`, `MeResponse` |
| `Config.ts` | Jira base URL을 가진 `AppConfig` |
| `Issue.ts` | 공통 Jira `RecentIssue` |
| `Job.ts` | `TriggerParams`, `TriggerAccepted`, `JobStatus` |
| `Partner.ts` | `PartnerOrg`, `PartnerMember`, `PartnerIssue` |
| `Report.ts` | `ReportSummary`, `ReportDetail`, `WidgetResult`, `AiAnalysis` |
| `Search.ts` | Jira·Confluence 검색 표시용 `SearchResult` |
| `Site.ts` | 사이트 aggregate, 하위 이력, create/update payload |
| `SlaDashboard.ts` | 최근 이슈 활동과 최근 댓글 표시 계약 |
| `Storage.ts` | `StorageItem`, `StorageFile`, `StorageQuota` |
| `Dashboard.ts` | SLA·월별·상태별 widget 표시 모델 |
| `WidgetId.ts` | 대시보드 최초 렌더 순서에 맞춘 widget ID 계약 |

## Report와 dashboard

`ReportDetail`은 summary 필드에 widget map과 선택적 AI 분석을 추가합니다. 서버 widget의 서로 다른 breakdown 구조를 React component 내부에서 즉석 추론하지 않고 `useDashboardData`가 `Dashboard.ts`의 표시 모델로 변환합니다. 첫 번째 대시보드의 w1부터 w14까지 모든 위젯은 Jira 프로젝트의 모든 요청 유형을 기본값으로 표시합니다. 화면 최상단 요청 유형 토글은 설정된 유형의 상세·유형별 집계를 조합해 카드, 모달, 월별 차트, SLA 차트, 분석 차트와 최근 이슈 현황을 즉시 다시 계산합니다. 토글 목록에 없는 유형은 `always_included` 집계 또는 상세의 미등록 유형 판별을 통해 항상 포함합니다. 일부 토글 유형을 제외한 동안에는 전체 유형을 기준으로 생성된 AI 분석을 숨깁니다. w3 생성·완료 건수에는 보고서 쿼리의 시작일과 종료일을 포함한 기간 일수가 표시됩니다. w7 미완료 이슈 상세는 `WorkTypeOpenWidget`으로 분류되어 지원 요청, 개선 요청, 인시던트 보고, CVE의 현재 열린 요청 건수를 제공합니다.

widget ID는 화면에서 데이터가 처음 렌더링되는 순서를 따릅니다.

`SlaDashboardIssue`는 최신 보고서의 최근 이슈 티켓 번호, 최초 생성 시각, 댓글을 포함한 마지막 업데이트 시각, 진행 상태를 표현합니다. `SlaDashboardComment`는 접힌 티켓 행을 펼칠 때 조회하는 최근 댓글의 작성자, 본문, 작성·수정 시각을 표현합니다.

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
| w14 | 유형별 평균 처리일 |

## Site aggregate

`SiteDetail`은 contact, access credential, node, patch history, visit history를 포함합니다. 하위 resource 변경 API도 서버 계약에 맞춰 갱신된 전체 `SiteDetail`을 반환합니다. payload 타입은 Domain에 위치하지만 전송 자체는 Application gateway와 Infrastructure adapter가 담당합니다.

## Storage

`StorageItem`은 파일과 폴더를 `is_dir`로 구분하고, `StorageQuota`는 used, limit, available, percent를 표현합니다. 브라우저 `File`이나 download URL 생성은 Domain 책임이 아닙니다.

## 경계 규칙

Domain에 HTTP status, axios response, React props, query key, CSS token을 추가하지 않습니다. 외부 동작은 `application/ports`, 화면 전용 모델과 상수는 `presentation`이 소유합니다.
