# API Reference

문서 기준: 2026-10-21. SLA 일일 알림 수동 트리거와 보고서별 최근 이슈 본문·댓글 조회를 포함합니다.

재배포 보고서는 기존 보호 라우트 인증 규칙을 적용하는 `GET /api/v1/redeployments/latest`로 최신 저장본을 조회하고, `POST /api/v1/redeployments`로 현재 시점 재생성을 요청합니다. 스키마·오류·수집 기준은 [재배포 보고서](09_redeployment_report.md)를 참고하세요.

Base URL은 `/api/v1`입니다. `LOGIN=true`일 때 보호 라우트는 `Authorization: Bearer <access token>`이 필요합니다. EventSource와 파일 링크는 사용자 정의 헤더를 보낼 수 없으므로 `_t=<access token>` query parameter를 사용합니다.

`GET /api/health`는 버전 prefix 밖의 공개 프로세스 확인 API이며 `{ "status": "ok" }`를 반환합니다. Jira 연결·권한 검사는 수행하지 않습니다. API의 상세 입력 모델은 `src/presentation/api/v1` 및 `src/presentation/schemas`가 원본입니다.

## Public 또는 자체 인증 라우트

| Method | Path | 요청 | 응답 |
|--------|------|------|------|
| POST | `/auth/login` | username, password | access token과 HttpOnly refresh cookie |
| POST | `/auth/refresh` | refresh cookie | 새 access token |
| POST | `/auth/logout` | refresh cookie | 활성 Jira 세션과 refresh cookie 제거, 기억한 계정은 유지 |
| GET | `/auth/me` | HttpOnly refresh cookie | username, display_name, auth_provider, login_required, is_superadmin |
| GET | `/auth/providers` | 없음 | `jira.enabled`, 현재 브라우저의 `jira.remembered`. 세션을 생성하지 않음 |
| POST | `/auth/jira/start` | 같은 origin 요청 | 기억한 계정의 권한 재검증 후 앱 복귀 URL 또는 최초 승인 URL. `force_authorization: true`는 이전 연결을 해제하고 새 승인 시작 |
| POST | `/auth/jira/forget` | 같은 origin 요청 | 기억한 브라우저와 활성 세션 해제, 진행 중인 직원 승인 취소, 관련 쿠키 제거 |
| GET | `/auth/jira/callback` | code, state 및 state cookie | JWT refresh cookie 발급 후 `/login?jira=success`로 303 이동 |
| GET | `/storage/preview` | folder, name, `_t` | inline file |
| GET | `/storage/preview-converted` | folder, name, `_t` | LibreOffice 변환 PDF |
| GET | `/storage/download` | folder, name, `_t` | attachment file |

일반 보호 API는 `LOGIN=false`이면 인증 검증을 건너뜁니다. 감사로그와 SLA 일일 알림 수동 트리거는 이 경우에도 접근을 거부합니다. 운영 cookie 속성은 `COOKIE_SECURE` 설정을 따릅니다.

로그인·갱신 응답은 `access_token`, `token_type` 외에 `username`, `display_name`, `auth_provider`, `is_superadmin`을 포함합니다. Jira의 `username`은 `jira:<cloudId>:<accountId>`인 고유 식별자이며 화면 표시 이름과 분리합니다. Jira 계정에는 superadmin 권한을 부여하지 않습니다. cookie를 변경하는 인증 POST는 교차 사이트 요청을 거부합니다. OAuth 설정과 허용 조건은 [Jira 로그인](11_jira_login.md)을 참고하세요.

## 관리자 감사로그

`GET /audit-logs`는 `SUPERADMIN`의 유효한 access token을 Bearer 헤더로 전달해야 합니다. 일반 `ADMIN` 계정은 403, 미인증·만료 토큰은 401입니다. query string의 토큰은 이 API에 사용할 수 없습니다.

