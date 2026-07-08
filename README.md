# TAC Auto Reports

> Jira 데이터 자동 수집 → AI 분석 → 웹 대시보드 시각화

## 아키텍처

```
┌────────────────────────────────────────────────┐
│                Docker Compose                   │
│                                                 │
│  ┌──────────┐  ┌────────────┐  ┌────────────┐  │
│  │  Nginx   │  │  FastAPI   │  │ PostgreSQL │  │
│  │  :80     │  │  :8000     │  │  :5432     │  │
│  │ (React)  │  │            │  │            │  │
│  └──────────┘  └────────────┘  └────────────┘  │
└────────────────────────────────────────────────┘
         │               │
      브라우저        Jira API
                     Gemini API
```

## 클린 아키텍처 레이어

```
Presentation  ──▶  Application  ──▶  Domain
Infrastructure              ──▶  Domain
```

- **Domain** — 순수 엔티티/VO/인터페이스, 외부 의존 없음
- **Application** — 유스케이스, 도메인 인터페이스만 의존
- **Infrastructure** — DB/Jira/Gemini 구현체, Container에서 조립
- **Presentation** — FastAPI 라우터, Pydantic 스키마

---

## 프로젝트 구조

```
Auto_Reports/
├── .env.example
├── docker-compose.yml
├── Makefile
├── REFACTORING.md
├── backend/
│   ├── Dockerfile
│   ├── alembic/
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── scripts/                        ← 진단/유틸 스크립트
│   │   ├── get_data.py                 ← Jira SLA 필드 탐색
│   │   └── test_sla_debug.py           ← SLA 디버그 진단
│   └── src/
│       ├── main.py
│       ├── config/
│       │   └── settings.py
│       ├── domain/
│       │   ├── entities/               ← Report, WidgetResult, widget_data
│       │   ├── value_objects/          ← AiAnalysis, WidgetId, DateRange
│       │   ├── ports/                  ← JiraPort, AiPort (ABC)
│       │   └── repositories/          ← ReportRepository (ABC)
│       ├── application/
│       │   ├── use_cases/              ← GenerateReportUseCase, GetReportUseCase
│       │   ├── services/               ← AiAnalyzer, ReportAssembler, QueryBuilder
│       │   ├── widgets/                ← 위젯별 독립 Collector 클래스
│       │   └── scheduler/             ← APScheduler 설정
│       ├── infrastructure/
│       │   ├── container.py            ← 객체 조립 (DI)
│       │   ├── job_runner.py           ← 비동기 실행 & 상태 추적
│       │   ├── external/               ← JiraClient, GeminiClient
│       │   └── persistence/            ← SQLAlchemy ORM, ReportRepositoryImpl
│       └── presentation/
│           ├── api/v1/                 ← reports.py, trigger.py
│           └── schemas/               ← Pydantic 스키마
└── frontend/
    └── src/
```

---

## 배포 가이드

### 사전 요구사항 (macOS)

