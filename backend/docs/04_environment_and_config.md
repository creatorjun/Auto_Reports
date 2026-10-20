# Environment and Configuration

문서 기준: 2026-10-16.

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
| `ISSUE_TYPES` | `["인시던트","개선","CVE","서비스 요청","H/W 장애 요청","승인된 서비스 요청","라이선스"]` | Jira 프로젝트 유형 목록 조회 실패 시 사용할 대시보드 토글 기본값 |
| `ACTIVE_STATUSES` | 사내 기본 목록 | 활성 상태 JSON list |
| `CLOSED_STATUSES` | 사내 기본 목록 | 종료 상태 JSON list |
| `SLA_THRESHOLD_DAYS` | `30` | 일반 대시보드의 지연 분류 기준. SLA 현황의 `breached=true` 판정을 대체하지 않음 |
| `SLA_INITIAL_RESPONSE_FIELD_ID` | `customfield_12152` | 최초 응답 field |
| `SLA_RESOLUTION_FIELD_ID` | `customfield_12151` | 해결 SLA field |
| `SLA_RESOLUTION_PAUSE_STATUSES` | `["결과 대기 중","자료 요청 중","보류 중"]` | 상태별 해결 SLA 시간 계산에서 제외할 상태. Jira 정지 조건 변경 시 함께 갱신하며 계산 합계는 Jira 원본 사용 시간으로 검증 |
| `JIRA_TAC_ASSIGNEE_FIELD_ID` | `customfield_10859` | 기존 담당자 표시·알림에서 우선 조회하는 호환 설정. 현재 Jira의 기본 ID는 파트너사 필드 |
| `JIRA_QA_ASSIGNEE_FIELD_ID` | `customfield_12222` | 기존 담당자 표시·알림에서 다음으로 조회하는 호환 설정. 현재 Jira의 기본 ID는 테스트 범위 필드 |
| `JIRA_RECENT_TAC_ASSIGNEE_FIELD_ID` | `customfield_12522` | 최근 이슈 현황의 별도 TAC 담당자 사용자 필드. 다른 담당자 값으로 대체하지 않으며, 이전 보고서의 미수집 값은 `-`로 표시 |
| `REPORT_RETENTION_WEEKS` | `52` | 일반 보고서의 실제 생성일 기준 보존 주수. 과거 집계 기간도 생성 후 보존하며, 연간 전용 보고서는 정리 대상에서 제외. 0이면 자동 정리 비활성 |

대시보드와 연간 보고서의 모든 위젯은 Jira 요청 유형 `라이선스`를 원천 JQL에서 제외합니다. 이 유형은 화면의 요청 유형 필터에도 표시되지 않습니다. 보고서 생성 시 Jira 프로젝트 메타데이터에서 현재 등록된 비하위 작업 유형을 조회하고, 라이선스를 제외한 연간·월별·SLA 유형별 분해값을 저장합니다. 상반기·하반기 선택 시 월별 집계는 각각 1~6월과 7~12월로 제한되고, 상세 데이터는 생성일 또는 해결일을 기준으로 같은 기간을 적용합니다. 메타데이터 조회가 실패하거나 빈 목록이면 `ISSUE_TYPES`를 사용합니다. 프로젝트 유형 목록 밖의 데이터는 `always_included` 집계 또는 원본 상세에 유지되지만, 라이선스는 예외로 항상 제외됩니다. 기존 연간 보고서는 저장된 유형별 분해값으로 라이선스를 즉시 차감해 표시합니다.

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
| `ADMIN` | `admin` | 일반 사용자 계정 이름 |
| `ADMIN_PASSWORD` | 빈 값 | 빈 값이면 로그인 불가 |
| `SUPERADMIN` | 빈 값 | 감사로그 조회 권한을 가진 관리자 계정 이름 |
| `SUPERADMIN_PASSWORD` | 빈 값 | 관리자 계정 암호. 미설정 시 관리자 권한 비활성 |
| `JWT_SECRET` | 개발용 placeholder | 강한 임의 값으로 변경. 개인정보 보고용 소유자 토큰 암호화에는 최소 32바이트 필요 |
| `JWT_ACCESS_EXPIRE_MINUTES` | `30` | access token 수명 |
| `JWT_REFRESH_EXPIRE_DAYS` | `7` | refresh token 수명 |
| `JIRA_LOGIN_ENABLED` | `false` | Jira OAuth 로그인 활성화. 기존 관리자 계정 유지 |
| `JIRA_OAUTH_CLIENT_ID` | 빈 값 | Atlassian OAuth 앱 Client ID |
| `JIRA_OAUTH_CLIENT_SECRET` | 빈 값 | 서버에서만 사용하는 앱 Secret |
| `JIRA_OAUTH_REDIRECT_URI` | 빈 값 | 등록한 `/api/v1/auth/jira/callback` 절대 URL |
| `JIRA_PRIVACY_OWNER_ACCOUNT_ID` | 빈 값 | 개인정보 정기 보고를 승인할 실제 Atlassian 앱 소유자의 계정 ID |
| `COOKIE_SECURE` | `false` | HTTPS 운영에서는 true |
| `CREDENTIAL_ENCRYPTION_KEY` | 빈 값 | 운영에서는 유효한 Fernet key 필수 |
| `CORS_ORIGINS` | `["*"]` | 운영 frontend origin으로 제한 |

