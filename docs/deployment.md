# 배포 가이드 v1.0

## 사전 요구사항

- Docker Engine 24+
- Docker Compose v2.20+
- Jira Cloud 계정 및 API 토큰
- (선택) Google Gemini API 키
- (선택) SSL 도메인

---

## 1. 기본 배포 (HTTP)

```bash
git clone https://github.com/creatorjun/Auto_Reports.git
cd Auto_Reports
cp .env.example .env
# .env 편집 후
docker compose up -d
```

브라우저에서 `http://<서버IP>` 로 접속합니다.

포트를 변경하려면 `.env` 에서 `APP_PORT=8080` 처럼 수정합니다.

---

## 2. 도메인 + SSL 배포 (HTTPS)

`docker-compose.yml` 하단의 주석 블록을 참고합니다.  
nginx-proxy + acme-companion 을 사용하여 Let's Encrypt 인증서를 자동 발급합니다.

### 절차

1. DNS A 레코드를 서버 IP 로 등록하고 전파 확인
2. `.env` 에 도메인/이메일 설정
   ```env
   DOMAIN=reports.example.com
   SSL_EMAIL=admin@example.com
   APP_PORT=80
   ```
3. `docker-compose.yml` 에서 주석 해제
   - `nginx-proxy` 서비스 블록
   - `acme-companion` 서비스 블록
   - `frontend`, `backend` 의 환경변수 주석 블록
   - `volumes` 추가 항목 (certs, vhost, html, acme)
4. 기존 컨테이너 중지 후 재시작
   ```bash
   docker compose down
   docker compose up -d
   ```

---

## 3. 업데이트

```bash
git pull origin main
docker compose down
docker compose build
docker compose up -d
```

> DB 마이그레이션이 필요한 경우 백엔드 컨테이너 기동 시 자동 적용됩니다.

---

## 4. 수동 Alembic 마이그레이션

```bash
docker compose exec backend alembic upgrade head
```

---

## 5. 데이터 백업

PostgreSQL 데이터는 Docker Named Volume `db_data` 에 저장됩니다.

```bash
docker compose exec db pg_dump -U postgres auto_reports > backup_$(date +%F).sql
```

스토리지 파일은 `storage_data` 볼륨에 저장됩니다.

```bash
docker run --rm \
  -v auto_reports_storage_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/storage_$(date +%F).tar.gz -C /data .
```

---

## 6. 로그 확인

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

---

## 7. 컨테이너 구성

| 컨테이너 | 이미지 | 역할 |
|----------|--------|------|
| `tac_db` | postgres:16-alpine | PostgreSQL 데이터베이스 |
| `tac_backend` | 빌드 (./backend) | FastAPI 앱 (port 8000) |
| `tac_frontend` | 빌드 (./frontend) | Nginx + React SPA (port 80) |

백엔드는 DB 헬스체크 통과 후 기동되며, 프론트엔드는 백엔드 기동 후 시작됩니다.

---

## 8. 자동 보고서 생성 스케줄

기본값은 **매주 금요일 23:00 (Asia/Seoul)** 입니다.

`.env` 에서 cron 표현식으로 변경 가능합니다.

```env
SCHEDULE_CRON=0 9 * * 1   # 매주 월요일 오전 9시
```

자동 생성 시 집계 기간은 직전 월요일~일요일(7일)로 자동 계산됩니다.

---

## 9. 문제 해결

### 백엔드가 DB 연결에 실패하는 경우
- `.env` 의 `DB_HOST` 가 `db` (컨테이너명) 인지 확인
- `docker compose ps` 로 db 컨테이너 헬스체크 상태 확인

### Jira 데이터가 수집되지 않는 경우
- `JIRA_BASE_URL` 에서 trailing slash 제거 확인
- Jira API Token 의 권한(프로젝트 읽기) 확인
- `docker compose logs backend` 에서 HTTP 오류 코드 확인

### AI 요약이 생성되지 않는 경우
- `AI_ENABLED=true` 및 `GEMINI_API_KEY` 설정 확인
- Gemini API 할당량 초과 여부 확인
- `AI_ENABLED=false` 로 비활성화 후 정상 동작 확인
