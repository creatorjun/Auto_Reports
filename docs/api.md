# API 명세 v1.0

Base URL: `http://<host>/api/v1`

모든 응답은 `application/json` 입니다.  
`LOGIN=true` 인 경우 ⚠️ 표시 엔드포인트는 `Authorization: Bearer <token>` 헤더가 필요합니다.

---

## 인증

### POST `/auth/login`

로그인하여 JWT 토큰을 발급합니다.

**Request Body**
```json
{ "username": "ADMIN", "password": "your_password" }
```

**Response 200**
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

---

## 보고서

### GET `/reports` ⚠️

보고서 목록을 반환합니다.

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `limit` | int | 20 | 최대 반환 수 |
| `offset` | int | 0 | 오프셋 |

**Response 200** — `ReportSummary[]`
```json
[
  {
    "id": 1,
    "week_start": "2026-06-30",
    "week_end": "2026-07-06",
    "report_date": "2026-07-04",
    "created_at": "2026-07-04T23:00:01+09:00"
  }
]
```

### GET `/reports/latest` ⚠️

가장 최근 보고서의 전체 데이터를 반환합니다.

**Response 200** — `ReportDetail`
```json
{
  "id": 1,
  "week_start": "2026-06-30",
  "week_end": "2026-07-06",
  "report_date": "2026-07-04",
  "ai_analysis": "이번 주 총 32건의 이슈가 ...",
  "widgets": {
    "w1": { "total": 120, "data": null },
    "w3": { "total": 12, "data": { "created": 8, "resolved": 4, ... } },
    ...
  }
}
```

**Response 204** — 보고서 없음

### GET `/reports/{id}` ⚠️

특정 ID 의 보고서 전체 데이터를 반환합니다.

**Response 200** — `ReportDetail`  
**Response 404** — 보고서 없음

### DELETE `/reports/{id}` ⚠️

보고서를 삭제합니다. 연결된 위젯도 cascade 삭제됩니다.

**Response 204**

---

## 보고서 생성 (Trigger)

### POST `/trigger` ⚠️

비동기 보고서 생성 Job 을 시작합니다.

**Request Body**
```json
{
  "start_date": "2026-06-30",
  "end_date":   "2026-07-06"
}
```

**Response 202**
```json
{ "job_id": "550e8400-e29b-41d4-a716-446655440000" }
```

### GET `/jobs/{job_id}` ⚠️

Job 상태를 폴링합니다. 프론트엔드는 2초 간격으로 최대 3분간 폴링합니다.

**Response 200**
```json
{
  "status": "done",
  "report_id": 5,
  "error": null
}
```

`status` 가능값: `pending` | `running` | `done` | `error`

**Response 404** — Job 없음

---

## 검색

### GET `/search` ⚠️

저장된 모든 보고서의 위젯 데이터에서 이슈를 전문 검색합니다.

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `q` | string | 검색어 (이슈 키, 제목 포함 검색) |

**Response 200**
```json
[
  {
    "key": "TAC-1234",
    "summary": "로그인 불가 이슈",
    "status": "해결됨",
    "report_id": 3,
    "week_start": "2026-06-23"
  }
]
```

---

## 파일 스토리지

### GET `/storage` ⚠️

스토리지 디렉토리 트리를 반환합니다.

**Response 200** — `StorageItem[]`

### POST `/storage/upload` ⚠️

파일을 업로드합니다. `multipart/form-data`.

| 필드 | 설명 |
|------|------|
| `file` | 업로드 파일 |
| `path` | 저장 경로 (선택, 기본 루트) |

**Response 201**

### GET `/storage/download` ⚠️

파일을 다운로드합니다.

| 파라미터 | 설명 |
|----------|------|
| `path` | 파일 경로 |

### DELETE `/storage` ⚠️

파일 또는 디렉토리를 삭제합니다.

| 파라미터 | 설명 |
|----------|------|
| `path` | 대상 경로 |

### POST `/storage/mkdir` ⚠️

새 디렉토리를 생성합니다.

**Request Body**
```json
{ "path": "reports/2026" }
```

### POST `/storage/rename` ⚠️

파일 또는 디렉토리 이름을 변경합니다.

**Request Body**
```json
{ "old_path": "foo.txt", "new_path": "bar.txt" }
```

---

## 설정

### GET `/config`

클라이언트가 로그인 기능 활성화 여부를 확인합니다. 인증 불필요.

**Response 200**
```json
{ "login_enabled": true }
```

---

## 헬스체크

### GET `/api/health`

인증 없이 백엔드 생존 여부를 확인합니다.

**Response 200**
```json
{ "status": "ok" }
```
