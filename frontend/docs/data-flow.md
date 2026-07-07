# Frontend 데이터 흐름

> 최종 수정: 2026-07-07

---

## 전체 흐름

```
Jira API
  └─▶ Backend (ReportCollector)
        └─▶ PostgreSQL (Report 저장)
              └─▶ FastAPI REST /api/reports/latest
                    └─▶ React Query (useLatestReport)
                          └─▶ DashboardPage
                                ├─▶ SummaryCard ×8
                                ├─▶ AiSummaryCard
                                ├─▶ SlaOverdueModal (조건부)
                                ├─▶ SlaMonthlyLineChart ×2
                                ├─▶ SlaDonutChart
                                ├─▶ ReasonPieChart
                                ├─▶ TrendLineChart
                                ├─▶ TypeBarChart
                                ├─▶ ResolutionTimeChart
                                └─▶ IssueDetailTable
```

---

## API 응답 구조 (`ReportDetail`)

```typescript
interface ReportDetail {
  id: number
  week_start: string       // "2026-06-30"
  week_end: string         // "2026-07-06"
  report_date: string      // "2026-07-07 14:00"
  ai_analysis?: AiAnalysis
  widgets: {
    w1:  WidgetData   // SLA 초과 이슈
    w2:  WidgetData   // 이슈 리뷰 중
    w3:  WidgetData   // 자료 요청 중
    w4:  WidgetData   // 연구소 대기(담당자 미지정)
    w5:  WidgetData   // 유형별 SLA 지연
    w6:  WidgetData   // 상태별 SLA 지연
    w7:  WidgetData   // SLA 지연 사유
    w8:  WidgetData   // 연간 누적 생성
    w9:  WidgetData   // 연간 누적 해결
    w10: WidgetData   // 유형별 평균 처리일
    w11: WidgetData   // 이슈별 해결시간 상세
    w12: WidgetData   // SLA 만족 vs 위반
    w13: WidgetData   // 결과 대기 중
    w14: WidgetData   // 이번 주 생성 vs 해결
    w15: WidgetData   // 최초 응답 SLA 월별
    w16: WidgetData   // 해결시간 SLA 월별
  }
}

interface WidgetData {
  total: number
  jql?: string
  breakdown?: Record<string, unknown>
}

interface AiAnalysis {
  summary: string
  risks: string[]
  recommendations: string[]
  sentiment: 'good' | 'warning' | 'critical'
}
```

---

## DashboardPage 데이터 매핑

| 변수 | 타입 | 값 |
|---|---|---|
| `w12` | `Record<string, number>` | `w.w12?.breakdown` |
| `w7` | `Record<string, number>` | `w.w7?.breakdown` |
| `w10` | `Record<string, { avg_days, count }>` | `w.w10?.breakdown` |
| `w11` | `Record<string, unknown>` | `w.w11?.breakdown` |
| `w14` | `Record<string, number>` | `w.w14?.breakdown` |
| `w15` | `SlaMonthlyBreakdown` | `w.w15?.breakdown` |
| `w16` | `SlaMonthlyBreakdown` | `w.w16?.breakdown` |
| `details` | `IssueDetail[]` | `w11.issue_details` |
| `overdueIssues` | `OverdueIssue[]` | `w1.breakdown.issue_details` |

---

## 라우팅

| 경로 | 컴포넌트 | 데이터 소스 |
|---|---|---|
| `/` | `DashboardPage` | `useLatestReport()` — 최신 보고서 |
| `/report/:id` | `DashboardPage` | `useReportById(id)` — 특정 보고서 |

---

## Jira 링크 규칙

이슈 키를 클릭 가능한 링크로 표시하는 컴포넌트들은 아래 상수를 사용:

```typescript
const JIRA_BASE = 'https://seculayer.atlassian.net/browse'
// 사용: `${JIRA_BASE}/${issue.key}` → 새 탭으로 열기
```

적용 컴포넌트: `IssueDetailTable`, `SlaOverdueModal`
