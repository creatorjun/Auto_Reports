# backend/docs/02_api_reference.md

# API Reference

**Base URL**: `/api/v1`  
**인증**: Bearer JWT (Access Token) — `Authorization: Bearer <token>`  
`LOGIN=false` 환경변수 설정 시 인증 비활성화 (개발 모드)

---

## Auth (`/auth`)

### POST `/auth/login`

| 항목 | 내용 |
|------|------|
| 설명 | 로그인. access token 반환, refresh token은 HttpOnly 쿠키 설정 |
| 인증 | 불필요 |
| Body | `{ "username": string, "password": string }` |
| 응답 200 | `{ "access_token": string, "token_type": "bearer" }` |
| 응답 401 | Invalid credentials |
| 응답 404 | `LOGIN=false`일 때 Auth not enabled |

**비고**: `SUPERADMIN` 계정으로 로그인 시 generation 기반 토큰 생성 (세션 강제 만료 지원)

---

### POST `/auth/refresh`

| 항목 | 내용 |
|------|------|
| 설명 | refresh token 쿠키로 access token 재발급 |
| 인증 | Cookie: `refresh_token` |
| 응답 200 | `{ "access_token": string, "token_type": "bearer" }` |
| 응답 401 | 쿠키 없거나 토큰 만료 |

---

### POST `/auth/logout`

| 항목 | 내용 |
|------|------|
| 설명 | refresh token 쿠키 삭제 |
| 응답 200 | `{ "detail": "Logged out" }` |

---

### GET `/auth/me`

| 항목 | 내용 |
|------|------|
| 설명 | 현재 로그인된 사용자 정보 조회 |
| 응답 200 | `{ "username": string, "login_required": bool }` |
| 응답 401 | 미인증 |

---

## Trigger (`/trigger`)

### POST `/trigger/`

| 항목 | 내용 |
|------|------|
| 설명 | 보고서 생성 잡 실행 (비동기 백그라운드) |
| 인증 | 필요 |
| Body | `{ "start_date": "YYYY-MM-DD"(optional), "end_date": "YYYY-MM-DD"(optional) }` |
| 응답 202 | `{ "job_id": string, "message": string }` |
| 응답 409 | 이미 실행 중인 잡 존재 |

**비고**: `start_date`, `end_date` 미입력 시 자동 주간 범위 계산

---

### GET `/trigger/{job_id}/status`

| 항목 | 내용 |
|------|------|
| 설명 | 잡 상태 폴링 조회 |
| 응답 200 | `JobStatusSchema` |
| 응답 404 | 존재하지 않는 job_id |

**JobStatusSchema**:
```json
{
  "job_id": "string",
  "status": "pending | running | done | error",
  "report_id": 1,
  "error": null
}
```

---

### GET `/trigger/{job_id}/stream`

| 항목 | 내용 |
|------|------|
| 설명 | SSE(Server-Sent Events)로 잡 진행 상황 실시간 스트리밍 |
| Content-Type | `text/event-stream` |
| 타임아웃 | 300초 |
| keepalive | 15초마다 `: keepalive` 전송 |

**SSE 이벤트 유형**:

| event | 설명 |
|-------|------|
| `status` | 현재 상태 페이로드 (pending/running) |
| `done` | 완료 (done/error 포함) |
| `error` | job_id 없음 오류 |
| `timeout` | 300초 초과 타임아웃 |

---

## Reports (`/reports`)

### GET `/reports/`

| 항목 | 내용 |
|------|------|
| 설명 | 저장된 보고서 목록 조회 |
| 응답 200 | `list[ReportSummary]` |

---

### GET `/reports/{report_id}`

| 항목 | 내용 |
|------|------|
| 설명 | 보고서 상세 조회 (캐시 우선 → DB 폴백) |
| 응답 200 | `ReportDetail` |
| 응답 404 | 보고서 없음 |

---

### GET `/reports/latest`

| 항목 | 내용 |
|------|------|
| 설명 | 가장 최근 보고서 조회 |
| 응답 200 | `ReportDetail` |
| 응답 404 | 보고서 없음 |

---

## Sites (`/sites`)

### GET `/sites/`

