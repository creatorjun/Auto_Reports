# Rovo Automation 관리자 설정

문서 기준: 2026-10-21. 이 문서는 현재 소스의 연동 계약과 관리자가 수행할 설정 절차입니다.

## 현재 상태와 적용 순서

Rovo Automation 어댑터, 집계 기반 분석 입력, 결과 검증 및 합성 데이터 검증 명령을 구현했습니다. **코드 배포와 분석 활성화는 별도이며 실제 Rovo 왕복은 아직 검증하지 않았습니다.** 현재 작업 계정은 TACEA의 Automation 생성 권한이 없어 규칙을 만들지 못했습니다. 관리자 설정과 합성 검증 전에는 `AI_PROVIDER=rovo_automation`, `AI_ENABLED=false`로 운영하며 관리자가 이 절차를 적용한 뒤 분석을 활성화합니다.

당시 화면은 로컬 점검 자료 [automation-permission-blocked.png](../../output/rovo-automation-validation/automation-permission-blocked.png)에 있습니다. `output/*-validation/`은 Git 제외 경로이므로 저장소를 새로 받은 환경에는 이 자료가 없을 수 있습니다.

적용 순서는 관리자 권한·전용 이슈 준비 → Automation 규칙 설정 → `AI_ENABLED=false`로 앱 배포 → 설정 형식 검사 → 합성 데이터 왕복 → `AI_ENABLED=true`로 활성화 → 새 보고서 확인입니다. 기존 보고서와 운영 중인 Jira 로그인 설정은 유지합니다.

## 구성과 전송 범위

```text
FastAPI → Atlassian Incoming webhook → Use Rovo
                                      ↓
FastAPI ← Jira REST API 조회 ← 전용 이슈의 요청별 임시 property
    ↓
응답 검증 및 임시 property 삭제 시도 → 보고서와 총평 DB 저장
```

앱은 외부 HTTPS로 웹훅과 기존 Jira 사이트에 접근합니다. Atlassian에서 사내 서버 `10.1.43.100`으로 들어오는 콜백은 사용하지 않습니다. 방화벽은 실제 설정한 웹훅 호스트와 Jira 호스트로의 HTTPS 통신을 허용해야 합니다.

분석 입력은 애플리케이션의 허용 목록으로 구성합니다. 보고 기간, 지표별 집계 범위, 건수·비율·기간, 데이터 한계, 제한된 근거 티켓 키와 이미 생성된 보고서의 저장 JQL을 전달합니다. 고객명·담당자·제목·본문·댓글·첨부파일·인증정보 필드를 넣지 않습니다. 상태명·유형명·JQL과 티켓 키도 업무 메타데이터이므로 조직의 데이터 취급 기준에 맞는지 관리자가 확인합니다.

입력의 JQL은 집계 출처 설명이며 Rovo에 실행시키는 명령이 아닙니다. 애플리케이션의 기존 수집기가 페이지를 이어 조회하거나 Jira 카운트 API로 집계한 결과를 사용합니다. Automation의 `Lookup work items`로 첫 100건을 가져와 전체 건수를 다시 계산하지 않습니다. 근거 키 목록은 제한된 표본으로, 전체 건수를 뜻하지 않습니다. 일부 파생 집계의 JQL·이력·분모가 없는 경우 입력에 그 한계를 명시합니다.

Use Rovo는 프롬프트와 스마트값으로 전달한 텍스트를 분석하며 별도 에이전트·추가 JQL 검색·외부 도구가 필요하지 않습니다. 결과는 보고서 전체 기준이고 화면의 유형·상태·반기 필터는 반영하지 않습니다. 기존 자동 갱신은 재분석하지 않으며 위젯이 바뀐 저장본에는 이전 총평이라는 안내를 표시합니다.

## 관리자 준비 사항

