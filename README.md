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

## 빠른 시작

```bash
# 1. 환경변수 설정
cp .env.example .env
vi .env   # JIRA_EMAIL, JIRA_API_TOKEN, GEMINI_API_KEY 필수 입력

# 2. 빌드 & 실행
make build
make up

# 3. DB 마이그레이션
make migrate

# 4. 대시보드 접속
open http://localhost

# 5. 즉시 보고서 생성 테스트
make trigger

# 6. 로그 확인
make logs
```

## API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| `GET`  | `/api/health` | 헬스체크 |
| `POST` | `/api/v1/trigger/` | 즉시 보고서 생성 |
| `GET`  | `/api/v1/reports/` | 보고서 목록 |
| `GET`  | `/api/v1/reports/latest` | 최신 보고서 |
| `GET`  | `/api/v1/reports/{id}` | 특정 보고서 |

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

## 주요 기능

- ⚡ **즉시 생성** — 헤더 버튼 클릭으로 회의 전 즉시 보고서 생성
- 🕐 **자동 스케줄** — 매주 금요일 23시 자동 생성 (크론 설정 변경 가능)
- 📊 **차트 5종** — SLA 도넛, 지연 사유 파이, 유형별 바, 해결시간 분포, 생성 vs 해결
- 🤖 **AI 분석** — Gemini 2.0 Flash 기반 총평 / 리스크 / 권고사항
- 🗂️ **히스토리** — 과거 보고서 목록 및 상세 조회
