# API Reference

Base URL은 `/api/v1`입니다. `LOGIN=true`일 때 보호 라우트는 `Authorization: Bearer <access token>`이 필요합니다. EventSource와 파일 링크는 사용자 정의 헤더를 보낼 수 없으므로 `_t=<access token>` query parameter를 사용합니다.

## Public 또는 자체 인증 라우트

| Method | Path | 요청 | 응답 |
|--------|------|------|------|
| POST | `/auth/login` | username, password | access token과 HttpOnly refresh cookie |
| POST | `/auth/refresh` | refresh cookie | 새 access token |
| POST | `/auth/logout` | 없음 | refresh cookie 제거 |
| GET | `/auth/me` | HttpOnly refresh cookie | username, login_required, is_superadmin |
| GET | `/storage/preview` | folder, name, `_t` | inline file |
| GET | `/storage/preview-converted` | folder, name, `_t` | LibreOffice 변환 PDF |
| GET | `/storage/download` | folder, name, `_t` | attachment file |

일반 보호 API는 `LOGIN=false`이면 인증 검증을 건너뜁니다. 감사로그 API는 이 경우에도 접근을 거부합니다. 운영 cookie 속성은 `COOKIE_SECURE` 설정을 따릅니다.

## 관리자 감사로그

`GET /audit-logs`는 `SUPERADMIN`의 유효한 access token을 Bearer 헤더로 전달해야 합니다. 일반 `ADMIN` 계정은 403, 미인증·만료 토큰은 401입니다. query string의 토큰은 이 API에 사용할 수 없습니다.

`start_date`, `end_date`(KST 날짜 포함), `event`, `username`, `ip`, `search`, `limit`(1~100, 기본 50), `offset`을 받습니다. 최신순 `items`, 전체 일치 `total`, `limit`, `offset`, 이벤트 목록 `events`, 누락·파일 상태 안내 `warnings`를 반환합니다. 항목은 `timestamp`, `event`, `username`, `ip`, `details`이며 사용자·IP가 없는 과거 기록은 null입니다. 이벤트는 정확히, 사용자·IP·검색어는 대소문자를 구분하지 않는 부분 일치로 찾습니다. 조회는 최대 100페이지이고 더 오래된 기록은 기간을 좁혀 조회합니다. 응답은 `Cache-Control: no-store`입니다.

로그 읽기 실패는 503, 잘못된 날짜 범위·페이지 범위는 422입니다. 자세한 저장·보존 방식은 [감사로그 문서](07_audit_logs.md)에 정리했습니다.

스토리지 미리보기·변환·다운로드는 `Authorization: Bearer <access token>` 헤더와 기존 `_t` 링크 인증을 모두 지원합니다. 둘 다 전달되면 Bearer 헤더를 검증합니다. PDF 변환은 서버에서 최대 120초 동안 실행하며, 브라우저의 변환 요청 제한은 응답 전송 여유를 포함한 150초입니다. 실패 시 JSON `detail`을 미리보기 화면에 표시합니다.

Markdown·텍스트·CSV 등 원본 미리보기도 파일 조회 실패 시 로딩을 종료하고 오류를 표시합니다. 다른 파일을 열면 이전 결과와 오류를 초기화하며, 닫힌 미리보기의 지연 응답은 새 화면에 반영하지 않습니다.

## Reports와 잡

| Method | Path | 요청 | 응답 |
|--------|------|------|------|
| GET | `/reports/?limit=20&offset=0` | pagination | `ReportSummary[]` |
| GET | `/reports/latest` | 없음 | `ReportDetail` 또는 `null` |
| GET | `/reports/{report_id}` | path id | `ReportDetail`, 없으면 404 |
| DELETE | `/reports/{report_id}` | path id | 204, 없으면 404 |
| POST | `/trigger/` | period와 date 또는 기존 start_date, end_date | 202와 job_id, 중복 실행이면 409 |
| GET | `/trigger/{job_id}/status` | path id | pending/running/done/error 상태 |
| GET | `/trigger/{job_id}/stream?_t=...` | path id와 token | SSE status/done/error/timeout |
| GET | `/sla-dashboard/issues` | 없음 | 최신 보고서의 최근 이슈 티켓별 생성·최종 업데이트·상태 |
| GET | `/sla-dashboard/issues/{issue_key}/comments?offset=0&limit=5` | 최근 이슈 key, 0 이상의 offset(기본값 0), 1 이상의 limit(기본값 5) | 최신순 댓글 최대 limit개의 `comments`와 `next_offset` |