- 대상 Jira 프로젝트에서 Automation 규칙을 만들고 관리할 권한이 필요합니다. Rovo의 자율 실행 연결은 조직 또는 사이트 관리자가 설정하고, 첫 연결에서 사용할 계정 권한을 확인합니다. 이 절차는 A2A 허용 설정이나 MCP 연결을 대신하지 않으며 해당 기능을 활성화하지 않습니다.
- 결과를 잠시 보관할 전용 이슈 하나를 정합니다. 일반 업무 이슈를 임의로 재사용하지 말고 프로젝트·이슈 보안 설정으로 접근 대상을 정합니다. 아래 `TACEA-12345`는 예시이며 실제 준비한 키로 바꿉니다.
- Automation 실행 계정은 전용 이슈를 볼 수 있고 property를 쓸 수 있어야 합니다. 앱의 기존 `JIRA_EMAIL`·`JIRA_API_TOKEN` 계정은 조회와 삭제를 위해 Browse Projects, Edit Issues 및 이슈 보안 접근 권한이 필요합니다. 직원 브라우저 로그인 토큰은 사용하지 않습니다.
- OAuth 기반 API 호출로 변경한다면 조회는 `read:jira-work` 또는 `read:issue.property:jira`, 삭제는 `write:jira-work` 또는 `delete:issue.property:jira` 범위를 확인합니다. 현재 앱은 기존 Jira 이메일·API 토큰 인증을 사용합니다.
- Rovo 사용 가능 플랜·조직 정책·사용량을 확인합니다. `Use Rovo` 실행에는 사용량이 발생할 수 있습니다. 합성 검증도 실제 실행 1회이며 무료라는 의미가 아닙니다.

Jira entity property는 앱별 비밀 저장소가 아닙니다. 해당 이슈를 읽거나 편집할 수 있는 사용자와 허용된 앱이 접근할 수 있으며, Atlassian은 개인·민감 데이터 저장을 권하지 않습니다. 전용 이슈의 접근 제한과 별개로 입력·출력에 개인정보와 민감 원문을 넣지 않습니다. 프로젝트 property는 쓰기·삭제에 관리자 권한이 필요하고 접근 범위가 넓어 이 구현에서 사용하지 않습니다.

## Automation 규칙 만들기

### 1. Incoming webhook

1. 대상 프로젝트의 Automation 또는 Studio의 Automation에서 새 규칙을 만듭니다. 규칙 범위에 전용 결과 이슈의 프로젝트가 포함되어야 합니다.
2. 트리거를 `Incoming webhook`으로 설정합니다.
3. 웹훅 본문의 `issues`에 지정된 이슈를 대상으로 실행하는 옵션을 선택합니다. **`No issues from the webhook`은 선택하지 않습니다.** 뒤의 `Set entity property`에 대상 이슈 문맥이 필요합니다. UI 문구가 다르면 트리거 설명에서 `issues` 배열의 이슈 키를 사용하는 옵션인지 확인합니다.
4. 이슈 키 조건을 추가하여 현재 이슈가 관리자 지정 전용 키와 정확히 일치할 때만 진행시킵니다. 앱의 `ROVO_AUTOMATION_RESULT_ISSUE_KEY`도 같은 키여야 합니다.
5. `{{webhookData.schema_version}}`이 `1`인지, `request_id`가 32자리 소문자 16진 문자열인지, `input_hash`가 64자리 소문자 16진 문자열인지 확인하는 조건을 추가합니다. 정규식은 각각 `^[0-9a-f]{32}$`, `^[0-9a-f]{64}$`입니다.
6. `expires_at_ms`가 숫자로 존재하고 `{{now.toMillis}}`가 `{{webhookData.expires_at_ms}}` 이하일 때만 진행하도록 숫자 비교 조건을 설정합니다. 화면에 이하 비교가 없으면 `작음` 비교로 설정해 만료 시각 직전까지만 허용합니다.

앱이 보내는 JSON의 필드는 다음과 같습니다. 아래 값은 설명용 예시이며 실제 요청의 ID·해시·만료 시각은 앱이 생성합니다.

```json
{
  "schema_version": 1,
  "issues": ["TACEA-12345"],
  "request_id": "0123456789abcdef0123456789abcdef",
  "input_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "prompt": "보고서 집계와 출력 형식이 포함된 분석 프롬프트",
  "expires_at_ms": 1792556400000
}
```

`request_id`는 UUID의 하이픈 없는 32자리 hex, `input_hash`는 프롬프트 UTF-8 바이트의 SHA-256입니다. `expires_at_ms`는 요청 시작 시각에 앱의 전체 분석 제한 시간을 더한 UTC Unix 밀리초입니다. 예시 시각을 실제 규칙이나 요청에 고정하지 않습니다.

