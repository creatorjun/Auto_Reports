# Backend Widget 명세

> 최종 수정: 2026-07-07  
> 기준 파일: `src/application/services/report_collector.py`, `query_builder.py`, `widget_id.py`

---

## 위젯 ID 목록

| WidgetId (Enum) | 값 | 설명 |
|---|---|---|
| `OVERDUE_ISSUES` | w1 | SLA 초과 미해결 이슈 |
| `ISSUE_REVIEW` | w2 | 이슈 리뷰 중 상태 지연 |
| `DATA_REQUEST` | w3 | 자료 요청 중 상태 지연 |
| `LAB_UNASSIGNED` | w4 | 연구소 대기 + 담당자 미지정 |
| `SLA_DELAY_BY_TYPE` | w5 | 유형별 SLA 지연 건수 |
| `SLA_DELAY_BY_STATUS` | w6 | 상태별 SLA 지연 건수 |
| `SLA_DELAY_REASON` | w7 | SLA 지연 사유 파이 데이터 |
| `YEARLY_CREATED` | w8 | 2026년 누적 생성 건수 |
| `YEARLY_RESOLVED` | w9 | 2026년 누적 해결 건수 |
| `AVG_RESOLUTION_TYPE` | w10 | 유형별 평균 처리일 |
| `RESOLUTION_REPORT` | w11 | 이슈별 해결시간 상세 보고서 |
| `SLA_MET_VS_VIOLATED` | w12 | SLA 만족 vs 위반 건수 |
| `RESULT_PENDING` | w13 | 결과 대기 중 상태 지연 |
| `CREATED_VS_RESOLVED` | w14 | 이번 주 생성 vs 해결 |
| `SLA_INITIAL_RESPONSE` | w15 | 최초 응답 SLA 월별 달성률 |
| `SLA_RESOLUTION_MONTHLY` | w16 | 해결시간 SLA 월별 달성률 |

---

## 위젯 상세

### w1 — SLA 초과 미해결 이슈

**JQL 조건**
```
project = {PROJECT_KEY}
AND issuetype IN (...)
AND created <= "-{SLA_THRESHOLD}d"
AND updated >= "-7d"
AND status NOT IN ({CLOSED_STATUSES})
```

**WidgetResult.breakdown 구조**
```json
{
  "by_type": {
    "인시던트": { "이슈 리뷰 중": 3, "자료 요청 중": 1 },
    "서비스 요청": { "결과 대기 중": 2 }
  },
  "issue_details": [
    {
      "key": "TACEA-4345",
      "summary": "[한전원자력연료] eyeCloud SIM 제품 로그...",
      "type": "인시던트",
      "created": "2026-01-01 09:00",
      "resp_status": "진행 중",
      "over_h": 988.6
    }
  ]
}
```
- `issue_details`는 초과시간(`over_h`) 내림차순 정렬
- `resp_status`: 해결됐으면 `"종료"`, 미해결이면 `"진행 중"`
- `over_h`: 생성일로부터 경과시간 - SLA 임계값(시간) = 초과분

---

### w2 — 이슈 리뷰 중 지연

**JQL 조건**
```
... AND status = "이슈 리뷰 중"
AND created <= "-{SLA_THRESHOLD}d"
AND updated >= "-7d"
AND status NOT IN ({CLOSED_STATUSES})
```

**WidgetResult**
```json
{ "total": 5, "jql": "...", "breakdown": null }
```

---

### w3 — 자료 요청 중 지연

**JQL 조건**
```
... AND status = "자료 요청 중"
AND created <= "-{SLA_THRESHOLD}d" ...
```

**WidgetResult**: `total`만 사용 (단순 카운트)

---

### w4 — 연구소 대기 (담당자 미지정)

**JQL 조건**
```
... AND status = "연구소 대기 중"
AND assignee IS EMPTY
AND created <= "-{SLA_THRESHOLD}d"
AND updated >= "-7d"
```

**WidgetResult**: `total`만 사용

---

### w5 — 유형별 SLA 지연

**WidgetResult.breakdown 구조**
```json
{ "인시던트": 8, "서비스 요청": 12, "개선": 3 }
```

---

### w6 — 상태별 SLA 지연

