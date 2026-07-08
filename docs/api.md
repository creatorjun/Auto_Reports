# API 레퍼런스

> **Version 1.0** | 2026-07-09

## Base URL

```
http://<host>/api
```

---

## 엔드포인트 목록

### `GET /api/health`

헬스 체크. 컨테이너 healthcheck에 사용됩니다.

**Response**
```json
{ "status": "ok" }
```

---

### `GET /api/config`

프론트엔드에서 동적으로 읽는 런타임 설정값을 반환합니다.

**Response**
```json
{
  "jira_base_url": "https://your-domain.atlassian.net"
}
```

---

### `GET /api/reports/latest`

DB에 저장된 가장 최근 리포트 데이터를 반환합니다.

**Response** (주요 필드)
```json
{
  "generated_at": "2026-07-09 08:00:00",
  "widgets": {
    "w1":  { "name": "올해 생성 총계",   "total": 312 },
    "w2":  { "name": "올해 해결 총계",   "total": 290 },
    "w3":  {
      "name": "주간 생성 vs 해결",
      "data": {
        "created": 24,
        "resolved": 18,
        "created_details": [
          { "key": "TACEA-9999", "summary": "...", "type": "서비스 요청", "status": "할 일", "created": "2026-07-08 10:30" }
        ],
        "resolved_details": [
          { "key": "TACEA-9998", "summary": "...", "type": "서비스 요청", "resolved": "2026-07-08 15:22" }
        ]
      }
    },
    "w4":  { "name": "이슈 리뷰 중",  "total": 5,  "data": { "issue_details": [ ... ] } },
    "w5":  { "name": "자료 요청 중",  "total": 3,  "data": { "issue_details": [ ... ] } },
    "w6":  { "name": "결과 대기 중",  "total": 8,  "data": { "issue_details": [ ... ] } },
    "w9":  {
      "name": "SLA 준수 vs 위반",
      "data": {
        "initial_response_violations": 2,
        "resolution_violations": 4,
        "violation_distribution": [ ... ]
      }
    },
    "w12": {
      "name": "최근 이슈 현황",
      "data": {
        "issue_details": [
          {
            "key": "TACEA-9990",
            "summary": "...",
            "type": "서비스 요청",
            "status": "구현 중",
            "stage_index": 4,
            "created": "2026-07-01 09:00",
            "elapsed_days": 8
          }
        ]
      }
    }
  }
}
```

---

### `POST /api/trigger`

스케줄러와 무관하게 즉시 리포트를 수집·저장합니다.

**Request Body**: 없음

**Response**
```json
{ "status": "triggered", "message": "리포트 수집이 시작되었습니다." }
```

> 수집은 백그라운드로 실행되며, 완료 후 `/api/reports/latest` 에서 갱신된 데이터를 확인할 수 있습니다.

---

## 공통 오류 응답

| 코드 | 의미 |
|---|---|
| 404 | 저장된 리포트 없음 (최초 실행 전 상태) |
| 500 | 서버 내부 오류 (로그 확인 필요) |
