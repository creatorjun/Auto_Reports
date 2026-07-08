# 위젯 정의

> **Version 1.0** | 2026-07-09

위젯은 w1~w12까지 총 12개로 구성됩니다. 각 위젯은 독립적인 Collector 클래스가 담당하며 `asyncio.gather`로 병렬 수집됩니다.

## 위젯 목록

| ID | 이름 | Collector | UI 위치 |
|---|---|---|---|
| w1 | 올해 생성 총계 | `SimpleCountCollector` | SummaryCard |
| w2 | 올해 해결 총계 | `SimpleCountCollector` | SummaryCard |
| w3 | 이번 주 생성 / 해결 | `CreatedVsResolvedCollector` | SummaryCard × 2 + 모달 |
| w4 | 이슈 리뷰 중 | `SimpleWithDetailsCollector` | SummaryCard + 모달 |
| w5 | 자료 요청 중 | `SimpleWithDetailsCollector` | SummaryCard + 모달 |
| w6 | 결과 대기 중 | `SimpleWithDetailsCollector` | SummaryCard + 모달 |
| w7 | 월별 생성 건수 | `MonthlyCollector` | 막대 그래프 |
| w8 | 월별 해결 건수 | `MonthlyCollector` | 막대 그래프 |
| w9 | SLA 준수 vs 위반 | `SlaMetVsViolatedCollector` | 원형 차트 |
| w10 | SLA 초과 이슈 | `SimpleWithDetailsCollector` | SummaryCard |
| w11 | 평균 해결 시간 (유형별) | `ResolutionCollector` | 테이블 |
| w12 | 최근 이슈 현황 | `RecentCollector` | 단계별 그래프 테이블 |

---

## 위젯별 상세

### w3 — 이번 주 생성 / 해결

- **생성 이슈**: `created >= "-7d"` 조건, fields: `summary, issuetype, status, created`
- **해결 이슈**: `resolved >= "-7d"` 조건, fields: `summary, issuetype, updated`
- 해결 일시는 `updated` 필드를 사용합니다 (`resolutiondate`가 null인 경우 대비)
- 모달에서 행 전체 클릭 시 Jira 이슈 URL을 새 탭으로 엽니다

### w4 — 이슈 리뷰 중

- `status = "이슈 리뷰 중"` AND `created <= "-{sla_threshold}d"` AND `updated >= "-7d"`
- SLA 임계일 초과 후 리뷰 대기 상태인 이슈 목록
- `elapsed_days` (경과일) 기준 내림차순 정렬

### w5 — 자료 요청 중

- `status = "자료 요청 중"` AND `created <= "-{sla_threshold}d"` AND `updated >= "-7d"`

### w6 — 결과 대기 중

- `status = "결과 대기 중"` AND `created <= "-{sla_threshold}d"` AND `updated >= "-7d"`

### w9 — SLA 준수 vs 위반

- Jira SLA 커스텀 필드(`sd-servicelevelagreement` 타입)를 자동 탐지
- `completedCycles[].breached` 또는 `ongoingCycle.breached` 값으로 위반 여부 판단
- 최초 응답 SLA / 해결 시간 SLA 두 항목을 각각 집계

### w12 — 최근 이슈 현황 (단계별 그래프)

- `status NOT IN (closed_statuses)` ORDER BY `issuekey DESC` 상위 50건
- 이슈 상태를 0~6 단계 인덱스로 매핑:

| 단계 | 상태 | 색상 |
|---|---|---|
| 0 | 할 일 / 재오픈 | 회색 |
| 1 | 자료 요청 중 | 파랑 |
| 2 | 이슈 리뷰 중 | 주황 |
| 3 | 연구소 대기 중 / 검토 중 | 보라 |
| 4 | 구현 중 | 초록 |
| 5 | 배포 파일 검토 중 | 청록 |
| 6 | 결과 대기 중 | 빨강 |

- `StageBar`: 7칸 중 `i <= stageIndex`까지 amber-400으로 채움
- 행 전체 클릭 시 Jira 이슈 URL 새 탭 오픈

---

## 모달 컴포넌트 클릭 동작

모든 모달의 이슈 행은 `<tr onClick>` / 모바일 `<div onClick>` 방식으로 클릭 시 새 탭 오픈합니다.
`<a>` 태그 대신 `window.open(url, '_blank', 'noreferrer')` 를 사용합니다.

| 모달 파일 | 트리거 위젯 |
|---|---|
| `WeeklyCreatedModal.tsx` | w3 생성 |
| `WeeklyResolvedModal.tsx` | w3 해결 |
| `IssueReviewModal.tsx` | w4 |
| `DataRequestModal.tsx` | w5 |
| `ResultPendingModal.tsx` | w6 |
