# Frontend 컴포넌트 명세

> 최종 수정: 2026-07-07  
> 기준 경로: `frontend/src/presentation/components/`

---

## 카드 컴포넌트 (`cards/`)

### SummaryCard

대시보드 상단 요약 수치 카드.

| Props | 타입 | 필수 | 설명 |
|---|---|---|---|
| `label` | `string` | ✅ | 카드 제목 |
| `value` | `number \| string` | ✅ | 표시 숫자 |
| `sub` | `string` | - | 보조 텍스트 |
| `color` | `blue \| red \| green \| yellow \| gray` | - | 색상 테마 (기본: blue) |
| `onClick` | `() => void` | - | 클릭 핸들러. 전달 시 커서·hover ring 활성화 |

**현재 카드 배치 순서 (DashboardPage)**

| 순서 | 라벨 | 데이터 출처 | 색상 | 클릭 |
|---|---|---|---|---|
| 1 | 이번 주 생성 | `w14.breakdown["생성"]` | blue | - |
| 2 | 이번 주 해결 | `w14.breakdown["해결"]` | green | - |
| 3 | 2026 생성 | `w8.total` | gray | - |
| 4 | 2026 해결 | `w9.total` | gray | - |
| 5 | SLA 초과 | `w1.total` | red | ✅ SlaOverdueModal 오픈 |
| 6 | 이슈 리뷰 중 | `w2.total` | yellow | - |
| 7 | 자료 요청 중 | `w3.total` | yellow | - |
| 8 | 결과 대기 중 | `w13.total` | yellow | - |

---

### AiSummaryCard

AI 분석 결과 표시 카드. `report.ai_analysis` 존재 시에만 렌더링.

| Props | 타입 | 설명 |
|---|---|---|
| `ai` | `AiAnalysis` | `summary / risks / recommendations / sentiment` |

`sentiment` 값에 따라 카드 색상 변경: `good`→초록, `warning`→노랑, `critical`→빨강

---

## 차트 컴포넌트 (`charts/`)

### SlaDonutChart

SLA 만족 / 위반 도넛 차트.

| Props | 타입 | 설명 |
|---|---|---|
| `met` | `number` | `w12.breakdown["SLA 만족"]` |
| `violated` | `number` | `w12.breakdown["SLA 위반"]` |

---

### ReasonPieChart

SLA 지연 사유 파이 차트.

| Props | 타입 | 설명 |
|---|---|---|
| `breakdown` | `Record<string, number>` | `w7.breakdown` — 사유명: 건수 |

---

### TrendLineChart

이번 주 생성 vs 해결 추세 미니 차트.

| Props | 타입 | 설명 |
|---|---|---|
| `created` | `number` | `w14.breakdown["생성"]` |
| `resolved` | `number` | `w14.breakdown["해결"]` |

---

### TypeBarChart

유형별 평균 처리일 막대 차트.

| Props | 타입 | 설명 |
|---|---|---|
| `breakdown` | `Record<string, { avg_days: number; count: number }>` | `w10.breakdown` |

---

### ResolutionTimeChart

이슈별 해결시간 산점도 / 바 차트.

| Props | 타입 | 설명 |
|---|---|---|
| `details` | `IssueDetail[]` | `w11.breakdown.issue_details` |

---

### SlaMonthlyLineChart

SLA 월별 달성률 라인 차트. w15(최초응답), w16(해결시간) 각각 하나씩 렌더링.

| Props | 타입 | 설명 |
|---|---|---|
| `title` | `string` | 차트 제목 |
| `subtitle` | `string` | 부제목 |
| `monthly` | `MonthlyEntry[]` | `{ month, year, month_num, rate, met, total }` |
| `color` | `string` | 라인 색상 hex |

---

## 테이블 컴포넌트 (`tables/`)

### IssueDetailTable

이슈별 해결시간 상세 테이블. `w11.breakdown.issue_details` 데이터 사용.

| 컬럼 | 데이터 | 비고 |
|---|---|---|
| 키 | `key` | Jira 링크 (`https://seculayer.atlassian.net/browse/{key}`), 새 탭 |
| 요약 | `summary` | 최대 40자 truncate |
| 유형 | `type` | 이슈 유형명 |
| 해결시간 | `resolution_h` | `{n}h` 형식 |
| 상태 | `res_breached` | `true` → SLA 위반 뱃지, `false` → SLA 만족 뱃지 |

---

### SlaOverdueModal

SLA 초과 카드 클릭 시 오버레이로 표시되는 모달. `w1.breakdown.issue_details` 데이터 사용.

**닫기**: ESC 키, 배경 클릭, 닫기 버튼

| 컬럼 | 데이터 | 비고 |
|---|---|---|
| 이슈 번호 | `key` | Jira 링크, 새 탭 |
| 제목 | `summary` | 최대 60자 truncate |
| 유형 | `type` | 이슈 유형명 |
| 생성일시 | `created` | `YYYY-MM-DD HH:mm` |
| 응답상태 | `resp_status` | `"진행 중"` 또는 `"종료"` |
| 초과시간 | `over_h` | `+{n}h` 빨간색 강조, 내림차순 정렬 |

| Props | 타입 | 설명 |
|---|---|---|
| `issues` | `OverdueIssue[]` | w1 issue_details 배열 |
| `total` | `number` | w1.total (헤더 표시용) |
| `onClose` | `() => void` | 닫기 콜백 |