`start_date`, `end_date`(KST 날짜 포함), `event`, `username`, `ip`, `search`, `limit`(1~100, 기본 50), `offset`을 받습니다. 최신순 `items`, 전체 일치 `total`, `limit`, `offset`, 이벤트 목록 `events`, 누락·파일 상태 안내 `warnings`를 반환합니다. 항목은 `timestamp`, `event`, `username`, `display_name`, `email_address`, `ip`, `details`이며 사용자·IP가 없는 과거 기록은 null입니다. `username`은 원본 식별자를 유지하며, Jira 사용자의 `display_name`·`email_address`는 현재 저장된 활성 프로필에서 조회하고 확인되지 않으면 null입니다. 이벤트는 정확히, 사용자·IP·검색어는 대소문자를 구분하지 않는 부분 일치로 찾습니다. `username`과 `search` 필터는 표시 이름·이메일도 검색하며 필터 적용 후 건수와 페이지를 계산합니다. 조회는 최대 100페이지이고 더 오래된 기록은 기간을 좁혀 조회합니다. 응답은 `Cache-Control: no-store`입니다.

로그 또는 사용자 프로필 읽기 실패는 503, 잘못된 날짜 범위·페이지 범위는 422입니다. 자세한 저장·보존 방식은 [감사로그 문서](07_audit_logs.md)에 정리했습니다.

스토리지 미리보기·변환·다운로드는 `Authorization: Bearer <access token>` 헤더와 기존 `_t` 링크 인증을 모두 지원합니다. 둘 다 전달되면 Bearer 헤더를 검증합니다. PDF 변환은 서버에서 최대 120초 동안 실행하며, 브라우저의 변환 요청 제한은 응답 전송 여유를 포함한 150초입니다. 실패 시 JSON `detail`을 미리보기 화면에 표시합니다.

Markdown·텍스트·CSV 등 원본 미리보기도 파일 조회 실패 시 로딩을 종료하고 오류를 표시합니다. 다른 파일을 열면 이전 결과와 오류를 초기화하며, 닫힌 미리보기의 지연 응답은 새 화면에 반영하지 않습니다.

## Reports와 잡

| Method | Path | 요청 | 응답 |
|--------|------|------|------|
| GET | `/reports/?limit=20&offset=0` | pagination | `ReportSummary[]` |
| GET | `/reports/latest` | 없음 | `ReportDetail` 또는 `null` |
| GET | `/reports/annual/{year}` | 연도 | 해당 연도의 마지막 annual 보고서, 없으면 404 |
| GET | `/reports/{report_id}/chart-issues` | chart 및 선택·필터 조건 | 현재 Jira 상세와 저장본 비교 메타데이터 |
| GET | `/reports/{report_id}` | path id | `ReportDetail`, 없으면 404 |
| DELETE | `/reports/{report_id}` | path id | 204, 없으면 404 |
| POST | `/trigger/` | period와 date, custom 기간의 start_date/end_date 또는 기존 날짜 요청 | 202와 job_id, 중복 실행이면 409 |
| GET | `/trigger/{job_id}/status` | path id | pending/running/done/error 상태 |
| GET | `/trigger/{job_id}/stream?_t=...` | path id와 token | SSE status/done/error/timeout |
| GET | `/sla-dashboard/issues` | 없음 | 최신 보고서의 최근 이슈 티켓별 생성·최종 업데이트·상태 |
| GET | `/sla-dashboard/issues/{issue_key}/description` | 최근 이슈 key, 선택 report_id(1 이상) | 현재 Jira 본문의 `body`와 참조 이미지 `images` |
| GET | `/sla-dashboard/issues/{issue_key}/description/images/{attachment_id}` | 최근 이슈 key, 본문 이미지 ID, 선택 report_id(1 이상) | 본문에 연결된 이미지 바이너리 |
| GET | `/sla-dashboard/issues/{issue_key}/comments?offset=0&limit=5` | 최근 이슈 key, 0 이상의 offset(기본값 0), 1 이상의 limit(기본값 5), 선택 report_id(1 이상) | 최신순 댓글 최대 limit개의 `comments`와 `next_offset` |