macOS에서 빌드하려면 [Homebrew](https://brew.sh)와 Docker Desktop이 필요합니다.

```bash
# Homebrew 설치 (미설치 시)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Docker Desktop 설치
brew install --cask docker
```

> Docker Desktop 앱을 실행하여 Docker 엔진이 구동 중인지 확인하세요.

---

### 1. 클론

**Linux / macOS**
```bash
git clone https://github.com/creatorjun/Auto_Reports.git && cd Auto_Reports
```

**Windows CMD**
```cmd
git clone https://github.com/creatorjun/Auto_Reports.git && cd Auto_Reports
```

---

### 2. 환경변수 설정

**Linux / macOS**
```bash
cp .env.example .env && vi .env
```

**Windows CMD**
```cmd
copy .env.example .env && notepad .env
```

> 필수 입력: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `GEMINI_API_KEY`

---

### 3. 빌드 & 실행

**Linux / macOS**
```bash
docker compose up -d --build
```

**Windows CMD**
```cmd
docker compose up -d --build
```

> macOS Apple Silicon(M1/M2/M3/M4)의 경우 Docker Desktop → Settings → General에서
> **"Use Rosetta for x86/amd64 emulation"** 옵션을 활성화하면 빌드 안정성이 향상됩니다.

> **DB 마이그레이션은 서버 시작 시 자동으로 실행됩니다.** 별도 명령이 필요하지 않습니다.

---

### 4. 접속 확인

```
http://localhost
```

---

## Makefile 단축 명령어

`make` 명령으로 자주 쓰는 작업을 간편하게 실행할 수 있습니다.

| 명령 | 동작 |
|------|------|
| `make up` | 컨테이너 시작 (`docker compose up -d`) |
| `make build` | 캐시 없이 전체 재빌드 |
| `make down` | 컨테이너 종료 |
| `make restart` | 백엔드 컨테이너만 재시작 |
| `make logs` | 전체 실시간 로그 |
| `make ps` | 컨테이너 상태 확인 |
| `make migrate` | DB 마이그레이션 수동 실행 |
| `make trigger` | 즉시 보고서 생성 (JSON 출력) |

---

## 운영 명령어

### 로그 확인

| 대상 | 명령어 |
|------|--------|
| 전체 실시간 | `docker compose logs -f` |
| 백엔드만 | `docker compose logs -f backend` |
| 프론트엔드만 | `docker compose logs -f frontend` |
| DB만 | `docker compose logs -f db` |
| 최근 100줄 | `docker compose logs --tail=100 backend` |

### 로그 검색

**Linux / macOS**
```bash
docker compose logs backend | grep "ERROR"
docker compose logs backend | grep "2026-07"
```

**Windows CMD**
```cmd
docker compose logs backend | findstr "ERROR"
docker compose logs backend | findstr "2026-07"
```

---

### 한 줄 리빌드 (풀 → 재빌드 → 재시작)

**Linux / macOS**
```bash
docker compose down && git pull && docker compose build --no-cache && docker compose up -d
```

**Windows CMD**
```bash
docker compose down && git pull && docker compose build --no-cache && docker compose up -d
```

---

### 컨테이너 상태 확인

```bash
docker compose ps
```

### 즉시 보고서 생성

```bash
curl -s -X POST http://localhost/api/v1/trigger/ | python3 -m json.tool
```

Job ID 반환 후 상태 폴링:

```bash
curl http://localhost/api/v1/trigger/{job_id}/status
```

---

## 진단 스크립트

`backend/scripts/` 디렉토리에 운영 진단용 스크립트가 있습니다.

### Jira SLA 필드 탐색

Jira 인스턴스의 SLA customfield ID를 자동으로 탐지하고 `DataStructure.md`로 저장합니다.

```bash
# .env 설정 후 로컬에서 실행
cd backend
python scripts/get_data.py

# 전체 customfield JSON 덤프 포함
python scripts/get_data.py --dump-all
```

### SLA 디버그 진단

Docker 컨테이너 내부에서 SLA 필드 매칭 및 월별 집계를 실시간 진단합니다.

```bash
docker compose exec backend python scripts/test_sla_debug.py
# 로그 파일: /tmp/sla_debug.log
```

---

## API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| `GET`    | `/api/health` | 헬스체크 |
| `POST`   | `/api/v1/trigger/` | 즉시 보고서 생성 (job_id 반환) |
| `GET`    | `/api/v1/trigger/{job_id}/status` | 생성 작업 상태 조회 |
| `GET`    | `/api/v1/reports/` | 보고서 목록 (`?limit=20&offset=0`) |
| `GET`    | `/api/v1/reports/latest` | 최신 보고서 |
| `GET`    | `/api/v1/reports/{id}` | 특정 보고서 상세 |
| `DELETE` | `/api/v1/reports/{id}` | 보고서 삭제 |

---

## 환경변수

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `JIRA_BASE_URL` | ✅ | — | Jira 인스턴스 URL (예: `https://your-domain.atlassian.net`) |
| `JIRA_EMAIL` | ✅ | — | Jira 계정 이메일 |
| `JIRA_API_TOKEN` | ✅ | — | [API 토큰 발급](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `GEMINI_API_KEY` | ✅ | — | [Gemini API 키](https://aistudio.google.com/app/apikey) |
| `AI_ENABLED` | | `true` | AI 분석 활성화 여부 |
| `DB_USER` | | `postgres` | PostgreSQL 사용자 |
| `DB_PASSWORD` | | `postgres` | PostgreSQL 비밀번호 |
| `DB_HOST` | | `db` | PostgreSQL 호스트 |
| `DB_NAME` | | `auto_reports` | DB 이름 |
| `SCHEDULE_CRON` | | `0 23 * * 5` | 자동 생성 크론 (기본: 금요일 23시) |
| `TZ` | | `Asia/Seoul` | 타임존 |
| `CORS_ORIGINS` | | `["*"]` | 허용 CORS 오리진 |
| `APP_PORT` | | `80` | Nginx 외부 포트 |
| `SLA_INITIAL_RESPONSE_FIELD_ID` | | `customfield_12152` | W15 초최 응답 SLA 필드 ID |
| `SLA_RESOLUTION_FIELD_ID` | | `customfield_12151` | W16 해결시간 SLA 필드 ID |
| `DOMAIN` | | — | DNS 등록 후 SSL 전환 시 입력 |
| `SSL_EMAIL` | | — | Let's Encrypt 인증서 발급 이메일 |
| `CONFLUENCE_SPACE_KEY` | | — | Confluence 연동 스페이스 키 (선택) |
| `CONFLUENCE_PARENT_PAGE_ID` | | — | Confluence 상위 페이지 ID (선택) |

---

## 주요 기능

- ⚡ **즉시 생성** — 헤더 버튼 클릭으로 회의 전 즉시 보고서 생성
- 🕐 **자동 스케줄** — 매주 금요일 23시 자동 생성 (크론 설정 변경 가능)
- 📊 **차트 5종** — SLA 도넛, 지연 사유 파이, 유형별 바, 해결시간 분포, 생성 vs 해결
- 🤖 **AI 분석** — Gemini 2.0 Flash 기반 총평 / 리스크 / 권고사항
- 🗂️ **히스토리** — 과거 보고서 목록 및 상세 조회
