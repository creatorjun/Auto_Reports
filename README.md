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

> 필수 입력: `JIRA_EMAIL`, `JIRA_API_TOKEN`, `GEMINI_API_KEY`

---

### 3. 빌드 & 실행

**Linux / macOS**
```bash
docker compose up -d --build
```

**Windows CMD**
```cmd
docker-compose up -d --build
```

> macOS Apple Silicon(M1/M2/M3/M4)의 경우 Docker Desktop → Settings → General에서
> **"Use Rosetta for x86/amd64 emulation"** 옵션을 활성화하면 빌드 안정성이 향상됩니다.

---

### 4. DB 마이그레이션

**Linux / macOS**
```bash
docker compose exec backend alembic upgrade head
```

**Windows CMD**
```cmd
docker-compose exec backend alembic upgrade head
```

---

### 5. 접속 확인

```
http://localhost
```

---

## 운영 명령어

### 로그 확인

| 대상 | Linux / macOS / Windows CMD |
|------|---------------------
| 전체 실시간 | `docker-compose logs -f` |
| 백엔드만 | `docker-compose logs -f backend` |
| 프론트엔드만 | `docker-compose logs -f frontend` |
| DB만 | `docker-compose logs -f db` |
| 최근 100줄 | `docker-compose logs --tail=100 backend` |

### 로그 검색

**Linux / macOS**
```bash
docker-compose logs backend | grep "ERROR"
docker-compose logs backend | grep "2026-07"
```

**Windows CMD**
```cmd
docker-compose logs backend | findstr "ERROR"
docker-compose logs backend | findstr "2026-07"
```

---

### 한 줄 리빌드 (다운 → 풀 → 재시작)

**Linux / macOS**
```bash
git pull && docker compose build --no-cache && docker compose up -d
```

**Windows CMD**
```cmd
docker-compose down && git pull && docker-compose up -d --build
```

---

### 컨테이너 상태 확인

**Linux / macOS / Windows CMD**
```bash
docker-compose ps
```

### 즉시 보고서 생성

**Linux / macOS**
```bash
curl -X POST http://localhost/api/v1/trigger/
```

**Windows CMD**
```cmd
curl -X POST http://localhost/api/v1/trigger/
```

---

## API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| `GET`  | `/api/health` | 헬스체크 |
| `POST` | `/api/v1/trigger/` | 즉시 보고서 생성 |
| `GET`  | `/api/v1/reports/` | 보고서 목록 |
| `GET`  | `/api/v1/reports/latest` | 최신 보고서 |
| `GET`  | `/api/v1/reports/{id}` | 특정 보고서 |

---

## 환경변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `JIRA_EMAIL` | ✅ | Jira 계정 이메일 |
| `JIRA_API_TOKEN` | ✅ | [API 토큰 발급](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `GEMINI_API_KEY` | ✅ | [Gemini API 키](https://aistudio.google.com/app/apikey) |
| `DB_USER` | | 기본값: `postgres` |
| `DB_PASSWORD` | | 기본값: `postgres` |
| `SCHEDULE_CRON` | | 기본값: `0 23 * * 5` (금요일 23시) |
| `TZ` | | 기본값: `Asia/Seoul` |
| `APP_PORT` | | 기본값: `80` |
| `DOMAIN` | | DNS 등록 후 SSL 전환 시 입력 |
| `SSL_EMAIL` | | DNS 등록 후 SSL 전환 시 입력 |

---

## 주요 기능

- ⚡ **즉시 생성** — 헤더 버튼 클릭으로 회의 전 즉시 보고서 생성
- 🕐 **자동 스케줄** — 매주 금요일 23시 자동 생성 (크론 설정 변경 가능)
- 📊 **차트 5종** — SLA 도넛, 지연 사유 파이, 유형별 바, 해결시간 분포, 생성 vs 해결
- 🤖 **AI 분석** — Gemini 2.0 Flash 기반 총평 / 리스크 / 권고사항
- 🗂️ **히스토리** — 과거 보고서 목록 및 상세 조회