대시보드 생성은 `{"period":"week","date":"2026-10-14"}` 형식으로 요청합니다. `period`는 `day`, `week`, `month`, `year`이며 `date`와 함께 전달해야 합니다. 일간 요청은 `{"period":"day","date":"2026-10-14"}`이며 KST 기준 2026-10-14 00:00 이상, 2026-10-15 00:00 미만을 조회합니다. KST 기준 주간은 해당 주 월요일~일요일 전체, 월간은 해당 달 전체, 연간은 해당 연도 전체로 기간을 계산합니다. 예시 기준일이면 각각 2026-10-12~2026-10-18, 2026-10-01~2026-10-31, 2026-01-01~2026-12-31이며 종료일 전체를 포함하도록 Jira 쿼리는 다음 날 00:00 미만을 사용합니다. 주간은 일요일 전체를 포함하고 다음 월요일인 2026-10-19 00:00은 제외합니다. 미래 기준일, 잘못된 기간, 두 필드 중 하나만 전달하거나 기존 `start_date`/`end_date`와 혼용하면 422입니다. 현재 주·월·연의 종료일은 미래일 수 있지만 실제 생성 시점에 조회 가능한 Jira 데이터만 집계합니다. SLA 위반도 같은 주·월·연간 기간 정책을 사용합니다.

직접 기간 선택은 `{"period":"custom","start_date":"2026-10-01","end_date":"2026-10-14"}`로 요청하며 `date`는 전달하지 않습니다. 두 날짜는 실제 달력에 존재하는 `YYYY-MM-DD` 형식이어야 하고, 시작일은 종료일 이전 또는 같은 날, 종료일은 KST 기준 오늘 이전 또는 같은 날이어야 합니다. 같은 날짜를 양쪽에 선택하면 해당 하루 전체를 조회합니다. 시작일 00:00 이상부터 종료일 다음 날 00:00 미만까지 집계하며, 입력 누락·형식 오류·역전된 기간·미래 종료일·다른 기간 방식과 혼용한 요청은 작업을 시작하지 않고 422를 반환합니다. 직접 선택이 1월 1일~12월 31일이어도 일반 대시보드 보고서로 생성하고 최신 Jira 데이터를 조회합니다. `period` 없이 전달하는 기존 `start_date`/`end_date` 요청의 연간 보고서 분류는 유지합니다. 최신 보고서 재실행은 직접 선택 보고서에도 저장된 시작일과 종료일을 그대로 사용합니다.

이 요청은 연간 선택도 `scope=standard`로 저장하므로 기존 대시보드 지표와 위젯 구성을 유지합니다. 기존 `start_date`/`end_date` API는 1월 1일 시작·같은 연도이며 연말 종료 또는 현재 연도 범위이면 annual로 판정합니다. 날짜 없는 정기 생성은 standard입니다. 날짜를 생략하면 유스케이스가 기본 보고 범위를 계산합니다. SSE는 300초 timeout과 15초 keepalive를 사용하며 프런트엔드는 상태 조회로 이어서 생성 완료를 추적합니다.

이력 목록은 standard와 annual을 모두 포함하고 `/reports/latest`는 standard만 조회합니다. 주기 갱신은 같은 ID의 데이터를 바꿀 수 있으므로 일반 보고서 ID 조회를 불변 SLA 이력과 동일하게 취급하지 않습니다.

장기 이슈 목록은 최신 일반 보고서의 w7 티켓 집합을 기준으로 Jira의 현재 `created`, `updated`, `status`를 조회합니다. 표시 상태가 `보류 중`인 티켓은 목록과 표시 건수에서 제외하며, 공백 차이는 동일한 상태로 처리합니다. 상태는 현재 Jira 값을 우선하고, 값이 없으면 저장 보고서의 상태를 사용합니다. 이 제외는 장기 이슈 목록에만 적용하며 저장 보고서와 본문·댓글 조회 범위는 유지합니다. `updated`는 댓글 생성·수정·삭제를 포함한 Jira 최종 업데이트 시각이며, 댓글 본문은 Jira 문서 형식을 일반 텍스트로 변환해 반환합니다. 댓글 endpoint는 `report_id`를 지정하면 해당 저장 보고서의 w7 티켓 집합을 기준으로 조회하고, 생략하면 최신 일반 보고서를 사용합니다. 보고서가 없거나 해당 집합에 포함되지 않은 티켓 key, 다른 프로젝트 key는 404로 거부합니다.

