# TAC Auto Reports v1.0

Jira Cloud API 와 Google Gemini AI 를 연동하여 TAC(Technical Assistance Center) 팀의 주간 보고서를 자동으로 수집·분석·시각화하는 풀스택 웹 애플리케이션입니다.

## 주요 기능

- Jira Cloud REST API v3 를 통한 이슈 데이터 자동 수집
- Google Gemini AI 기반 자연어 보고서 요약 생성
- 14개 위젯으로 구성된 대시보드 (SLA, 트렌드, 월별 통계 등)
- APScheduler 기반 주기적 자동 생성 (기본: 매주 금요일 23:00)
- 보고서 이력 조회 및 파일 스토리지 관리
- JWT 기반 옵셔널 로그인 인증
- Docker Compose 원클릭 배포

## 기술 스택

| 구분 | 기술 |
|------|------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x (asyncio), Alembic, APScheduler |
| Database | PostgreSQL 16 |
| AI | Google Gemini (google-genai) |
| Frontend | React 18, TypeScript, Vite, TanStack Query v5, Zustand, Recharts, Tailwind CSS |
| Infra | Docker, Docker Compose, Nginx (프론트 서빙) |

## 빠른 시작

### 1. 저장소 클론

```bash
git clone https://github.com/creatorjun/Auto_Reports.git
cd Auto_Reports
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일에서 아래 항목을 반드시 입력합니다.

```env
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token

GEMINI_API_KEY=your-gemini-api-key   # AI 요약 비활성화 시 AI_ENABLED=false

DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=auto_reports
```

### 3. 실행

```bash
docker compose up -d
```

```bash
git pull; docker compose down; docker compose build --no-cache; docker compose up -d
```

```bash
docker compose up -d --build; docker logs tac_backend
```

브라우저에서 `http://localhost` (기본 포트 80) 로 접속합니다.

> DB 마이그레이션은 백엔드 컨테이너 기동 시 `alembic upgrade head` 가 자동 실행됩니다.

## 환경 변수 전체 목록

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `JIRA_BASE_URL` | Jira Cloud 도메인 | _(필수)_ |
| `JIRA_EMAIL` | Jira 계정 이메일 | _(필수)_ |
| `JIRA_API_TOKEN` | Jira API 토큰 | _(필수)_ |
| `AI_ENABLED` | Gemini AI 요약 활성화 | `true` |
| `GEMINI_API_KEY` | Gemini API 키 | _(AI 활성화 시 필수)_ |
| `DB_USER` | PostgreSQL 사용자 | `postgres` |
| `DB_PASSWORD` | PostgreSQL 비밀번호 | `postgres` |
| `DB_HOST` | PostgreSQL 호스트 | `db` |
| `DB_NAME` | 데이터베이스 이름 | `auto_reports` |
| `SCHEDULE_CRON` | 자동 생성 cron 표현식 | `0 23 * * 5` |
| `TZ` | 타임존 | `Asia/Seoul` |
| `CORS_ORIGINS` | 허용 CORS Origin JSON 배열 | `["http://localhost:3000"]` |
| `APP_PORT` | 외부 노출 포트 | `80` |
| `DOMAIN` | SSL 적용 도메인 | _(선택)_ |
| `SSL_EMAIL` | Let's Encrypt 이메일 | _(선택)_ |
| `LOGIN` | 로그인 기능 활성화 | `true` |
| `ADMIN` | 관리자 계정명 | `ADMIN` |
| `ADMIN_PASSWORD` | 관리자 비밀번호 | _(필수)_ |
| `JWT_SECRET` | JWT 서명 비밀키 | _(필수)_ |
| `CONFLUENCE_SPACE_KEY` | Confluence 스페이스 키 | _(선택)_ |
| `CONFLUENCE_PARENT_PAGE_ID` | Confluence 상위 페이지 ID | _(선택)_ |

## 문서

- [아키텍처](docs/architecture.md)
- [API 명세](docs/api.md)
- [위젯 명세](docs/widgets.md)
- [배포 가이드](docs/deployment.md)

## 라이선스

MIT
