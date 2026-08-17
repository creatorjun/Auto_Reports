# API Reference

Base URL은 `/api/v1`입니다. `LOGIN=true`일 때 보호 라우트는 `Authorization: Bearer <access token>`이 필요합니다. EventSource와 파일 링크는 사용자 정의 헤더를 보낼 수 없으므로 `_t=<access token>` query parameter를 사용합니다.

## Public 또는 자체 인증 라우트

| Method | Path | 요청 | 응답 |
|--------|------|------|------|
| POST | `/auth/login` | username, password | access token과 HttpOnly refresh cookie |
| POST | `/auth/refresh` | refresh cookie | 새 access token |
| POST | `/auth/logout` | 없음 | refresh cookie 제거 |
| GET | `/auth/me` | Bearer token | username, login_required |
| GET | `/storage/preview` | folder, name, `_t` | inline file |
| GET | `/storage/preview-converted` | folder, name, `_t` | LibreOffice 변환 PDF |
| GET | `/storage/download` | folder, name, `_t` | attachment file |

`LOGIN=false`이면 인증 검증을 건너뜁니다. 운영 cookie 속성은 `COOKIE_SECURE` 설정을 따릅니다.

## Reports와 잡

| Method | Path | 요청 | 응답 |
|--------|------|------|------|
| GET | `/reports/?limit=20&offset=0` | pagination | `ReportSummary[]` |
| GET | `/reports/latest` | 없음 | `ReportDetail` 또는 `null` |
| GET | `/reports/{report_id}` | path id | `ReportDetail`, 없으면 404 |
| DELETE | `/reports/{report_id}` | path id | 204, 없으면 404 |
| POST | `/trigger/` | 선택적 start_date, end_date | 202와 job_id, 중복 실행이면 409 |
| GET | `/trigger/{job_id}/status` | path id | pending/running/done/error 상태 |
| GET | `/trigger/{job_id}/stream?_t=...` | path id와 token | SSE status/done/error/timeout |

SSE는 300초 timeout과 15초 keepalive를 사용합니다. 날짜를 생략하면 유스케이스가 기본 보고 범위를 계산합니다.

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