규칙에서 발급한 URL과 secret을 안전하게 보관합니다. 앱은 `X-Automation-Webhook-Token` 헤더로 secret을 전송합니다. URL 뒤에 secret을 붙이지 말고 앱 설정에서도 둘을 분리합니다. 토큰을 재발급하면 이전 토큰은 무효화되므로 앱 설정도 함께 갱신해야 합니다. 이 단계에서 발급된 실제 URL·secret을 문서·Git·스크린샷·공유 로그에 넣지 않습니다.

### 2. Use Rovo

`Use Rovo` 액션을 추가하고 필요한 사이트 연결을 완료합니다. 프롬프트에는 다음 스마트값을 넣습니다.

```text
{{webhookData.prompt}}
```

앱이 분석 규칙·허용된 데이터·응답 형식을 함께 전달하므로 규칙에 다른 데이터 조회나 고객·담당자 필드를 추가하지 않습니다. 출력은 `{{rovoResponse}}`입니다. `Use agent`의 `{{agentResponse}}`와 혼용하지 않습니다.

Rovo에 요구하는 출력은 다음 다섯 필드만 있는 JSON 객체입니다. JSON을 출력하도록 요청하더라도 모델의 엄격한 스키마 준수가 보장되는 것은 아니므로 앱이 다시 검증합니다.

```json
{
  "summary": "실제 보고 기간을 포함한 한국어 요약",
  "risks": ["지표나 근거 키로 설명한 문제점 또는 데이터 한계"],
  "bottlenecks": [],
  "recommendations": ["근거에 연결된 점검 또는 개선 제안"],
  "sentiment": "warning"
}
```

- `summary`: 비어 있지 않은 문자열, 최대 1000자.
- `risks`, `bottlenecks`, `recommendations`: 필수 배열, 각각 최대 5개, 각 원소는 비어 있지 않은 문자열로 최대 300자. 근거가 없는 병목은 빈 배열입니다.
- `sentiment`: `good`, `warning`, `critical` 중 하나. 정보가 부족하면 `warning`을 요청합니다.
- 추가 필드, 잘못된 자료형, 입력에 없는 티켓 키는 앱에서 거부합니다. 정량적 사실과 인과관계까지 자동으로 증명하는 검증은 아니므로 관리자 합성 검증과 실제 보고서 확인이 필요합니다.

### 3. 만료 확인과 임시 결과 저장

Use Rovo 뒤, 저장 액션 **직전**에 `{{now.toMillis}} <= {{webhookData.expires_at_ms}}` 숫자 비교 조건을 한 번 더 둡니다. 이하 비교가 없으면 앞 단계와 같이 `작음`으로 설정합니다. 만료되었으면 결과를 쓰지 않고 종료합니다. 앞의 만료 조건은 오래 대기한 요청의 불필요한 분석을 줄이고, 이 조건은 앱이 기다리지 않는 결과가 뒤늦게 저장되는 경우를 줄입니다.

`Set entity property` 액션을 추가합니다.

| 설정 | 값 |
|---|---|
| Entity type | Issue / Work item |
| Property key | `auto_reports.rovo.{{webhookData.request_id}}` |
| Property value | 아래 템플릿 |

```text
{
  "schema_version": 1,
  "request_id": {{webhookData.request_id.asJsonString}},
  "input_hash": {{webhookData.input_hash.asJsonString}},
  "expires_at_ms": {{webhookData.expires_at_ms}},
  "status": "completed",
  "output": {{rovoResponse.asJsonString}}
}
```

`asJsonString`은 JSON 문자열의 따옴표와 특수문자 이스케이프를 함께 만듭니다. **스마트값 바깥에 따옴표를 추가하지 않습니다.** `output`은 JSON 객체가 아니라 Rovo 응답을 담은 문자열입니다. 원문을 직접 삽입하면 응답 속 따옴표·개행 때문에 property JSON이 깨질 수 있습니다. 저장 전 문법 검사기가 미치환 스마트값을 경고하면 템플릿과 최종 JSON을 구분하여 합성 실행 결과로 확인합니다.

