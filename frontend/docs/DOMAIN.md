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
| `Storage.ts` | `StorageItem`, `StorageFile`, `StorageQuota` |
| `Dashboard.ts` | SLA·월별·상태별 widget 표시 모델 |
| `WidgetId.ts` | 대시보드 최초 렌더 순서에 맞춘 widget ID 계약 |

## Report와 dashboard

`ReportDetail`은 summary 필드에 widget map과 선택적 AI 분석을 추가합니다. 서버 widget의 서로 다른 breakdown 구조를 React component 내부에서 즉석 추론하지 않고 `useDashboardData`가 `Dashboard.ts`의 표시 모델로 변환합니다. w1 연간 생성과 w2 연간 해결은 프로젝트 전체 이슈 유형 중 `라이센스 요청`을 제외합니다. w3 생성·완료 건수에는 보고서 쿼리의 시작일과 종료일을 포함한 기간 일수가 표시됩니다. w7 미완료 이슈 상세는 `WorkTypeOpenWidget`으로 분류되어 지원 요청, 개선 요청, 인시던트 보고, CVE의 현재 열린 요청 건수를 제공합니다.

widget ID는 화면에서 데이터가 처음 렌더링되는 순서를 따릅니다.

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
