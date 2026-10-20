# SLA 일일 알림

2026-10-20 구현 기준. 기존 할 일 알림의 수신자에게 매일 한국시간 09:00에 SLA 위반이 임박한 티켓을 단계별로 묶어 한 통의 이메일로 보냅니다.

## 대상과 시간 기준

- 설정된 Jira 프로젝트의 미완료 티켓 전체를 조회합니다. 보고서 기간이나 생성일로 제한하지 않습니다.
- Jira에 등록된 SLA 필드를 매 실행 시 조회하고 각 진행 주기의 실제 목표·잔여 시간을 사용합니다. 아래 목표 시간을 코드에 고정하지 않습니다.
- 목표 시간이 양수이며 `0 <= 잔여 시간 × 100 <= 목표 시간 × 30`인 SLA를 포함합니다. 정확히 30%인 경우와 아직 위반되지 않은 잔여 0도 포함합니다.
- 티켓의 어느 SLA든 진행 또는 완료 주기에 위반 이력이 있으면 그 티켓 전체를 제외합니다. 다른 단계의 잔여 시간이 조건에 맞더라도 발송하지 않습니다.
- 완료된 SLA 주기는 발송 행을 만들지 않습니다. 현재 진행 중인 다른 주기의 위반 여부 확인에는 사용합니다.
- 기존 프로젝트 정책에 따라 라이선스 요청과 완료 상태 티켓을 제외합니다.
- 일시정지 중인 진행 주기도 조건에 맞으면 포함하고 메일에 일시정지를 표시합니다. 업무시간 밖이라는 이유로 별도 제외하지 않습니다.
- 잔여 시간은 Jira 업무 캘린더 계산값입니다. 달력상의 마감 시각에서 현재 시각을 빼거나 상태별 경과 시간을 추정하지 않습니다.

메일에는 단계별로 티켓 링크, 제목, 현재 상태, 담당자, 목표 시간, 잔여 시간, 잔여율, 진행 상태를 표시합니다. 같은 티켓이 여러 단계에 해당하면 각 단계에 표시하고 제목의 건수는 고유 티켓 수로 계산합니다. 각 단계 안에서는 잔여 시간이 짧은 순서로 정렬합니다. 대상이 없으면 메일을 보내지 않습니다.

## 현재 Jira 설정 확인

2026-10-20 Jira 실조회 기준 사이트 전체 SLA 필드는 10개이고 TACEA에서 적용 중인 SLA는 6개입니다. 이슈에 공개된 SLA ID로 개별 설정을 조회해 확인한 값입니다. 기본 목표는 조건별 규칙에 해당하지 않는 나머지 이슈의 목표입니다.

| SLA | 기본 목표 | 조건별 목표 |
|---|---:|---|
| 최초 응답 SLA | 4시간 | 인시던트·서비스 요청·H/W 장애 요청·개선도 4시간 |
| 할 일 SLA | 목표 없음 | 인시던트·개선·서비스 요청 8시간 |
| 연구소 대기 SLA | 8시간 | 인시던트 8시간, 개선 16시간 |
| 개발 SLA | 목표 없음 | 인시던트 48시간, 개선 난이도 상/중/하 240/160/80시간 |
| QA 검토 SLA | 24시간 | 인시던트·개선도 24시간 |
| 해결 시간 SLA | 120시간 | 서비스 요청 40시간, 인시던트 160시간, 개선 난이도 상/중/하 304/224/144시간 |

할 일과 개발의 기본 목표는 0시간이 아니라 미설정입니다. 목표 시간은 Tech-Ops 또는 Dev-Ops 캘린더의 업무시간이며 두 캘린더 모두 한국시간 월~금 09:00~12:00 및 13:00~18:00를 적용하고 등록된 휴일을 제외합니다. Jira 설정은 이후 변경될 수 있고, 이전 주기는 현재 설정과 다른 목표 값을 유지할 수 있습니다.

## 설정과 실행

다음 조건이 모두 충족되면 백엔드 시작 시 일일 작업을 등록합니다.