Jira 제한은 property key 255 bytes, value 32,768 bytes입니다. 앱의 출력 필드 상한은 이 제한에 여유를 두기 위한 계약이며, 임의로 늘리지 않습니다. property 전체가 제한을 넘으면 저장 실패이므로 audit log에서 확인합니다. `expires_at_ms`는 관리자 정리에 사용하는 추가 메타데이터이며 앱의 출력 JSON 안에 넣지 않습니다.

규칙을 저장하고 활성화한 뒤 전용 이슈 조건·만료 조건·Rovo 연결·최종 템플릿을 다시 확인합니다. 앱이 임시 property를 삭제해도 규칙 audit log와 Atlassian의 처리 이력이 함께 지워지는 것은 아닙니다.

## 앱 설정

초기에는 다음 값을 안전한 서버 설정 경로에 넣고 AI를 비활성화합니다. 이 값은 형식 예시이며 URL·토큰·이슈 키는 관리자가 준비한 값으로 바꿉니다.

```dotenv
AI_PROVIDER=rovo_automation
AI_ENABLED=false
ROVO_AUTOMATION_WEBHOOK_URL=https://api-private.atlassian.com/automation/webhooks/REPLACE_WITH_REAL_PATH
ROVO_AUTOMATION_WEBHOOK_TOKEN=REPLACE_WITH_SECRET
ROVO_AUTOMATION_RESULT_ISSUE_KEY=TACEA-12345
ROVO_AUTOMATION_TIMEOUT_SECONDS=180
ROVO_AUTOMATION_POLL_SECONDS=5
```

기존 `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`도 필요합니다. 현재 어댑터가 허용하는 웹훅은 HTTPS의 `api-private.atlassian.com/automation/webhooks/`, `api.atlassian.com/automation/webhooks/`, `automation.atlassian.com/pro/hooks/` 경로입니다. 규칙에서 발급한 URL을 그대로 사용하고 URL에 계정정보·query·fragment·secret을 추가하지 않습니다. 발급 URL이 허용 범위와 다르면 임의로 변형하지 말고 앱 지원 범위를 검토합니다.

| 설정 | 기본값 | 범위·의미 |
|---|---|---|
| `ROVO_AUTOMATION_TIMEOUT_SECONDS` | 180 | 15~300초, 제출·결과 대기를 포함한 분석 제한 |
| `ROVO_AUTOMATION_POLL_SECONDS` | 5 | 1~30초, 임시 property 조회 간격 |
| `AI_ENABLED` | true | 초기 적용에는 명시적으로 false, 합성 검증 후 true |
| `AI_PROVIDER` | gemini | Rovo에는 rovo_automation을 명시 |

프런트엔드의 보고서 생성 대기 한도는 전체 5분입니다. Rovo 분석은 Jira 수집 뒤에 실행되므로 기본 180초를 권장합니다. Rovo 한도를 300초로 올리면 수집 시간을 더해 화면 대기 한도를 넘을 수 있습니다. 화면에서 시간초과가 나면 자동으로 보고서 생성을 반복하지 말고 히스토리와 서버 작업 상태·규칙 audit log부터 확인합니다.

프롬프트에는 앱 자체의 UTF-8 60,000 bytes 제한이 있습니다. 이는 Atlassian 웹훅의 공식 최대 크기를 뜻하지 않습니다. 서버는 두 분석까지 동시에 실행하고 웹훅은 요청당 한 번만 전송합니다. Jira 조회의 `429`에서는 `Retry-After`를 반영하며 전체 제한 시간 안에서 기다립니다.

## 운영 배포와 합성 검증

아래는 관리자 적용을 위한 Bash 절차이며 이미 실행한 배포 기록이 아닙니다. 서버의 `/Auto_Reports`에서 작업합니다. 먼저 [운영·배포 가이드](10_operations.md)에 따라 검토된 소스 반영, DB 백업, 진행 중인 보고서 작업 유무와 이전 이미지·커밋을 확인합니다. backend 교체는 실행 중인 작업을 중단할 수 있으므로 작업 완료 후 진행합니다.

### 기존 Compose 설정 보존