| 항목 | 내용 |
|------|------|
| 설명 | 전체 사이트 목록 (요약 정보) |
| 응답 200 | `list[SiteSummaryResponse]` |

---

### GET `/sites/search`

| 항목 | 내용 |
|------|------|
| 설명 | 사이트명/고객명 검색 |
| Query | `q: str` (필수, min 1), `limit: int` (1~100, 기본 10) |
| 응답 200 | `list[SiteSummaryResponse]` |

---

### GET `/sites/recent`

| 항목 | 내용 |
|------|------|
| 설명 | 최근 수정된 사이트 목록 |
| Query | `limit: int` (1~50, 기본 5) |
| 응답 200 | `list[SiteSummaryResponse]` |

---

### GET `/sites/{site_id}`

| 항목 | 내용 |
|------|------|
| 설명 | 사이트 상세 조회 |
| 응답 200 | `SiteResponse` (노드, 패치이력, 방문이력, 접근 자격증명 포함) |
| 응답 404 | 사이트 없음 |

---

### POST `/sites/`

| 항목 | 내용 |
|------|------|
| 설명 | 사이트 생성 |
| Body | `SiteCreateRequest` |
| 응답 201 | `SiteResponse` |

---

### PATCH `/sites/{site_id}`

| 항목 | 내용 |
|------|------|
| 설명 | 사이트 부분 수정 |
| Body | `SiteUpdateRequest` (모든 필드 optional) |
| 응답 200 | `SiteResponse` |
| 응답 404 | 사이트 없음 |

---

### DELETE `/sites/{site_id}`

| 응답 | 내용 |
|------|------|
| 204 | 삭제 성공 |
| 404 | 사이트 없음 |

---

### POST `/sites/{site_id}/nodes`

| 항목 | 내용 |
|------|------|
| 설명 | 배포 노드 추가 |
| Body | `DeploymentNodeCreateRequest` |
| 응답 201 | `DeploymentNodeSchema` |

---

### PATCH `/sites/{site_id}/nodes/{node_id}`

| Body | `DeploymentNodeUpdateRequest` (모든 필드 optional) |
|------|-------------------------------------------------|
| 응답 200 | `DeploymentNodeSchema` |

---

### DELETE `/sites/{site_id}/nodes/{node_id}`

| 응답 204 | 삭제 성공 |
|---------|----------|

---

### POST `/sites/{site_id}/patch-histories`

| Body | `PatchHistoryCreateRequest` |
|------|----------------------------|
| 응답 201 | `PatchHistorySchema` |

---

### PATCH `/sites/{site_id}/patch-histories/{ph_id}`

| Body | `PatchHistoryUpdateRequest` |
|------|-----------------------------|
| 응답 200 | `PatchHistorySchema` |

---

### DELETE `/sites/{site_id}/patch-histories/{ph_id}`

| 응답 204 | 삭제 성공 |
|---------|----------|

---

### POST `/sites/{site_id}/visit-histories`

| Body | `VisitHistoryCreateRequest` |
|------|----------------------------|
| 응답 201 | `VisitHistorySchema` |

---

### PATCH `/sites/{site_id}/visit-histories/{vh_id}`

| Body | `VisitHistoryUpdateRequest` |
|------|----------------------------|
| 응답 200 | `VisitHistorySchema` |

---

### DELETE `/sites/{site_id}/visit-histories/{vh_id}`

| 응답 204 | 삭제 성공 |
|---------|----------|

---

## Partners (`/partners`)

### GET `/partners/`

| 설명 | Jira 커스텀 필드 기반 파트너 담당자 목록 조회 |
|------|---------------------------------------------|
| 응답 200 | `list[PartnerSchema]` |

---

## Storage (`/storage`)

### POST `/storage/upload`

| 설명 | 파일 업로드 (multipart/form-data) |
|------|----------------------------------|
| 응답 200 | `{ "file_id": string, "filename": string }` |

---

### GET `/storage/{file_id}`

| 설명 | 파일 다운로드 |
|------|---------------|
| 응답 200 | 파일 바이너리 스트림 |
| 응답 404 | 파일 없음 |

---

### DELETE `/storage/{file_id}`

| 응답 204 | 삭제 성공 |
|---------|----------|