일반 사용자와 관리자 credential 비교는 constant-time compare를 사용합니다. `ADMIN`과 `SUPERADMIN`은 서로 다른 이름으로 지정합니다. 같은 이름이면 관리자 권한을 부여하지 않습니다. `/auth/me`가 반환하는 `is_superadmin`과 API의 서버 권한 검사로 감사로그 접근을 제어하며, `LOGIN=false`에서도 감사로그는 공개하지 않습니다. 관리자 재로그인은 이전 관리자 세션을 무효화합니다. access credential 암호화 key를 바꾸면 기존 ciphertext를 복호화할 수 없으므로 별도 key rotation 절차가 필요합니다.

## AI, storage, schedule

| Variable | Default | 설명 |
|----------|---------|------|
| `GEMINI_API_KEY` | 빈 값 | Gemini API key |
| `AI_ENABLED` | `true` | false면 보고서 AI 분석 생략. 보안 뉴스 번역은 별도 설정 |
| `SECURITY_NEWS_TRANSLATION_ENABLED` | `true` | Gemini key가 있을 때 보안 뉴스 제목·요약 한국어 번역 |
| `SECURITY_NEWS_TRANSLATION_MODEL` | `gemini-3.5-flash-lite` | 뉴스 번역 모델. 모델 변경만으로 저장된 번역을 다시 요청하지 않음 |
| `SECURITY_NEWS_TRANSLATION_CACHE_PATH` | `reports/security-news-translations.sqlite3` | 영구 번역·호출 제한 저장소. Compose에서는 `/app/reports` 볼륨 |
| `SECURITY_NEWS_TRANSLATION_DAILY_REQUEST_LIMIT` | `60` | UTC 날짜별 최대 번역 요청 횟수, 재시작 후에도 유지 |
| `SECURITY_NEWS_TRANSLATION_BATCH_SIZE` | `10` | 한 요청에 묶는 최대 기사 수 |
| `SECURITY_NEWS_TRANSLATION_MIN_INTERVAL_SECONDS` | `10` | 번역 요청 사이 최소 간격 |
| `SECURITY_NEWS_TRANSLATION_MAX_ATTEMPTS` | `3` | 같은 원문에 대한 최대 번역 시도 횟수 |
| `STORAGE_DIR` | `/app/storage` | 파일 root |
| `AUDIT_LOG_DIR` | `logs` | 감사로그 저장·조회 경로. Compose에서는 `/app/logs`로 고정하고 named volume에 보관 |
| `SCHEDULE_CRON` | `0 23 * * 5` | APScheduler 숫자 요일 기준 토요일 23시. 금요일은 `0 23 * * fri` |
| `TZ` | `Asia/Seoul` | scheduler timezone |
| `REFRESH_REPORT_ENABLED` | `true` | 최신 일반 및 현재 연도 전용 보고서의 기존 ID 주기 갱신 |
| `REFRESH_REPORT_INTERVAL_MINUTES` | `5` | 갱신 주기 |

Settings 기본값과 `.env.example`은 구분합니다. 예제는 `LOGIN=true`, 별도의 `ISSUE_TYPES` 목록 등 일부 값을 명시적으로 덮어씁니다. `AI_ENABLED=true`라도 Gemini key가 비어 있으면 클라이언트를 초기화하지 않고 분석 결과를 null로 반환합니다. 현재 Gemini 분석은 일반·연간 보고서의 종합 분석이고 SLA별 Rovo/A2A 분석이 아닙니다.

APScheduler는 숫자 요일을 월요일=0으로 해석합니다. 재배포 현황의 매일 08시 KST 작업은 코드에 별도로 등록하며 `SCHEDULE_CRON`, `TZ`, `REFRESH_REPORT_ENABLED`와 독립적입니다. SLA 현황은 수동 생성만 제공합니다. 전체 이슈 동기화 간격과 재배포 시작일 2026-01-01은 환경 변수 설정이 아닙니다.