**WidgetResult.breakdown 구조**
```json
{ "이슈 리뷰 중": 5, "자료 요청 중": 3, "결과 대기 중": 2, "연구소 대기 중": 7 }
```

---

### w7 — SLA 지연 사유 (파이)

**WidgetResult.breakdown 구조**
```json
{
  "TAC 처리 지연": 4,
  "연구소 대기": 7,
  "개발 진행 중": 3,
  "고객 응답 대기": 5,
  "보류": 1,
  "영업 검토": 2
}
```

---

### w8 / w9 — 연간 누적 생성 / 해결

**JQL 조건** (w8 예시)
```
... AND created >= "2026-01-01"
```

**WidgetResult**: `total`만 사용

---

### w10 — 유형별 평균 처리일

**대상**: 최근 7일 내 해결된 이슈

**WidgetResult.breakdown 구조**
```json
{
  "인시던트": { "avg_days": 5.2, "avg_hours": 124.8, "count": 10 },
  "서비스 요청": { "avg_days": 3.1, "avg_hours": 74.4, "count": 8 }
}
```

---

### w11 — 이슈별 해결시간 상세 보고서

**대상**: 최근 7일 내 해결된 이슈 (최대 200건)

**WidgetResult.breakdown 구조**
```json
{
  "avg_resolution_hours": 96.5,
  "avg_resolution_days": 4.0,
  "resolution_breached": 3,
  "total_issues": 18,
  "issue_details": [
    {
      "key": "TACEA-4539",
      "summary": "[주택도시보증공사] postgres 15 버전...",
      "type": "서비스 요청",
      "resolution_h": 16.95,
      "res_breached": false
    }
  ]
}
```
- `issue_details` 최대 20건
- `res_breached`: `resolution_h > SLA_THRESHOLD * 24` 이면 `true`

---

### w12 — SLA 만족 vs 위반

**대상**: 최근 7일 내 해결된 이슈
- 만족: `resolved >= -7d AND created >= -{SLA_THRESHOLD}d`
- 위반: `resolved >= -7d AND created <= -{SLA_THRESHOLD}d`

**WidgetResult.breakdown 구조**
```json
{ "SLA 만족": 15, "SLA 위반": 3 }
```

---

### w13 — 결과 대기 중 지연

**JQL 조건**
```
... AND status = "결과 대기 중"
AND created <= "-{SLA_THRESHOLD}d" ...
```

**WidgetResult**: `total`만 사용

---

### w14 — 이번 주 생성 vs 해결

**WidgetResult.breakdown 구조**
```json
{ "생성": 7, "해결": 5 }
```

---

### w15 — 최초 응답 SLA 월별 달성률

**대상**: 최근 6개월, Jira SLA 필드(`sla_initial_response_field_id`) 사용

**WidgetResult.breakdown 구조**
```json
{
  "monthly": [
    { "month": "2월", "year": 2026, "month_num": 2, "rate": 92.5, "met": 37, "total": 40 },
    ...
  ]
}
```

---

### w16 — 해결시간 SLA 월별 달성률

**구조**: w15와 동일, Jira SLA 필드만 다름 (`sla_resolution_field_id`)

---

## 공통 WidgetResult 스키마

```python
@dataclass
class WidgetResult:
    name: str              # 위젯 표시명
    total: int             # 대표 집계 숫자
    jql: str | None        # 사용된 JQL (단순 카운트 위젯)
    breakdown: dict | None # 위젯별 세부 데이터
```

---

## 환경 변수 / Settings 참조

| 변수 | 설명 |
|---|---|
| `JIRA_PROJECT_KEY` | Jira 프로젝트 키 (예: `TACEA`) |
| `SLA_THRESHOLD_DAYS` | SLA 기준일 (기본: 30일) |
| `JIRA_ISSUE_TYPES` | 집계 대상 이슈 유형 목록 |
| `JIRA_CLOSED_STATUSES` | 종료 상태 목록 |
| `JIRA_ACTIVE_STATUSES` | 진행 중 상태 목록 |
| `SLA_INITIAL_RESPONSE_FIELD_ID` | Jira 최초응답 SLA 커스텀 필드 ID |
| `SLA_RESOLUTION_FIELD_ID` | Jira 해결시간 SLA 커스텀 필드 ID |