댓글 응답은 `comments` 배열과 `next_offset`을 가진 객체이며, `limit`을 생략하면 최대 5개를 반환합니다. 이어지는 댓글이 있으면 `next_offset`은 `offset + limit`이고 마지막 댓글까지 조회하면 `null`입니다. 다음 요청의 `offset`에 이 값을 전달하는 조회도 지원하지만, 장기 이슈 및 대시보드 최근 이슈 화면의 `댓글 더보기`는 `offset=0`을 유지하고 `limit=5`, `10`, `15` 순으로 늘려 최신 댓글부터 누적 범위를 다시 조회합니다. 대시보드는 현재 보고서의 ID를 `report_id`로 전달하므로 과거·연간 보고서의 이슈도 현재 Jira 댓글을 조회할 수 있습니다. 음수 `offset`이나 1 미만의 `limit`·`report_id`는 422로 거부합니다.

댓글 목록 조회는 서버의 Jira 응답 캐시를 사용하지 않고 요청마다 Jira에 작성 시각 최신순(`orderBy=-created`)으로 조회합니다. 프론트엔드 댓글 query의 `staleTime`은 2분이며, 더보기를 누르면 늘어난 `limit`으로 새 요청을 보내고 성공한 최신 응답으로 표시 목록을 갱신합니다. 실패하면 이전에 표시한 댓글을 유지합니다.

### 차트 상세 조회

`GET /reports/{report_id}/chart-issues`의 `chart`는 `sla_initial`, `sla_resolution`, `resolution_type`, `redeployment`입니다. `month`(1~12), `issue_type`, `semester=h1|h2`, `sla_status=all|met|violated`, `filter_types`·반복 `selected_types`, `filter_statuses`·반복 `selected_statuses`를 받습니다. 재배포는 추가로 `partner`, `cause`, `assignee` 중 상세 항목 하나를 선택합니다.

SLA 차트는 month 필수, 처리일 유형 차트는 month 불가입니다. 재배포는 month/partner/cause/assignee 중 하나만 허용하고 반기·현재 상태 필터를 허용하지 않습니다. `filter_types=true`인데 `selected_types`가 없으면 빈 선택이며 필터 생략과 다릅니다. 유효하지 않은 조합은 422입니다.

응답은 `issues`, `snapshot_count`, `current_count`, `source_total`, `source_total_exact`, `collection_limit`, `truncated`, `queried_at`, `snapshot_at`, `source=current_jira`입니다. 저장 차트의 수치와 현재 Jira 상세가 다를 수 있으며 보고서 자체를 갱신하지 않습니다. 없는 보고서는 404, Jira 수집 실패는 502입니다.

### 이슈 본문과 첨부 이미지

`GET /sla-dashboard/issues/{issue_key}/description`은 해당 보고서의 최근 이슈 집합을 확인한 뒤 Jira의 현재 본문을 조회합니다. 응답의 `body`는 문단·목록·표를 일반 텍스트로 변환하며 `images`는 본문에 참조된 첨부 이미지 ID와 대체 텍스트입니다. 보고서에 본문을 저장하지 않습니다. 본문이 없는 경우 빈 문자열과 빈 이미지 목록을 반환하며, 없는 티켓과 보고서 범위 밖의 요청은 404입니다. `/description/images/{attachment_id}`도 현재 본문의 이미지인지 확인한 뒤 기존 이미지 크기·종류 제한을 적용해 반환합니다. 보호 API 인증 및 선택 `report_id` 범위는 댓글과 동일합니다.

`GET /sla-dashboard/issues/{issue_key}/comments/{comment_id}/images/{attachment_id}`는 선택 `report_id`가 가리키는 보고서(생략 시 최신 일반 보고서)의 티켓과 댓글에 연결된 이미지인지 확인한 뒤 바이너리로 반환합니다. 보호 API의 Bearer 인증을 사용하고 `Cache-Control: private, max-age=120`을 반환합니다. 임의 첨부 ID나 해당 보고서 티켓 집합 밖의 키는 허용하지 않습니다. 원본 공급자 실패는 502입니다.

## 전체 이슈

`GET /issue-management/issues`는 `issues`, `initialized`, `refreshing`, `synced_at`, `error`를 반환합니다. 서버에서 프로젝트 전체/증분 수집을 백그라운드로 시작하고 현재 메모리 캐시를 즉시 반환합니다. 최소 30초 간격의 요청 유발 갱신이며 처음과 1시간 경과 후 전체를 수집합니다. 증분 조회에는 2분 중첩을 둡니다. 동기화 실패는 기존 캐시와 error에 반영하므로 HTTP 성공을 최신 동기화 성공과 구분합니다. 서버 측 검색·pagination API가 아니라 프런트엔드가 받은 전체 목록을 필터링합니다.

