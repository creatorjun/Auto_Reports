# 배포 가이드

> **Version 1.0** | 2026-07-09

## 사전 요구사항

- Docker 24.x 이상
- Docker Compose v2.x 이상
- Jira Cloud 접근 권한 및 API 토큰
- (선택) Google Gemini API 키

---

## 빠른 시작

```bash
# 1. 저장소 클론
git clone https://github.com/creatorjun/Auto_Reports.git
cd Auto_Reports

# 2. 환경 설정
cp .env.example .env
vim .env   # 필수 항목 입력

# 3. 빌드 및 실행
docker compose up -d --build

# 4. 수동 리포트 수집 (최초 데이터 적재)
curl -X POST http://localhost/api/trigger
```

---

## 환경 변수 설명

| 변수 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `JIRA_BASE_URL` | ✅ | — | Jira 인스턴스 URL (예: `https://xxx.atlassian.net`) |
| `JIRA_EMAIL` | ✅ | — | Jira 로그인 이메일 |
| `JIRA_API_TOKEN` | ✅ | — | Jira API 토큰 |
| `AI_ENABLED` | — | `true` | Gemini AI 요약 활성화 여부 |
| `GEMINI_API_KEY` | — | — | Gemini API 키 (`AI_ENABLED=true`일 때 필요) |
| `DB_USER` | — | `postgres` | PostgreSQL 유저 |
| `DB_PASSWORD` | — | `postgres` | PostgreSQL 비밀번호 |
| `DB_HOST` | — | `db` | PostgreSQL 호스트 (컨테이너명) |
| `DB_NAME` | — | `auto_reports` | DB 이름 |
| `SCHEDULE_CRON` | — | `0 23 * * 5` | 자동 수집 크론 표현식 (기본: 매주 금요일 23시) |
| `TZ` | — | `Asia/Seoul` | 타임존 |
| `CORS_ORIGINS` | — | — | 허용할 CORS 오리진 (JSON 배열 문자열) |
| `APP_PORT` | — | `80` | 외부 노출 포트 |
| `DOMAIN` | — | — | SSL 적용 시 도메인 |
| `SSL_EMAIL` | — | — | Let's Encrypt 이메일 |
| `CONFLUENCE_SPACE_KEY` | — | — | Confluence 연동 스페이스 키 (선택) |
| `CONFLUENCE_PARENT_PAGE_ID` | — | — | Confluence 상위 페이지 ID (선택) |

---

## 컨테이너 구성

| 컨테이너 | 이미지 | 역할 |
|---|---|---|
| `tac_db` | `postgres:16-alpine` | 데이터 영속성 (리포트 저장) |
| `tac_backend` | `./backend` (자체 빌드) | FastAPI 서버, APScheduler, Jira 수집 |
| `tac_frontend` | `./frontend` (자체 빌드) | React SPA + Nginx |

의존 순서: `tac_db` → `tac_backend` → `tac_frontend`

### 볼륨

| 볼륨 | 용도 |
|---|---|
| `db_data` | PostgreSQL 데이터 영속화 |
| `reports_data` | 생성된 리포트 파일 저장 |

---

## 자주 쓰는 명령어

```bash
# 로그 확인
docker compose logs -f backend

# 백엔드만 재시작
docker compose restart backend

# 전체 종료 및 볼륨 삭제 (데이터 초기화 시)
docker compose down -v

# 수동 리포트 수집
curl -X POST http://localhost/api/trigger

# 최신 리포트 확인
curl http://localhost/api/reports/latest | python3 -m json.tool
```

---

## SSL / HTTPS 적용 (선택)

`docker-compose.yml` 하단의 주석 블록을 해제하면 `nginx-proxy` + `acme-companion`으로
Let's Encrypt 인증서를 자동 발급·갱신합니다.

1. DNS A 레코드를 서버 IP로 등록
2. `.env`에 `DOMAIN`, `SSL_EMAIL` 입력
3. `docker-compose.yml` 주석 해제 후 재배포

```bash
docker compose down
docker compose up -d --build
```

---

## 스케줄러 기본 동작

`SCHEDULE_CRON=0 23 * * 5` (기본값) 기준:

- **매주 금요일 23:00 KST**에 자동으로 Jira 데이터를 수집하고 DB에 저장합니다.
- 크론 표현식은 표준 5자리 cron 형식을 따릅니다 (`분 시 일 월 요일`).
- 즉시 수집이 필요하면 `POST /api/trigger`를 호출합니다.