| 설정 | 조건 |
|---|---|
| `SMTP_HOST` 및 기존 SMTP 설정 | 기존 메일 발송 가능 |
| `NOTIFY_TODO_ENABLED` | `true` |
| `NOTIFY_TODO_TO` | 기존 수신자 목록 사용 |
| `NOTIFY_SLA_DIGEST_ENABLED` | 기본 `true`; `false`로 일일 SLA 메일만 비활성화 |

예약은 `SCHEDULE_CRON`, `TZ`, `REFRESH_REPORT_ENABLED`와 독립적으로 매일 09:00 `Asia/Seoul`입니다. 주말과 공휴일에도 실행합니다. 일시정지나 업무시간 밖의 잔여 시간이 그대로라면 다음 날에도 같은 티켓을 알릴 수 있습니다. 처음 실행할 때 즉시 발송하거나 서버가 중단됐던 날짜의 메일을 소급 발송하지 않습니다. 실행 중인 스케줄러에서 1시간 이내 지연된 예약은 한 번 실행합니다.

동일 프로세스에서 같은 날짜에 성공한 발송과 동시에 호출된 작업은 중복 발송을 막습니다. 성공 날짜는 메모리에 보관하며 다중 worker/replica용 전역 중복 방지는 제공하지 않습니다. 현재 Compose의 단일 백엔드 프로세스를 기준으로 합니다.

Jira 조회 실패, 불완전한 페이지, 손상된 시간 값은 빈 결과로 취급하지 않고 작업을 실패시켜 부분 목록 발송을 방지합니다. 0초 목표는 잔여율을 정의할 수 없어 제외하고 로그로 남깁니다. SMTP 실패 후에는 성공 날짜를 기록하지 않으므로 같은 날 재호출할 수 있지만 자동 재시도 예약은 추가하지 않습니다. 다음 정기 실행은 다음 날 09시입니다.

SMTP가 일부 수신자를 거부한 경우도 실패로 처리합니다. 이 경우 일부 수신자는 이미 메일을 받았을 수 있으므로 운영자가 같은 날짜에 재시도하면 그 수신자에게 중복 전달될 수 있습니다. SMTP 접수 성공은 최종 받은편지함 도착 보장과 구분합니다.

의존성은 기존 `backend/requirements.txt`의 httpx, APScheduler, aiosmtplib를 사용합니다. DB migration이나 프런트엔드 빌드가 필요하지 않습니다. 운영 백엔드를 새 코드로 재배포해야 실제 예약이 적용됩니다.

## HTTP 수동 트리거

`POST /api/v1/notifications/sla-digest/trigger`로 예약과 동일한 SLA 조회·선별·발송을 요청할 수 있습니다. 일반 보고서 트리거와 같은 로그인 사용자 권한을 적용하며 `Authorization: Bearer <access token>` 헤더가 반드시 필요합니다. 이 API는 `LOGIN=false`에서도 비인증 호출을 허용하지 않고, URL query의 `token`이나 `_t`를 인증에 사용하지 않습니다.

요청 본문을 생략하거나 `{}` 또는 `{"dry_run":false}`를 보내면 기존 수신자에게 실제 메일을 발송합니다. 먼저 `{"dry_run":true}`로 확인하면 Jira를 실조회하여 대상 건수만 반환하며 메일 발송·HTML 생성·당일 중복 기록 변경은 하지 않습니다. `dry_run`은 JSON boolean만 허용합니다. 수신자 변경, 강제 재발송, 날짜 변경 옵션은 없습니다.

PowerShell에서 서비스 주소와 기존 로그인 계정으로 access token을 받은 뒤 미리 조회할 수 있습니다. 환경변수의 계정·비밀번호와 응답 토큰을 로그나 공유 문서에 남기지 않습니다.

```powershell
$baseUrl = 'https://reports.example.com'
$loginBody = @{ username = $env:REPORTS_USERNAME; password = $env:REPORTS_PASSWORD } | ConvertTo-Json
$session = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/auth/login" -ContentType 'application/json' -Body $loginBody
$headers = @{ Authorization = "Bearer $($session.access_token)" }
Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/notifications/sla-digest/trigger" -Headers $headers -ContentType 'application/json' -Body '{"dry_run":true}'
```