상태 전이 기준 검색에는 `status_transitions`(이슈 키 → 상태명 → 마지막 전이 시각), `status_transition_days`(이슈 키 → 상태명 → 한국 시간 기준 경과 일수), `transition_history_ready`를 함께 반환합니다. 같은 상태로 여러 번 전이되면 가장 최근 전이만 사용하며, 이후 다른 상태로 바뀌어도 해당 전이 이력은 남습니다. 기존 `issues[].elapsed_days`는 생성일 기준을 유지합니다. 최초 상태나 이력이 없는 상태에 전이일을 생성하지 않으며, 수정일·해결일을 전이일로 대체하지 않습니다. 실제 Jira 상태 ID를 현재 상태명으로 연결하므로 이력의 `Closed`도 현재 표시명인 `닫힘`으로 조회됩니다.

상태 이력은 `status` 필드만 bulk changelog API로 수집하여 기존 스냅샷 JSON에 보관합니다. 전체 동기화에서도 수정 시각이 같은 이슈의 이력은 재사용하고 새 이슈·수정된 이슈만 갱신합니다. 이전 형식 스냅샷은 기존 목록을 먼저 표시한 뒤 전체 이력을 보강하며, 준비 전에는 `transition_history_ready=false`입니다. 이력 조회·검증·저장 실패 시 기존 목록과 이력을 함께 유지하고 오류를 반환합니다. 자정을 넘기면 한국 날짜 기준 전이 경과일을 다시 계산합니다.

`/issue-management/issues/{issue_key}` 아래의 보호 API는 저장된 전체 이슈 목록에 포함된 프로젝트 티켓만 허용합니다. 보고서 ID 없이 완료·이전 티켓도 조회하며, 상세 조회 자체는 목록 동기화를 시작하지 않습니다. 본문·댓글 변환과 참조 이미지 검증은 보고서 상세와 같은 `IssueDetailsService`를 사용합니다.

| GET 경로 접미사 | 응답 |
|---|---|
| `/description` | 현재 Jira 본문 `body`와 참조 이미지 `images` |
| `/description/images/{attachment_id}` | 현재 본문에 참조된 이미지 |
| `/comments?offset=0&limit=5` | 최신순 댓글과 `next_offset`; 화면은 limit를 5, 10, 15개로 증가 |
| `/comments/{comment_id}/images/{attachment_id}` | 해당 댓글에 참조된 이미지 |

목록 밖 티켓·다른 프로젝트·관련 없는 이미지는 404, 잘못된 offset/limit는 422, 공급자 실패는 502입니다. 이미지 응답은 `Cache-Control: private, max-age=120`이며 본문과 댓글을 기존 보고서에 저장하지 않습니다.

## SLA 현황

`GET /sla-status`는 현재 SLA 잔여율이 30% 미만인 미완료·미위반 티켓의 스냅샷을 반환합니다. 서버 캐시는 60초이며 `refresh=true`로 새 수집을 요청합니다. 같은 티켓의 여러 SLA는 한 티켓에 묶고 상태별 해결 SLA 체류시간과 확인 불가 경고를 제공합니다. 인증은 일반 보호 API와 같고 응답은 `Cache-Control: no-store`입니다. 수집 실패는 503이며 빈 정상 결과와 구분합니다. [조회 기준과 시간 해석](15_sla_status.md)을 참고하세요.

## SLA 위반 보고서

`POST /sla-violations`는 `period=week|month|year`와 `date`를 JSON으로 받아 주간은 해당 주 월요일~일요일 전체, 월간·연간은 해당 달·연도 전체에 생성된 위반 티켓을 수집하고 히스토리에 자동 저장한 보고서를 201로 반환합니다. 기준일이 2026-10-14이면 주간은 2026-10-12~2026-10-18이며, KST 기준 일요일 전체를 포함하고 다음 월요일 00:00은 제외합니다. 기존 저장 보고서는 재계산하지 않습니다. `GET /sla-violations/latest`는 마지막 보고서 또는 `null`, `GET /sla-violations/history?limit=20&offset=0`은 생성순 요약 목록, `GET /sla-violations/{id}`는 저장된 보고서를 반환합니다. 잘못된 입력은 422, 생성 중 중복 요청은 409, Jira 수집 오류는 502입니다. [집계 기준과 응답 계약](08_sla_violation_report.md)을 참고하세요.

