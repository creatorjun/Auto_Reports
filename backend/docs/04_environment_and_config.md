# backend/docs/04_environment_and_config.md

# Environment & Configuration

## 환경변수 목록

`backend/.env` 파일 또는 환경변수로 설정합니다.  
`pydantic-settings`가 `.env` 파일을 자동으로 로드합니다.

### 필수 항목

| 환경변수 | 타입 | 설명 |
|---------|------|------|
| `jira_base_url` | str | Jira Cloud URL (예: `https://yourcompany.atlassian.net`) |
| `jira_email` | str | Jira API 인증 이메일 |
| `jira_api_token` | str | Jira API Token |

---

### Jira 설정

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `project_key` | `"TACEA"` | Jira 프로젝트 키 |
| `issue_types` | `["인시던트", "개선", "CVE", "서비스 요청"]` | 집계 대상 이슈 타입 |
| `active_statuses` | (목록) | 활성 상태 목록 |
| `closed_statuses` | `["Closed", "반려됨", "중복 이슈", "취소됨"]` | 종료 상태 목록 |
| `sla_threshold_days` | `30` | SLA 위반 기준 일수 |
| `sla_initial_response_field_id` | `"customfield_12152"` | SLA 초기 응답 커스텀 필드 ID |
| `sla_resolution_field_id` | `"customfield_12151"` | SLA 해결 커스텀 필드 ID |
| `jira_tac_assignee_field_id` | `"customfield_10859"` | TAC 담당자 커스텀 필드 ID |
| `jira_qa_assignee_field_id` | `"customfield_12222"` | QA 담당자 커스텀 필드 ID |

---

### AI 설정

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `gemini_api_key` | `""` | Google Gemini API Key |
| `ai_enabled` | `true` | AI 분석 활성화 여부. `false`면 ai_analysis 컬럼 null로 저장 |

---

### 데이터베이스 설정

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `db_user` | `"postgres"` | PostgreSQL 유저 |
| `db_password` | `"postgres"` | PostgreSQL 패스워드 |
| `db_host` | `"db"` | PostgreSQL 호스트 (docker-compose 서비스명) |
| `db_name` | `"auto_reports"` | 데이터베이스 이름 |

**생성되는 DATABASE_URL**: `postgresql+asyncpg://{user}:{password}@{host}/{name}`

---

### 인증/보안 설정

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `LOGIN` | `false` | 로그인 기능 활성화 여부 |
| `ADMIN` | `"admin"` | 일반 관리자 계정명 |
| `ADMIN_PASSWORD` | `""` | 일반 관리자 패스워드 |
| `SUPERADMIN` | `""` | 슈퍼어드민 계정명 (설정 시 generation 기반 강제 로그아웃 지원) |
| `SUPERADMIN_PASSWORD` | `""` | 슈퍼어드민 패스워드 |
| `JWT_SECRET` | `"please-set-JWT_SECRET-in-env"` | **반드시 변경** — JWT 서명 키 |
| `jwt_access_expire_minutes` | `30` | Access token 만료 시간 (분) |
| `jwt_refresh_expire_days` | `7` | Refresh token 만료 시간 (일) |

**주의**: `JWT_SECRET`은 운영 환경에서 반드시 강력한 랜덤 문자열로 교체해야 합니다.

---

### 스케줄러 설정

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `schedule_cron` | `"0 23 * * 5"` | APScheduler cron 표현식 (매주 금요일 23:00) |
| `tz` | `"Asia/Seoul"` | 스케줄러 타임존 |

---

### 기타 설정

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `cors_origins` | `["*"]` | CORS 허용 오리진 목록 |
| `report_retention_weeks` | `52` | 보고서 DB 보존 기간(주). `0`이면 자동 삭제 비활성화 |
| `storage_dir` | `"/app/storage"` | 로컬 파일 스토리지 경로 |
| `confluence_space_key` | `""` | Confluence 스페이스 키 (현재 미사용) |
| `confluence_parent_page_id` | `""` | Confluence 부모 페이지 ID (현재 미사용) |

---

## 개발 환경 `.env` 예시

```env
jira_base_url=https://yourcompany.atlassian.net
jira_email=your@email.com
jira_api_token=your-jira-api-token
gemini_api_key=your-gemini-api-key

db_user=postgres
db_password=postgres
db_host=db
db_name=auto_reports

LOGIN=false
JWT_SECRET=dev-secret-change-in-production

project_key=TACEA
schedule_cron=0 23 * * 5
```

---

## Docker Compose 구성

`docker-compose.yml`은 다음 3개 서비스로 구성됩니다.

| 서비스 | 설명 |
|--------|------|
| `db` | PostgreSQL 15 |
| `backend` | FastAPI (uvicorn) — 포트 8000 |
| `frontend` | React 프론트엔드 (nginx) — 포트 80 |

백엔드는 `db` 서비스가 healthy 상태가 된 후 `alembic upgrade head`를 수행하고 uvicorn을 시작합니다.