LibreOffice는 문서 PDF 변환에 사용하며 실행 파일이 없으면 변환 endpoint가 명시적 오류를 반환합니다.

각 변환 요청은 시스템 임시 디렉터리에 독립적인 LibreOffice 프로필과 PDF 출력 디렉터리를 생성합니다. 서버 계정은 임시 디렉터리에 쓰기 권한이 있어야 합니다. 변환 결과는 응답용으로 읽은 뒤 정리하며, 원본 폴더에 같은 이름의 PDF가 있어도 덮어쓰거나 삭제하지 않습니다. 120초 제한 초과 또는 요청 취소 시 실행한 변환 프로세스를 종료하고 임시 파일을 정리합니다.

## SMTP notification

| Variable | Default |
|----------|---------|
| `SMTP_HOST` | 빈 값 |
| `SMTP_PORT` | `587` |
| `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | 빈 값 |
| `SMTP_USE_TLS`, `SMTP_START_TLS` | `false` |
| `NOTIFY_TODO_ENABLED`, `NOTIFY_TAC_ENABLED` | `false` |
| `NOTIFY_TODO_TO`, `NOTIFY_TAC` | 빈 JSON list |
| `NOTIFY_SLA_DIGEST_ENABLED` | `true` |
| `NOTIFY_TAC_KEYWORD` | 사내 기본값 |

SMTP host와 각 enable·recipient 조건이 모두 충족된 알림만 구성됩니다.

`NOTIFY_SLA_DIGEST_ENABLED=true`이고 기존 할 일 알림의 SMTP·`NOTIFY_TODO_ENABLED`·`NOTIFY_TODO_TO` 조건이 충족되면 같은 수신자에게 매일 09:00 KST SLA 요약을 한 통 발송합니다. Jira 목표 시간 대비 잔여 시간이 0~30%인 진행 SLA를 대상으로 하며, 어느 SLA든 현재 또는 완료 주기에 위반 이력이 있는 티켓은 제외합니다. 별도 수신자 설정이나 보고서 갱신은 필요하지 않습니다. 대상이 없으면 발송하지 않습니다. 상세 기준과 발송 없는 미리보기는 [SLA 일일 알림](12_sla_digest.md)을 참고하세요.

## 실행 방식별 설정

| 항목 | 적용 범위 |
|---|---|
| `APP_PORT=80` | Compose frontend의 호스트 포트. Settings 항목이 아님 |
| `TZ`, `AUDIT_LOG_DIR` | 현재 Compose backend의 `environment`가 각각 `Asia/Seoul`, `/app/logs`로 명시하여 env_file 값보다 우선 |
| `STORAGE_DIR` | 변경 시 Compose의 storage volume mount도 같은 경로로 맞춰야 함 |
| `VITE_API_BASE_URL` | 프런트엔드 빌드/개발 시 API 주소. 기본 `/api/v1`, 이미 빌드된 nginx 컨테이너의 런타임 env로 바뀌지 않음 |
| `CONFLUENCE_SPACE_KEY`, `CONFLUENCE_PARENT_PAGE_ID` | Settings에는 있으나 현재 수집/게시 경로에서 사용하지 않음. 자동 Confluence 게시 기능 없음 |
| `DOMAIN`, `SSL_EMAIL` | 예제에 남은 값이며 현재 Compose에서 사용하지 않음. 자동 TLS 설정 기능 없음 |

목록 설정은 JSON 배열 형식입니다. `.env` 변경은 프로세스 재생성 때 반영되며 frontend 빌드 시 설정과 구분합니다. API host를 로컬에서 직접 실행할 때는 `DB_HOST` 등 Compose 내부 이름을 실제 접근 주소로 조정합니다.

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
SUPERADMIN=root
SUPERADMIN_PASSWORD=replace-with-admin-password
JWT_SECRET=replace-with-random-secret
COOKIE_SECURE=true
CREDENTIAL_ENCRYPTION_KEY=replace-with-fernet-key
CORS_ORIGINS=["https://workspace.company.example"]
```

## Docker Compose

`docker-compose.yml`은 PostgreSQL 16, FastAPI backend, nginx React frontend를 정의합니다. DB healthcheck 뒤 backend가 시작되고 backend healthcheck 뒤 frontend가 시작됩니다. `db_data`, `reports_data`, `storage_data`, `audit_logs` named volume을 사용합니다. 기존 컨테이너 내부 로그의 첫 이전 방법은 [감사로그 문서](07_audit_logs.md)를 참고하세요.