## SLA 위반 임박 알림 트리거

`POST /notifications/sla-digest/trigger`는 매일 09시 KST 예약과 같은 SLA 일일 알림을 수동 실행합니다. 일반 로그인 사용자의 유효한 Bearer access token이 필요하며, URL 토큰은 받지 않고 `LOGIN=false`인 경우도 401로 거부합니다.

요청 본문 생략·`{}`·`{"dry_run":false}`는 실제 발송, `{"dry_run":true}`는 Jira 실조회 후 대상 건수만 반환합니다. 미리 조회는 메일을 보내거나 당일 중복 기록을 변경하지 않습니다. `dry_run`은 JSON boolean이며 추가 필드와 수신자·강제 재발송 옵션은 허용하지 않습니다.

HTTP 200 응답은 `status`, `ticket_count`, `sla_count`, `recipient_count`, `generated_at`이며 `Cache-Control: no-store`를 적용합니다. 상태는 발송 접수 `sent`, 대상 없음 `no_matches`, 당일 발송 완료 `already_sent`, 미리 조회 `preview`입니다. `already_sent`의 건수는 당일 성공한 발송 기준입니다. 수동·예약 실행은 동일한 당일 중복 방지를 사용하므로 수동 발송을 먼저 완료하면 그날의 정기 예약은 다시 발송하지 않습니다.