이미 브라우저 로그인 등으로 발급받은 유효한 access token이 있으면 로그인 요청을 생략하고 그 토큰을 헤더에 사용할 수 있습니다. 실제 발송을 요청하려면 다음과 같이 호출합니다.

```powershell
Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/notifications/sla-digest/trigger" -Headers $headers -ContentType 'application/json' -Body '{"dry_run":false}'
```

성공 응답은 HTTP 200이며 `Cache-Control: no-store`를 적용합니다. 아래 수치는 응답 형식 예시입니다.

```json
{
  "status": "preview",
  "ticket_count": 2,
  "sla_count": 3,
  "recipient_count": 5,
  "generated_at": "2026-10-20T09:00:00+09:00"
}
```

| status | 의미 |
|---|---|
| `preview` | 미리 조회 완료. 현재 대상 건수만 반환하고 발송하지 않음 |
| `sent` | 대상 티켓을 한 통에 담아 SMTP에 접수 완료 |
| `no_matches` | 조건에 맞는 대상이 없어 발송하지 않음 |
| `already_sent` | 같은 KST 날짜에 성공한 발송이 있어 발송하지 않음. 건수는 해당 성공 발송 기준 |

`ticket_count`는 고유 티켓 수, `sla_count`는 메일에 포함될 단계별 SLA 행 수, `recipient_count`는 기존 설정의 유효한 수신자 수이며 이메일 주소는 응답하지 않습니다. `generated_at`은 요청을 처리한 KST 시각입니다. 미리 조회는 같은 날 이미 발송했더라도 최신 Jira 건수를 다시 조회합니다.

수동 호출과 09시 예약은 동일 유스케이스·동시 실행 잠금·당일 중복 기록을 공유합니다. 따라서 수동 실발송을 먼저 완료하면 같은 날의 자동 예약은 다시 보내지 않습니다. 반대 순서도 같습니다. 프로세스를 재시작하면 메모리의 중복 기록이 초기화된다는 기존 제한은 수동 트리거에도 적용됩니다.

미인증·만료 토큰·로그인 비활성화는 401, 잘못된 JSON 형식이나 지원하지 않는 옵션은 422, 메일 기능 비활성화는 503, Jira 조회 또는 SMTP 발송 실패는 502입니다. 외부 오류 원문과 수신자 주소는 오류 응답에 포함하지 않습니다. 감사로그에는 `SLA_DIGEST_TRIGGER` 또는 `SLA_DIGEST_TRIGGER_FAILED` 이벤트와 요청 사용자·실행 모드·건수 또는 오류 종류를 기록합니다. 일부 수신자만 거부된 뒤 재호출할 때의 중복 전달 가능성은 앞의 SMTP 실패 안내를 따릅니다.

## 발송 없는 검증

저장소 루트에서 기존 Python 환경으로 실행합니다.

```powershell
venv\Scripts\python.exe backend\scripts\preview_sla_digest.py
```

이 명령은 Jira를 실조회하고 동일 유스케이스와 렌더러를 실행하지만 SMTP 대신 메모리 어댑터를 사용합니다. 기본 출력은 Git에서 제외된 `output/sla-digest-validation/preview.html`이며 `--output`과 `--env-file`로 경로를 지정할 수 있습니다. 출력 JSON의 `email_sent`는 항상 `false`입니다. HTML에는 실제 티켓 정보가 있으므로 외부 게시하거나 Git에 추가하지 않습니다.

백엔드 디렉터리에서 관련 회귀 검사를 실행합니다.

```bash
python -m unittest tests.test_sla_digest tests.test_sla_digest_api tests.test_sla_digest_renderer tests.test_sla_digest_jira_source tests.test_sla_digest_schedule tests.test_smtp_email_client tests.test_container_lifecycle tests.test_architecture -v
```

경계값, 이미 위반한 티켓 전체 제외, 여러 단계의 한 통 발송, 다음 날 재알림, 실패 후 재시도, 페이지 누락, 동적 SLA 추가, 리소스 종료, 09시 KST 예약과 기존 알림 설정의 연결을 검사합니다. 실제 SMTP 전달과 다음 정기 실행 성공 여부는 배포 후 `[SlaDigest]` 및 스케줄러 로그로 별도 확인합니다.
