# 운영·배포 가이드

문서 기준: 2026-10-14 · 구현 커밋 `e280b75`.

2026-10-14 소스 기준입니다. 아래 Bash 명령은 Docker Compose가 설치된 Linux 서버의 저장소 루트에서 실행합니다. 서버 주소·비밀번호·토큰은 문서에 저장하지 않습니다.

## 구성과 최초 실행

서비스 이름은 `db`, `backend`, `frontend`, 기본 컨테이너 이름은 `tac_db`, `tac_backend`, `tac_frontend`입니다. `docker compose logs`·`exec`에는 서비스 이름을 사용합니다.

루트 `.env.example`을 `.env`로 복사한 뒤 [환경 설정](04_environment_and_config.md)에 맞게 실제 값을 입력합니다. Jira API 계정에는 대상 프로젝트·SLA·상태 이력·Assets 조회에 필요한 권한이 있어야 합니다. 보고서 AI를 쓰지 않으면 `AI_ENABLED=false`, 보안 뉴스 번역을 쓰지 않으면 `SECURITY_NEWS_TRANSLATION_ENABLED=false`로 설정합니다.

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 backend
curl -f http://localhost/api/health
docker compose exec backend alembic current
docker compose exec backend alembic heads
```

`APP_PORT`를 바꾸면 health URL의 포트도 바꿉니다. Compose의 backend는 호스트 8000 포트를 공개하지 않으며 nginx의 `/api/`로 접근합니다. health 성공은 프로세스 응답 확인이며 Jira 인증·보고서 생성 성공까지 의미하지 않습니다.

기본 nginx는 HTTP 80으로 동작합니다. 저장소의 `docker-compose.https.yml`과 `frontend/nginx.https.conf`를 선택하면 HTTP 요청을 HTTPS로 전환하고 443 포트에서 TLS를 제공합니다. `DOMAIN`, `SSL_EMAIL` 값만 지정해도 인증서가 자동 발급되는 구성은 아닙니다.

## HTTPS 적용

서버에서 사용할 인증서와 개인 키를 `.certs/fullchain.pem`, `.certs/privkey.pem`에 준비합니다. 접속 주소가 IP라면 인증서의 Subject Alternative Name에 그 IP가 있어야 합니다. 자체 서명 인증서는 클라이언트의 신뢰 저장소에 해당 인증서를 등록해야 브라우저 경고 없이 사용할 수 있습니다. 공개 CA 인증서와 동일한 신뢰 상태로 자동 적용되는 것은 아닙니다. 개인 키는 서버에서만 보관하고 파일 권한을 `600`으로 제한합니다.

`.env`에 `COOKIE_SECURE=true`를 지정하고, Jira OAuth 콜백도 실제 HTTPS 주소의 `/api/v1/auth/jira/callback`으로 등록합니다. `TLS_CERTS_DIR`을 지정하면 기본 `.certs` 대신 해당 서버 디렉터리를 읽기 전용으로 마운트합니다.

Uvicorn이 nginx에서 전달하는 HTTPS 프로토콜을 인식하도록 `FORWARDED_ALLOW_IPS`에 실제 Compose 네트워크의 CIDR 또는 고정 nginx 주소를 지정합니다. 임의의 외부 요청을 신뢰하는 `*`는 사용하지 않습니다. 네트워크 이름과 CIDR은 다음처럼 확인합니다.

```bash
docker inspect tac_frontend --format '{{range $name, $config := .NetworkSettings.Networks}}{{println $name}}{{end}}'
docker network inspect NETWORK_NAME --format '{{range .IPAM.Config}}{{println .Subnet}}{{end}}'
```

확인한 신뢰 범위를 `.env`에 기록한 뒤 다음을 실행합니다. `.certs/`와 서버별 `docker-compose.override.yml`은 Git에서 제외됩니다. 기존 override가 있으면 먼저 보존하고 병합합니다.

```bash
cp docker-compose.https.yml docker-compose.override.yml
docker compose config --quiet
docker compose up -d --build --no-deps backend frontend
docker compose exec frontend nginx -t
curl --cacert .certs/fullchain.pem https://SERVER_ADDRESS/api/health
```

이후 기본 `docker compose` 명령은 override를 자동 적용합니다. HTTP health 확인은 308 리다이렉트 응답이므로 적용 후에는 HTTPS URL과 신뢰할 인증서를 사용합니다. 인증서 갱신 시 같은 경로의 인증서·키를 교체하고 `nginx -t` 확인 후 `docker compose exec frontend nginx -s reload`를 실행합니다. 만료일도 함께 점검합니다. 인증서·개인 키는 Git에 추가하지 않습니다.

## 갱신 종류

| 대상 | 트리거 | 동작 |
|---|---|---|
| 일반 보고서 생성 | UI 또는 `SCHEDULE_CRON` | 새 일반 보고서와 job 저장 |
| 일반·연간 보고서 갱신 | `REFRESH_REPORT_ENABLED`, 기본 5분 | 최신 일반 및 현재 연도 전용 보고서가 존재할 때 같은 ID의 위젯 갱신 |
| SLA 위반 | UI의 기간·기준일 생성 | 성공할 때 새 저장본, 정기 자동 생성 없음 |
| 재배포 현황 | 매일 08:00 KST, 앱 시작, 지금 갱신 | 최근 도래한 08시 이후 저장본이 없으면 수집, 당일 저장본 대체 |
| 전체 이슈 | 목록 요청 | 30초 최소 간격 증분 수집, 1시간 경과 시 전체 재동기화 |
| 보안 뉴스 | 매일 08:00 KST 또는 최신 자료 확인 | 저장 스냅샷 조회, 방문·앱 시작 시 수집 없음, 수동 최소 60초, NVD는 최소 2시간 |

`SCHEDULE_CRON`은 다섯 필드를 APScheduler `CronTrigger`에 전달합니다. 숫자 요일은 월요일=0, 일요일=6입니다. 현재 기본값 `0 23 * * 5`는 **토요일 23시**, 금요일은 `0 23 * * fri`입니다. 재배포와 보안 뉴스의 08시 KST는 이 cron 및 `TZ`와 독립적입니다. 일반 보고서 갱신은 AI 분석·생성 시각을 새로 만드는 동작이 아닙니다.

현재 Compose는 단일 backend 프로세스를 실행합니다. 일반 보고서 job의 중복 예약은 프로세스 내부에서 제어하므로 여러 backend worker/replica 운영 시 스케줄이 중복되지 않도록 별도 설계가 필요합니다. 재배포 수집은 DB advisory lock도 사용합니다. 중지된 기간의 일별 재배포 이력을 모두 소급 생성하지는 않습니다.

SLA 일일 메일은 기존 할 일 알림 수신자에게 매일 09:00 KST 발송합니다. 시작 즉시 실행하거나 중단 기간의 메일을 소급 발송하지 않습니다. `NOTIFY_SLA_DIGEST_ENABLED=false`로 이 작업만 끌 수 있습니다. 단일 프로세스의 같은 날짜 중복 발송을 방지하며 여러 worker/replica 간 발송 상태를 공유하지 않습니다. Jira 수집 또는 SMTP 실패는 작업 오류로 남고 성공으로 기록되지 않습니다. 설정과 발송 없는 검증 명령은 [SLA 일일 알림](12_sla_digest.md)을 참고하세요.

## 백업과 마이그레이션

DB, 파일 보관함과 감사로그는 별도 데이터입니다. 다음 named volume을 함께 관리합니다. 실제 이름 앞에는 Compose project 이름이 붙습니다.

| 논리 볼륨 | 내용 |
|---|---|
| `db_data` | PostgreSQL 보고서·job·사이트·접속 정보 |
| `storage_data` | 업로드 파일 |
| `audit_logs` | 감사로그와 회전 파일 |
| `reports_data` | 보고서 파일용 `/app/reports` 마운트 |

Linux에서 DB 백업 예시:

```bash
mkdir -p backups
backup_file="backups/auto_reports-$(date +%Y%m%d-%H%M%S).dump"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup_file"
test -s "$backup_file"
docker compose exec -T db pg_restore --list < "$backup_file" > /dev/null
```

백업 파일에는 사이트 접속 정보 등 민감 데이터가 포함될 수 있으므로 접근을 제한하고 Git에 추가하지 않습니다. 파일/감사로그 볼륨은 별도 스냅샷 또는 백업 도구로 보관하고 DB와 파일 사이의 일관성이 필요하면 쓰기 작업을 중지한 시점에 백업합니다. `.env`와 `CREDENTIAL_ENCRYPTION_KEY`는 데이터와 함께 복구 가능한 보안 저장소에 별도로 보관합니다. 암호화 키 없이 ciphertext를 복구해도 원문을 읽을 수 없습니다.

백엔드 entrypoint는 `alembic upgrade head` 성공 후에만 서버를 실행합니다. 현재 head는 `0020`이며 전체 이슈의 마지막 저장본 테이블을 추가합니다. 마이그레이션 세부 사항은 [데이터 모델](03_data_model.md)에 있습니다. `0016`은 C-Level 테이블과 데이터를 삭제하며 downgrade는 빈 테이블만 복원합니다. 마이그레이션 전 백업이 없으면 삭제된 데이터를 되돌릴 수 없습니다.

직원 Jira 로그인 공유 전 개인정보 보고 연결·과거 이력 보완 절차는 [Jira 로그인](11_jira_login.md)을 따릅니다. `docker compose exec backend python scripts/backfill_personal_data.py`는 이름이나 집계를 변경하지 않는 조회 전용 진단입니다. DB 백업 후 `--apply`를 붙이면 Jira 이력으로 확인된 계정 ID만 저장합니다. `/admin/jira-privacy`에서 미연결 항목과 보고 실패를 확인합니다. 보완 작업 중에는 해당 보고서 저장이 잠시 대기할 수 있습니다.

`docker compose down -v`는 운영 데이터 볼륨 삭제 명령이므로 일반 배포·재시작 절차에 사용하지 않습니다. 백업 복구는 먼저 별도 DB에서 `pg_restore`로 검증하고, 서비스 중지와 대상 DB·볼륨을 확정한 다음 수행합니다. 코드만 이전 커밋으로 돌려도 DB 변경과 삭제 데이터는 되돌아가지 않습니다.

## 변경 배포

현재 커밋과 작업 트리를 확인하고 위 백업을 완료합니다.

```bash
git status --short
git rev-parse HEAD
git pull --ff-only origin main
docker compose config --quiet
```

작업 트리에 변경이 있으면 먼저 변경 내용을 보존·정리합니다. frontend만 변경한 경우:

```bash
docker compose up -d --build --no-deps frontend
```

backend 코드·의존성·migration을 변경한 경우:

```bash
docker compose up -d --build --no-deps backend
docker compose ps
docker compose logs --tail=100 backend
curl -f http://localhost/api/health
docker compose exec backend alembic current
docker compose exec frontend nginx -s reload
```

backend가 정상 시작된 뒤 nginx를 reload하여 재생성된 backend 주소를 다시 확인합니다. 양쪽을 변경했다면 backend 확인 후 frontend도 빌드·재생성합니다. DB 이미지나 Compose 자체 변경은 해당 서비스 변경 내용을 별도로 검토합니다. 일반 배포에는 전체 `down`이나 `--no-cache` 빌드가 필요하지 않습니다. 문서만 변경하면 Git 반영으로 충분하며 이미지 재빌드·재시작은 필요하지 않습니다.

## 검증과 점검

| 범위 | 명령 또는 확인 | 의미 |
|---|---|---|
| 문서 | 상대 링크·코드 경로 대조, `git diff --check` | 문서 참조와 패치 형식 |
| Backend | `python -m unittest discover -s tests -v`, `python -m compileall -q src tests` (backend에서) | 회귀 및 Python 구문 |
| Frontend | `pnpm install --frozen-lockfile`, `node --test tests/*.test.mjs`, `pnpm build` (frontend에서) | 회귀·TypeScript·배포 번들 |
| 컨테이너 | `docker compose ps`, backend 로그, health, `alembic current` | 앱 기동 및 DB revision |
| 실제 데이터 | 인증 후 저장본 조회·필요한 범위 생성·이력 재조회 | Jira 권한, 수집·저장과 화면 동작 |

SLA 생성 검증에서는 생성 응답의 ID·고유 티켓 수·각 SLA 수를 히스토리 및 ID 조회 결과와 대조합니다. 화면 기본 필터로 제외된 수와 저장 원본 수는 다를 수 있습니다. 재배포는 생성일과 당일 저장본 대체를 확인합니다. GET 조회만으로 신규 수집·저장 성공을 확인했다고 판단하지 않습니다.

## 장애 확인

- 401/403: 로그인 모드, access/refresh token, 계정 권한을 확인합니다. 감사로그는 `SUPERADMIN` 전용이며 `LOGIN=false`로 공개되지 않습니다.
- 409: 같은 보고서 수집이 진행 중인지 확인합니다. 재배포는 다른 프로세스의 DB lock도 검사합니다.
- 502/수집 실패: backend 로그에서 Jira 인증·권한, 페이지 누락과 데이터 필드 문제를 확인합니다. SLA/재배포의 실패 응답을 정상 빈 보고서로 처리하지 않습니다.
- 일반 보고서 단계별 평균 일부 누락: `[w14-단계별시간]` 로그에서 해당 이슈의 잘못된 상태 이력을 확인합니다. 통신 오류와 티켓별 이력 검증 실패는 다른 처리 경로입니다.
- 전체 이슈가 비어 있음: `initialized`, `refreshing`, `error`, `synced_at`을 확인합니다. backend 재시작 시 `issue_management_snapshots`의 마지막 목록을 복원하고 백그라운드에서 갱신합니다. 저장본이 없는 최초 실행은 전체 수집이 필요합니다. 복원 실패는 `Issue snapshot restore failed`, 갱신·저장 실패는 `Issue synchronization failed` 로그로 확인합니다.
- 파일 변환 오류: LibreOffice 설치, 임시 디렉터리 권한과 서버 120초 제한을 확인합니다. 프런트엔드 변환 요청 제한은 150초입니다.
- 구버전 화면/asset 404: HTML은 no-store, 해시 assets는 장기 캐시입니다. 새로고침 후 버전과 frontend 이미지 반영 여부를 확인합니다.

`Makefile`의 `trigger`는 인증 헤더가 없으므로 `LOGIN=true` 환경의 검증 명령으로 쓰지 않습니다. UI 또는 토큰을 안전하게 주입한 API 클라이언트를 사용합니다.