입력 오류 422, 기능 비활성화 503, Jira·SMTP 실패 502를 반환합니다. 진행·완료 SLA 어디에든 위반 이력이 있는 티켓은 전체 제외하고 잔여율 0~30%인 티켓만 다룹니다. [PowerShell 호출 예시, 설정 및 실패 후 재시도 주의사항](12_sla_digest.md#http-수동-트리거)을 참고하세요.

## 재배포 현황 보고서

| Method | Path | 응답 |
|---|---|---|
| GET | `/redeployments/latest` | 마지막 저장본 또는 null |
| POST | `/redeployments` | body 없이 현재 기준 강제 갱신, 성공 200과 저장본 |

동시 수집은 409, 수집 실패는 502이며 `Cache-Control: no-store`를 적용합니다. 같은 KST 날짜는 기존 저장본을 대체합니다. 매일 08시 KST 갱신은 서버 스케줄러가 수행합니다. 별도의 날짜별 이력 조회·삭제 API는 없습니다. [재배포 계약](09_redeployment_report.md)을 참고하세요.

## Sites

| Method | Path | 응답 |
|--------|------|------|
| GET | `/sites/` | `SiteSummary[]` |
| GET | `/sites/search?q=...&limit=10` | 검색된 `SiteSummary[]` |
| GET | `/sites/recent?limit=5` | 최근 `SiteSummary[]` |
| GET | `/sites/{site_id}` | `SiteResponse` |
| POST | `/sites/` | 생성된 `SiteResponse` |
| PATCH | `/sites/{site_id}` | 갱신된 `SiteResponse` |
| DELETE | `/sites/{site_id}` | 204 |
| POST | `/sites/{site_id}/nodes` | 갱신된 전체 `SiteResponse` |
| PATCH | `/sites/{site_id}/nodes/{node_id}` | 갱신된 전체 `SiteResponse` |
| DELETE | `/sites/{site_id}/nodes/{node_id}` | 204 |
| POST | `/sites/{site_id}/patch-histories` | 갱신된 전체 `SiteResponse` |
| PATCH | `/sites/{site_id}/patch-histories/{ph_id}` | 갱신된 전체 `SiteResponse` |
| DELETE | `/sites/{site_id}/patch-histories/{ph_id}` | 204 |
| POST | `/sites/{site_id}/visit-histories` | 갱신된 전체 `SiteResponse` |
| PATCH | `/sites/{site_id}/visit-histories/{vh_id}` | 갱신된 전체 `SiteResponse` |
| DELETE | `/sites/{site_id}/visit-histories/{vh_id}` | 204 |

Aggregate 또는 하위 엔티티가 없으면 404입니다.

## Partners, Search, Config

| Method | Path | 응답 |
|--------|------|------|
| GET | `/partners/organizations` | Jira Service Desk 조직 목록 |
| GET | `/partners/organizations/{org_id}/members` | 조직 멤버 목록 |
| GET | `/partners/issues?org_id=...` | 조직 이슈 목록 |
| GET | `/partners/issues?account_id=...` | 멤버 이슈 목록 |
| GET | `/search?q=...&limit=5` | Jira·Confluence 검색 결과, q 1~200자·limit 1~20 |
| GET | `/config` | jira_base_url |

통합 검색은 Jira와 Confluence를 병렬 조회합니다. limit는 각 공급자에 적용되므로 총 결과 수가 limit보다 많을 수 있습니다. 한 공급자 오류는 로그에 남기고 다른 공급자의 결과를 반환할 수 있습니다. Confluence 자동 게시 API는 없습니다.

## 보안 뉴스

| Method | Path | 역할 |
|---|---|---|
| GET | `/security-news` | 마지막 저장 자료 조회, 외부 수집·번역 시작 없음 |
| POST | `/security-news/refresh` | 수동 갱신 요청, 진행 중이면 같은 작업 공유 |

기존 로그인 인증을 적용하며 두 응답 모두 `Cache-Control: no-store`입니다. 자동 수집은 매일 08:00 KST에 실행하고 수동 최신화도 유지합니다. 저장본이 없고 수집 중이 아닌 최초 조회는 `initialized=false`, `refreshing=false`인 빈 목록입니다. 원문 `title`·`summary`, CVE 검색용 `original_description`, 선택적 한국어 한 줄 요약 `summary_ko`를 제공합니다. 별도 제목 번역은 생성하지 않아 `title_ko`는 null이며 `translation`의 기존 필드명으로 요약 진행·완료·대기 상태를 반환합니다. 저장 스냅샷, 갱신 시각과 오류 의미, 60초 수동 제한·NVD·KEV의 2시간 제한·영구 요약 캐시는 [보안 뉴스 계약](13_security_news.md)에 정리했습니다.

## Storage

| Method | Path | 역할 |
|--------|------|------|
| GET | `/storage/quota` | used, limit, available, percent 조회 |
| GET | `/storage/items?folder=...` | 폴더 항목 목록 |
| GET | `/storage/check?folder=...&name=...` | 존재 여부 조회 |
| POST | `/storage/folders` | 폴더 생성 |
| DELETE | `/storage/folders?folder=...&name=...` | 폴더 삭제 |
| POST | `/storage/move` | 파일 또는 폴더를 다른 폴더로 이동 |
| POST | `/storage/selection/archive` | 선택한 파일과 폴더를 ZIP으로 다운로드 |
| POST | `/storage/selection/delete` | 선택한 파일과 폴더를 일괄 삭제 |
| POST | `/storage/upload?folder=...&overwrite=false` | multipart 단일 파일 업로드 |
| POST | `/storage/upload/init` | chunk upload session 생성 |
| POST | `/storage/upload/chunk?upload_id=...&chunk_index=...` | chunk 업로드 |
| POST | `/storage/upload/complete` | chunk 병합과 최종 파일 반환 |
| DELETE | `/storage/upload/abort?upload_id=...` | session 중단과 임시 데이터 삭제 |
| DELETE | `/storage/files?folder=...&name=...` | 파일 삭제 |

`/storage/move`는 `source_folder`, `name`, `destination_folder`를 JSON body로 받습니다. 동일 경로와 폴더 자기 하위 이동은 400, 대상 이름 충돌은 409로 반환합니다.

선택 작업은 `folder`, `names`를 JSON body로 받으며 한 번에 1개 이상 200개 이하의 현재 폴더 항목을 처리합니다. ZIP 임시 파일은 응답 완료 후 자동 삭제됩니다. 일괄 삭제는 모든 항목의 경로와 존재 여부를 먼저 검증합니다.

경로는 Storage adapter가 정규화하고 root 이탈을 거부합니다. 중복은 409, quota 초과는 413, 잘못된 경로는 400 또는 404로 반환합니다.