현재 운영 환경은 기본 파일·HTTPS override·런타임 환경 보존 파일 세 개를 함께 사용합니다. 실행 중 컨테이너의 실제 경로를 먼저 확인합니다. 전체 `docker inspect`나 값이 포함된 전체 Compose 설정을 공유 로그에 출력하지 않습니다.

```bash
cd /Auto_Reports
docker inspect tac_backend --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}'
docker inspect tac_frontend --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}'
```

2026-10-21 점검에서 확인한 세 경로는 다음과 같습니다. 현재 출력과 일치할 때 사용하며, 달라졌으면 현재 운영 경로를 검토해 반영합니다. 세 번째 파일은 현재 활성 설정이므로 이름에 `backups`가 있어도 생략하거나 삭제하지 않습니다.

```bash
compose_files=(
  -f /Auto_Reports/docker-compose.yml
  -f /Auto_Reports/docker-compose.override.yml
  -f /var/backups/auto_reports/recent-comments-20261021T120322/preserved-runtime-environment.json
)
docker compose "${compose_files[@]}" config --quiet
```

`.env`, 위 세 파일, 인증서·개인 키와 기존 환경값을 보존합니다. 설정 변경은 Rovo 관련 키와 `AI_PROVIDER`·`AI_ENABLED`에 한정합니다. 뒤의 Compose 파일의 `backend.environment`에 같은 키가 있으면 `.env`보다 우선하므로 **실제로 적용되는 최종 값**도 맞춰야 합니다. 보호된 편집기나 비밀 관리 절차로 필요한 키만 수정하며 전체 런타임 환경을 새 설정으로 덮어쓰지 않습니다. JSON·환경 파일의 비밀값을 터미널에 출력하거나 Git에 추가하지 않습니다.

2026-10-21 읽기 전용 재확인에서는 세 번째 파일에 `AI_ENABLED`·`AI_PROVIDER` 덮어쓰기가 없었습니다. 이 상태가 유지된다면 `.env`에 `AI_ENABLED=false`, `AI_PROVIDER=rovo_automation`과 Rovo 설정을 넣으면 되며 추가 override 파일은 필요하지 않습니다. 당시 실행 중인 backend는 `AI_ENABLED=true`, `AI_PROVIDER` 미설정이었으므로, 기존 Gemini 활성 상태를 둔 채 새 분석 소스를 먼저 배포하지 않습니다. 비활성 설정을 준비한 다음 이미지를 적용합니다.

### AI 비활성 상태 배포

소스와 설정을 준비한 뒤 backend·frontend를 빌드합니다. 변경된 소스가 컨테이너에 있어야 다음 검증 모듈도 실행할 수 있습니다.

```bash
docker compose "${compose_files[@]}" build backend frontend
docker compose "${compose_files[@]}" up -d --no-build --no-deps backend
docker inspect tac_backend --format '{{.State.Health.Status}}'
```

backend가 `healthy`가 된 뒤 frontend를 교체하고 nginx와 HTTPS를 확인합니다. DB 컨테이너는 재생성하지 않습니다.

```bash
docker compose "${compose_files[@]}" up -d --no-build --no-deps frontend
docker compose "${compose_files[@]}" exec -T frontend nginx -t
docker compose "${compose_files[@]}" exec -T frontend nginx -s reload
curl --cacert /Auto_Reports/.certs/fullchain.pem --fail --silent --show-error https://10.1.43.100/api/health
docker compose "${compose_files[@]}" exec -T backend python -c 'from src.infrastructure.config.settings import Settings; s=Settings(); print({"ai_enabled": s.ai_enabled, "ai_provider": s.ai_provider})'
```

마지막 출력이 `ai_enabled: False`, `ai_provider: rovo_automation`인지 확인합니다. health 성공은 Rovo 연결 성공이 아닙니다.

### 설정 형식 검사와 실제 왕복

표준 Compose 환경에서는 다음 명령을 사용합니다. `Settings`는 현재 작업 디렉터리의 `.env`와 프로세스 환경을 읽으므로 임의의 로컬 디렉터리에서 실행하지 않고, 실제 배포한 backend 컨테이너 안에서 실행하는 방식을 권장합니다.

```bash
docker compose exec -T backend python -m scripts.verify_rovo_automation
docker compose exec -T backend python -m scripts.verify_rovo_automation --execute
```