대시보드 생성은 `{"period":"week","date":"2026-10-07"}` 형식으로 요청합니다. `period`는 `week`, `month`, `year`이며 `date`와 함께 전달해야 합니다. KST 기준 월요일~일요일, 해당 달 전체, 해당 연도 전체로 기간을 계산합니다. 미래 기준일, 잘못된 기간, 두 필드 중 하나만 전달하거나 기존 `start_date`/`end_date`와 혼용하면 422입니다. 현재 주·월·연의 종료일은 미래일 수 있지만 실제 생성 시점에 조회 가능한 Jira 데이터만 집계합니다.

이 요청은 연간 선택도 `scope=standard`로 저장하므로 기존 대시보드 지표와 위젯 구성을 유지합니다. 기존 `start_date`/`end_date` API와 스케줄러의 연간 판정은 유지합니다. 날짜를 생략하면 유스케이스가 기본 보고 범위를 계산합니다. SSE는 300초 timeout과 15초 keepalive를 사용하며 프런트엔드는 상태 조회로 이어서 생성 완료를 추적합니다.

장기 이슈 목록은 최신 보고서의 w7 티켓 집합을 기준으로 Jira의 현재 `created`, `updated`, `status`를 조회합니다. `updated`는 댓글 생성·수정·삭제를 포함한 Jira 최종 업데이트 시각이며, 댓글 본문은 Jira 문서 형식을 일반 텍스트로 변환해 반환합니다. 댓글 endpoint는 최신 보고서에 포함되지 않은 티켓 key를 404로 거부합니다.

댓글 응답은 `comments` 배열과 `next_offset`을 가진 객체이며, `limit`을 생략하면 최대 5개를 반환합니다. 이어지는 댓글이 있으면 `next_offset`은 `offset + limit`이고 마지막 댓글까지 조회하면 `null`입니다. 다음 요청의 `offset`에 이 값을 전달하는 조회도 지원하지만, 장기 이슈 화면의 `댓글 더보기`는 `offset=0`을 유지하고 `limit=5`, `10`, `15` 순으로 늘려 최신 댓글부터 누적 범위를 다시 조회합니다. 음수 `offset`이나 1 미만의 `limit`은 422로 거부합니다.

댓글 목록 조회는 서버의 Jira 응답 캐시를 사용하지 않고 요청마다 Jira에 작성 시각 최신순(`orderBy=-created`)으로 조회합니다. 프론트엔드 댓글 query의 `staleTime`은 2분이며, 더보기를 누르면 늘어난 `limit`으로 새 요청을 보내고 성공한 최신 응답으로 표시 목록을 갱신합니다. 실패하면 이전에 표시한 댓글을 유지합니다.

## SLA 위반 보고서

`POST /sla-violations`는 `period=week|month|year`와 `date`를 JSON으로 받아 선택 날짜가 속한 기간에 생성된 위반 티켓을 수집하고 히스토리에 자동 저장한 보고서를 201로 반환합니다. `GET /sla-violations/latest`는 마지막 보고서 또는 `null`, `GET /sla-violations/history?limit=20&offset=0`은 생성순 요약 목록, `GET /sla-violations/{id}`는 저장된 보고서를 반환합니다. 잘못된 입력은 422, 생성 중 중복 요청은 409, Jira 수집 오류는 502입니다. [집계 기준과 응답 계약](08_sla_violation_report.md)을 참고하세요.

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
| GET | `/search?q=...&limit=5` | Jira 검색 결과 |
| GET | `/config` | jira_base_url |

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
