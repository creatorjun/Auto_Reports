# 위젯 명세 v1.0

대시보드는 **14개 위젯(w1~w14)** 으로 구성됩니다. 각 위젯은 독립적인 Collector 클래스로 구현되며, `widget_key`, `total`, `data(JSONB)` 형태로 PostgreSQL 에 저장됩니다.

---

## 카운트 위젯 (w1~w6)

`count_collector.py` 에서 처리합니다.

| 위젯 | 라벨 | 설명 | Jira JQL 조건 |
|------|------|------|---------------|
| w1 | 올해 생성 | 당해연도 1월 1일 이후 생성된 전체 이슈 수 | `created >= "YYYY-01-01"` |
| w2 | 올해 해결 | 당해연도 1월 1일 이후 해결된 전체 이슈 수 | `resolutiondate >= "YYYY-01-01"` |
| w3 | 주간 생성/완료 | 집계 기간(start~end) 내 생성 및 해결된 이슈 수 + 상세 목록 | `created >= start AND created <= end` |
| w4 | 이슈 리뷰 중 | 현재 '이슈 리뷰 중' 상태인 이슈 수 + 상세 목록 | `status = "이슈 리뷰 중"` |
| w5 | 자료 요청 중 | 현재 '자료 요청 중' 상태인 이슈 수 + 상세 목록 | `status = "자료 요청 중"` |
| w6 | 결과 대기 중 | 현재 '결과 대기 중' 상태인 이슈 수 + 상세 목록 | `status = "결과 대기 중"` |

### w3 data 구조
```json
{
  "created": 8,
  "resolved": 4,
  "created_details": [
    { "key": "TAC-101", "summary": "...", "type": "버그", "priority": "높음",
      "status": "진행 중", "created": "2026-07-01", "reporter": "홍길동",
      "tac_team": "TAC팀" }
  ],
  "resolved_details": [ ... ]
}
```

### w4~w6 data 구조
```json
{
  "issue_details": [
    { "key": "TAC-88", "summary": "...", "type": "문의",
      "status": "이슈 리뷰 중", "created": "2026-06-25",
      "reporter": "김철수", "tac_team": "TAC팀" }
  ]
}
```

---

## SLA 월별 추이 (w7~w8)

`monthly_collector.py` 에서 처리합니다. 최근 6개월의 SLA 준수율을 월별로 집계합니다.

| 위젯 | 라벨 | SLA 기준 |
|------|------|----------|
| w7 | 최초응답 SLA | 최초 응답 시간 위반 여부 |
| w8 | 해결시간 SLA | 최종 해결 시간 위반 여부 |

### data 구조
```json
{
  "monthly": [
    { "month": "2026-02", "total": 18, "violated": 3, "rate": 83.3 },
    { "month": "2026-03", "total": 22, "violated": 1, "rate": 95.5 }
  ]
}
```

---

## SLA 위반 현황 (w9)

`count_collector.py` 에서 처리합니다. SLA 위반 이슈를 최초응답/해결시간 단계별로 집계합니다.

### data 구조
```json
{
  "initial_response_violations": 2,
  "resolution_violations": 1,
  "violation_distribution": [
    { "stage": "최초응답 위반", "count": 2,
      "issue_details": [ { "key": "TAC-55", "summary": "...", ... } ] },
    { "stage": "해결시간 위반", "count": 1, "issue_details": [ ... ] }
  ]
}
```

---

## SLA 지연 사유 (w10)

`sla_delay_collector.py` 에서 처리합니다. SLA 지연 중인 이슈를 현재 상태별로 분류합니다.

### data 구조
```json
{
  "by_status": { "이슈 리뷰 중": 3, "자료 요청 중": 5 },
  "by_status_details": {
    "이슈 리뷰 중": [
      { "key": "TAC-77", "summary": "...", "days_overdue": 3 }
    ]
  }
}
```

---

## 유형별 해결시간 (w11)

`resolution_collector.py` 에서 처리합니다. 이슈 유형별 평균 해결시간을 계산합니다.

### data 구조
```json
{
  "by_type": {
    "버그": { "count": 10, "avg_days": 2.3, "avg_hours": 55.2 },
    "문의": { "count": 25, "avg_days": 0.8, "avg_hours": 19.1 }
  }
}
```

---

## 미완료 이슈 (w12)

`recent_collector.py` 에서 처리합니다. 현재 열려 있는 모든 미완료 이슈 목록입니다.

### data 구조
```json
{
  "issue_details": [
    { "key": "TAC-123", "summary": "...", "type": "버그",
      "status": "진행 중", "created": "2026-07-01",
      "elapsed_days": 9, "reporter": "이영희", "tac_team": "TAC팀" }
  ]
}
```

---

## 월별 등록/해결 건수 (w13~w14)

`monthly_count_collector.py` 에서 처리합니다. 최근 6개월의 월별 등록 및 해결 건수입니다.

| 위젯 | 라벨 |
|------|------|
| w13 | 월별 등록 건수 |
| w14 | 월별 해결 건수 |

### data 구조
```json
{
  "monthly": [
    { "month": "2026-02", "count": 18 },
    { "month": "2026-03", "count": 22 }
  ]
}
```

---

## 위젯 확장 가이드

1. `backend/src/application/widgets/` 에 `BaseWidgetCollector` 를 상속하는 새 Collector 클래스 생성
2. `backend/src/domain/entities/widget_data.py` 에 데이터 타입 추가
3. `job_runner.py` 의 위젯 수집 파이프라인에 등록
4. `frontend/src/presentation/components/charts/` 에 차트 컴포넌트 추가
5. `DashboardPage.tsx` 에 렌더링 로직 추가