위 세 설정 파일을 쓰는 운영 환경에서는 같은 명령에 `compose_files`를 반드시 적용합니다.

```bash
docker compose "${compose_files[@]}" exec -T backend python -m scripts.verify_rovo_automation
docker compose "${compose_files[@]}" exec -T backend python -m scripts.verify_rovo_automation --execute
```

- 옵션 없음: 로컬 설정 형식·필수값 검사만 합니다. HTTP 요청, Jira 권한 확인, Rovo 실행은 없습니다. `configured: true`, `executed: false`는 실제 연결 성공이 아닙니다.
- `--execute`: 회사 보고서를 읽지 않고 기간·생성 20건·완료 15건 등의 고정 합성 수치만 한 번 보냅니다. 이 명령은 명시적 연결 시험이므로 `AI_ENABLED=false` 상태에서도 실행합니다. 실제 웹훅·Rovo·Jira 임시 property 쓰기/조회/삭제가 발생할 수 있습니다.
- 종료 코드 0과 `verified_result: true`, `provider: rovo_automation`, `company_report_transmitted: false`를 확인합니다. 응답 내용·토큰은 출력하지 않습니다. `verified_result: true`만으로 최종 DELETE까지 성공했다고 보장하지 않으므로 정리 경고와 잔존 property도 확인합니다.
- 규칙 audit log에서 실행 대상 이슈, 조건, Use Rovo, property 저장이 성공했는지 함께 확인합니다. 웹훅 HTTP 200만으로 성공을 판단하지 않습니다. Atlassian의 새 웹훅은 잘못된 토큰에도 200을 돌려줄 수 있습니다.

### 활성화

합성 왕복과 임시 결과 정리를 확인한 뒤, 앞에서 확인한 실제 적용 설정의 `AI_ENABLED`만 `true`로 바꿉니다. 설정은 프로세스 시작 시 읽으므로 단순 `restart` 대신 backend를 재생성합니다.

```bash
docker compose "${compose_files[@]}" up -d --no-build --no-deps --force-recreate backend
docker inspect tac_backend --format '{{.State.Health.Status}}'
```

backend가 `healthy`가 되면 nginx를 reload하고 앱의 적용 설정을 확인합니다.

```bash
docker compose "${compose_files[@]}" exec -T frontend nginx -t
docker compose "${compose_files[@]}" exec -T frontend nginx -s reload
docker compose "${compose_files[@]}" exec -T backend python -c 'from src.infrastructure.config.settings import Settings; s=Settings(); print({"ai_enabled": s.ai_enabled, "ai_provider": s.ai_provider})'
```

새 보고서 하나를 생성하여 저장된 기간·집계와 총평을 대조합니다. 요약·문제점·병목·개선 제안, Rovo 표시와 분석 시각, 히스토리 재조회, PDF·Excel의 분석 내용까지 확인합니다. 근거 없는 병목 배열은 비어 있을 수 있습니다. 자동 갱신 후에는 이전 분석이라는 안내가 나오는지 확인합니다. 과거 보고서는 이 설정만으로 자동 재분석되지 않습니다.

활성화 뒤 분석 실패가 반복되면 `AI_ENABLED=false`로 되돌리고 같은 방식으로 backend를 재생성합니다. 수집·보고서 저장은 계속 사용할 수 있습니다. 코드나 이미지 롤백이 필요하면 배포 전에 보존한 커밋·이미지와 운영 절차를 사용하며, 데이터 볼륨을 지우지 않습니다.

## 시간초과·임시 결과 정리

어댑터는 property key, schema version, request ID, 입력 해시, 완료 상태, 출력 문자열과 출력 스키마를 확인합니다. 검증 결과는 메모리의 분석 객체로 만들고, **분석 호출의 `finally`에서 자기 요청의 property 삭제를 시도한 뒤** 호출자에게 돌려줍니다. 보고서 DB 저장은 그 이후입니다. DB에 저장된 총평을 삭제하는 동작이 아닙니다.

삭제는 최대 5초 동안 시도하며 실패하면 경고를 남깁니다. timeout이나 취소가 발생해도 Atlassian의 원격 실행이 자동 취소되는 것은 아닙니다. 만료 조건이 있어도 취소 직후 실행, 만료 검사와 저장 사이의 경합, 삭제 실패로 임시 결과가 남을 수 있습니다. **시간초과 응답만으로 원격 결과 정리 완료를 보장하지 않습니다.**

