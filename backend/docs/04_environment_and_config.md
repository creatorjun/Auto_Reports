# Environment and Configuration

`pydantic-settings`가 프로세스 환경과 실행 디렉터리의 `.env`를 읽습니다. 환경 변수 이름은 대소문자를 구분하지 않지만 배포 파일에서는 아래 대문자 표기를 권장합니다.

## Required

| Variable | 설명 |
|----------|------|
| `JIRA_BASE_URL` | Jira Cloud base URL |
| `JIRA_EMAIL` | Jira API 계정 이메일 |
| `JIRA_API_TOKEN` | Jira API token |

## Jira와 보고서

| Variable | Default | 설명 |
|----------|---------|------|
| `PROJECT_KEY` | `TACEA` | 집계 프로젝트 |
| `ISSUE_TYPES` | 사내 기본 목록 | 집계 이슈 유형 JSON list |
| `ACTIVE_STATUSES` | 사내 기본 목록 | 활성 상태 JSON list |
| `CLOSED_STATUSES` | 사내 기본 목록 | 종료 상태 JSON list |
| `SLA_THRESHOLD_DAYS` | `30` | SLA 지연 기준 |
| `SLA_INITIAL_RESPONSE_FIELD_ID` | `customfield_12152` | 최초 응답 field |
| `SLA_RESOLUTION_FIELD_ID` | `customfield_12151` | 해결 SLA field |
| `JIRA_TAC_ASSIGNEE_FIELD_ID` | `customfield_10859` | TAC 담당자 field |
| `JIRA_QA_ASSIGNEE_FIELD_ID` | `customfield_12222` | QA 담당자 field |
| `REPORT_RETENTION_WEEKS` | `52` | 0이면 자동 정리 비활성 |

## Database

| Variable | Default |
|----------|---------|
| `DB_USER` | `postgres` |
| `DB_PASSWORD` | `postgres` |
| `DB_HOST` | `db` |
| `DB_NAME` | `auto_reports` |

Application은 위 값으로 `postgresql+asyncpg://...` URL을 구성합니다.

## Authentication과 security

| Variable | Default | 운영 조건 |
|----------|---------|-----------|
| `LOGIN` | `false` | 인증 사용 시 true |
| `ADMIN` | `admin` | 관리자 이름 |
| `ADMIN_PASSWORD` | 빈 값 | 빈 값이면 로그인 불가 |
| `SUPERADMIN` | 빈 값 | 선택 계정 |
| `SUPERADMIN_PASSWORD` | 빈 값 | 선택 계정 암호 |
| `JWT_SECRET` | 개발용 placeholder | 강한 임의 값으로 변경 |
| `JWT_ACCESS_EXPIRE_MINUTES` | `30` | access token 수명 |
| `JWT_REFRESH_EXPIRE_DAYS` | `7` | refresh token 수명 |
| `COOKIE_SECURE` | `false` | HTTPS 운영에서는 true |
| `CREDENTIAL_ENCRYPTION_KEY` | 빈 값 | 운영에서는 유효한 Fernet key 필수 |
| `CORS_ORIGINS` | `["*"]` | 운영 frontend origin으로 제한 |

일반·슈퍼 관리자 credential 비교는 constant-time compare를 사용합니다. access credential 암호화 key를 바꾸면 기존 ciphertext를 복호화할 수 없으므로 별도 key rotation 절차가 필요합니다.

## AI, storage, schedule

| Variable | Default | 설명 |
|----------|---------|------|
| `GEMINI_API_KEY` | 빈 값 | Gemini API key |
| `AI_ENABLED` | `true` | false면 AI 분석 생략 |
| `STORAGE_DIR` | `/app/storage` | 파일 root |
| `SCHEDULE_CRON` | `0 23 * * 5` | 금요일 23시 |
| `TZ` | `Asia/Seoul` | scheduler timezone |
| `REFRESH_REPORT_ENABLED` | `true` | 최신 보고서 주기 갱신 |
| `REFRESH_REPORT_INTERVAL_MINUTES` | `5` | 갱신 주기 |

LibreOffice는 문서 PDF 변환에 사용하며 실행 파일이 없으면 변환 endpoint가 명시적 오류를 반환합니다.

## SMTP notification

| Variable | Default |
|----------|---------|
| `SMTP_HOST` | 빈 값 |
| `SMTP_PORT` | `587` |
| `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | 빈 값 |
| `SMTP_USE_TLS`, `SMTP_START_TLS` | `false` |
| `NOTIFY_TODO_ENABLED`, `NOTIFY_TAC_ENABLED` | `false` |
| `NOTIFY_TODO_TO`, `NOTIFY_TAC` | 빈 JSON list |
| `NOTIFY_TAC_KEYWORD` | 사내 기본값 |

SMTP host와 각 enable·recipient 조건이 모두 충족된 알림만 구성됩니다.

## Example

```env
JIRA_BASE_URL=https://company.atlassian.net
JIRA_EMAIL=service-account@company.example
JIRA_API_TOKEN=replace-me
AI_ENABLED=false
DB_USER=postgres
DB_PASSWORD=replace-me
DB_HOST=db
DB_NAME=auto_reports
LOGIN=true
ADMIN=admin
ADMIN_PASSWORD=replace-me
JWT_SECRET=replace-with-random-secret
COOKIE_SECURE=true
CREDENTIAL_ENCRYPTION_KEY=replace-with-fernet-key
CORS_ORIGINS=["https://workspace.company.example"]
```

## Docker Compose

`docker-compose.yml`은 PostgreSQL 16, FastAPI backend, nginx React frontend를 정의합니다. DB healthcheck 뒤 backend가 시작되고 backend healthcheck 뒤 frontend가 시작됩니다. `db_data`, `reports_data`, `storage_data` named volume을 사용합니다.