관리자는 기존의 승인된 Jira 인증 수단으로 다음 범위만 확인·정리합니다. 인증정보를 명령줄 인자·공유 로그에 직접 넣지 않습니다.

1. `GET /rest/api/3/issue/{전용이슈키}/properties`로 property key 목록을 조회합니다.
2. `auto_reports.rovo.` 접두어와 32자리 hex 요청 ID 형식에 맞는 키만 고릅니다. 다른 앱의 property는 건드리지 않습니다.
3. `GET /rest/api/3/issue/{전용이슈키}/properties/{해당키}`의 `value.expires_at_ms`가 숫자이고 현재 UTC Unix 밀리초보다 과거인지 확인합니다. 아직 실행 중인 요청은 지우지 않습니다. 만료값이 없거나 형식이 잘못된 항목은 자동 삭제하지 말고 audit log와 생성 경위를 확인합니다.
4. 조건을 확인한 해당 키만 `DELETE /rest/api/3/issue/{전용이슈키}/properties/{해당키}`로 삭제합니다. 성공은 204이며, 다시 조회했을 때 404이면 해당 property가 없습니다.

이 임시 데이터 정리는 앱 DB의 보고서 보존 기간과 별개입니다. Jira property에는 이 구현이 사용하는 자동 TTL이 없으므로 관리자 점검 절차에 잔존 확인을 포함합니다.

| 증상 | 확인할 내용 |
|---|---|
| 설정 형식 검사 실패 | 공식 HTTPS URL 형식, 필수 토큰·기존 Jira 인증, 고정 이슈 키, 시간 범위 |
| 웹훅 200인데 결과 없음 | 활성 규칙·secret·`issues` 트리거 대상·전용 이슈 조건·만료 시각·audit log |
| 전용 이슈 조회/삭제 실패 | 앱 인증 계정의 Browse Projects·Edit Issues·이슈 보안 접근 |
| property JSON 저장 실패 | `asJsonString` 바깥 따옴표 중복, 값의 32,768 bytes 제한, Rovo 응답 크기 |
| 앱이 결과 거부 | request ID·해시·schema version, 필수 출력 필드·자료형·길이, 입력에 없는 티켓 키 |
| Rovo 분석 시간초과 | 규칙 실행 지연·조직 사용량·Jira 제한을 확인하고 늦게 저장된 결과 점검 |
| 화면 대기 시간초과 | 보고서 전체 5분 한도와 Jira 수집 시간을 함께 확인, 히스토리 확인 후 판단 |
| 총평 없이 보고서 저장 | 분석 실패를 수집 실패와 분리한 정상 동작; 원인은 별도 확인 |

## 공식 참고 문서

- [Use Rovo 설정과 연결 권한](https://support.atlassian.com/studio/docs/use-rovo-in-an-automation-rule/)
- [Use Rovo의 텍스트 입력·출력 범위](https://support.atlassian.com/studio/docs/what-is-the-use-rovo-action/)
- [Incoming webhook URL·secret 설정](https://support.atlassian.com/cloud-automation/docs/configure-the-incoming-webhook-trigger-in-atlassian-automation/)
- [웹훅 검증과 HTTP 200의 한계](https://support.atlassian.com/automation/kb/check-if-the-incoming-webhook-trigger-in-an-automation-rule-is-correct/)
- [JSON 스마트값과 asJsonString](https://support.atlassian.com/cloud-automation/docs/jira-smart-values-json-functions/)
- [Set entity property와 Automation 액션](https://support.atlassian.com/cloud-automation/docs/jira-automation-actions/)
- [Issue properties REST API·조회/삭제 권한](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-properties/)
- [Entity properties 보안·크기 제한](https://developer.atlassian.com/cloud/jira/platform/jira-entity-properties/)
- [Jira rate limit과 Retry-After](https://developer.atlassian.com/cloud/jira/platform/rate-limiting/)
- [Automation 서비스 제한](https://support.atlassian.com/cloud-automation/docs/automation-service-limits/)
