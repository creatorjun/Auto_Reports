# Data Model

문서 기준: 2026-10-16.

Alembic `0018`은 재배포 스냅샷 테이블 `redeployment_reports`를 추가합니다. `id`, KST 날짜 유일 키 `snapshot_date`, `generated_at`, `generated_by`, 원본 티켓·JQL·경고를 포함한 JSONB `payload`를 저장하며 같은 날 갱신은 원자적으로 대체합니다. 자세한 계약은 [재배포 보고서](09_redeployment_report.md)를 참고하세요.

PostgreSQL과 SQLAlchemy async ORM을 사용합니다. 영속성 모델은 `src/infrastructure/persistence`, 프레임워크 독립 모델은 `src/domain`에 있습니다.

## Tables

### reports

| Column | Type | 설명 |
|--------|------|------|
| id | integer PK | 자동 증가 ID |
| week_start, week_end | date | 보고 범위 |
| report_date | varchar | 표시용 보고서 날짜 |
| widgets | jsonb | widget serializer 결과 |
| ai_analysis | jsonb nullable | 선택적 Gemini 요약, 위험, 권고, sentiment |
| scope | varchar | `standard` 또는 `annual`, 기본 standard |
| report_year | integer nullable | 연간 전용 보고서의 연도 |
| created_at | timestamptz | 생성 시각, index |

일반 보고서는 주·월·연 선택과 관계없이 `scope=standard`입니다. 연간 전용 메뉴는 `scope=annual`, `report_year`를 사용합니다. 최신 일반 조회는 standard만, 연도별 조회는 해당 annual만 선택합니다. 이력 목록은 두 scope 모두 포함합니다. 주기 갱신은 위젯·기간·표시 날짜를 갱신하지만 생성 ID·생성 시각·AI 분석은 유지합니다.

자동 보존 정리는 새 보고서 생성 후 수행하며 standard의 `created_at`을 KST 기준 cutoff와 비교합니다. 기본 52주, 0은 비활성입니다. SLA·재배포와 연간 전용 보고서에는 이 정리를 적용하지 않습니다.

### jobs

| Column | Type | 설명 |
|--------|------|------|
| job_id | varchar PK | UUID |
| status | varchar | pending, running, done, error |
| report_id | integer nullable | 완료 보고서 ID |
| error | varchar nullable | 실패 또는 취소 메시지 |
| created_at, updated_at | timestamptz | 상태 수명 |

### sites

사이트 기본 정보, 계약 날짜·유형·상태, 고객과 유지보수 담당자의 이름·전화·메일·회사 정보를 nullable column으로 저장합니다. `site_name`은 필수이며 trim/lower expression index가 있습니다.

### deployment_nodes

site_id 외래키와 hostname, role, CPU core/thread, memory/disk 용량, OS, IP, disk 여유·갱신 시각, `pkg_version`을 저장합니다. 사이트 삭제 시 cascade됩니다.

### patch_histories와 visit_histories

패치 이력은 Jira·파일 링크, 일자, 유형, 적용자, 결과, 롤백, 비고를 저장합니다. 방문 이력은 방문 일시, 엔지니어 연락처, 요청과 조치 내용을 저장합니다. 두 테이블 모두 site_id cascade 외래키를 사용합니다.

### access_credentials

사이트와 1:1이며 CLI, Web, DB, VPN별 username, password, IP, port와 note를 저장합니다. `CREDENTIAL_ENCRYPTION_KEY`가 설정되면 repository adapter가 각 문자열을 Fernet으로 암호화한 뒤 저장하고 조회 시 복호화합니다. 키가 없으면 호환성을 위해 평문 저장되므로 운영 환경에서는 반드시 키를 설정해야 합니다.

### sla_violation_reports

주간·월간·연간 SLA 위반 보고서의 `period`, `selected_date`, `start_date`, `end_date`, `generated_at`, `generated_by`, `ticket_count`, `initial_response_count`, `resolution_count`와 티켓 상세·데이터 경고를 담은 `payload` JSONB를 저장합니다. `0017_add_sla_violation_reports.py`로 생성하고 최신 보고서는 생성 시각·ID 내림차순으로 선택합니다. 일반 보고서와 독립된 불변 스냅샷이며 상세 이력은 [SLA 위반 보고서 문서](08_sla_violation_report.md)에 정리했습니다.

티켓의 `sla_cycles`는 최초응답·해결 SLA의 완료 및 진행 주기를 각각 저장합니다. 위반 주기만 담는 `breaches`와 달리 정상 주기도 포함하므로 한 SLA만 위반한 티켓에서도 두 SLA의 목표를 비교할 수 있습니다. 반복 주기는 합산하거나 최근 하나로 덮어쓰지 않습니다.

| 주기 필드 | 값과 의미 |
|---|---|
| `metric` | `initial_response` 또는 `resolution` |
| `breached`, `ongoing` | 위반 여부와 현재 진행 주기 여부 |
| `paused` | Jira의 일시정지 여부; 확인되지 않으면 null |
| `goal_ms`, `elapsed_ms`, `exceeded_ms` | Jira SLA 기준 목표·경과·초과 시간의 밀리초 정수; 확인되지 않으면 null |
| `started_at`, `stopped_at` | 주기 시작·완료 시각; 시간대를 포함한 ISO 8601 문자열 또는 null |
| `breached_at`, `status` | 실제 위반 시각과 당시 상태; 미위반 또는 확인되지 않은 값은 null |

초과 시간은 동일 주기의 Jira 목표·경과·잔여 시간으로 검증하며 상태별 체류시간이나 보고서 생성 시각으로 대신 계산하지 않습니다. 주기의 목표는 해당 티켓에 Jira가 적용한 값이며 고객사 계약 등급을 별도로 추정하지 않습니다. 저장하지 않았던 과거 `sla_cycles`는 null로 읽습니다. 새로 보고서를 생성해야 시간이 수집되며 기존 이력을 갱신하지 않습니다. 이 JSONB 확장은 별도의 Alembic 마이그레이션을 요구하지 않습니다.

상태별 시간의 `status_durations_basis`는 `resolution_sla` 또는 `wall_clock`입니다. 새 보고서는 Jira 캘린더·정지 상태를 적용하고 SLA 사용 시간과 검증한 `status_durations`를 저장하며, 검증 불가이면 null입니다. `status_duration_calendar`는 같은 배분으로 검증된 캘린더 이름입니다. 필드가 없는 과거 보고서는 `wall_clock`으로 읽고 UI에서 SLA 시간으로 표시하지 않습니다. 재생성으로 새 이력을 만들며 기존 JSONB는 수정하지 않습니다.

### redeployment_reports

| Column | Type | 설명 |
|---|---|---|
| id | integer PK | 저장 ID |
| snapshot_date | date unique | 생성 시각의 KST 날짜 |
| generated_at | timestamptz | 실제 수집 기준 시각 |
| generated_by | varchar | 생성자 |
| payload | jsonb | 기간 시작, 원본 JQL, 티켓·상세 사유·경고 |

같은 날짜 갱신은 upsert로 대체하고 이전 날짜 행은 유지합니다. API는 최신 조회와 갱신만 제공하며 날짜별 이력 조회·삭제 API는 없습니다.

### issue_management_snapshots

프로젝트별 마지막 전체 이슈 목록을 한 행으로 저장합니다. `project_key`는 고유 키, `synced_at`은 마지막 성공한 동기화의 시작 시각, `full_synced_at`은 마지막 전체 수집의 시작 시각이며 모두 시간대가 있는 timestamp입니다. `payload.issues`는 화면에 필요한 필드와 원본 생성 시각, 사용자 계정 ID 및 개인정보 조회 시각을 포함합니다. 더 오래된 동기화 결과는 최신 저장본을 덮어쓰지 않습니다.

앱 시작 시 저장본을 복원하고 조회 요청에는 즉시 반환합니다. 30초 간격으로 필요한 변경분을 백그라운드 수집하며 마지막 전체 수집 후 1시간이 지났으면 전체 목록을 대조합니다. 갱신 중이나 실패 시 마지막 성공 목록을 유지합니다. 최초 설치처럼 저장본이 없는 경우에만 첫 전체 수집을 기다립니다. 저장본은 개인정보 보고·삭제 대상에 포함되며 저장과 복원 시 삭제된 계정 이름을 다시 표시하지 않습니다.

### 개인정보 보고 데이터

`personal_data_accounts`는 Jira 계정 ID를 기본키로 서버 표시 이름, 해당 프로필을 실제 조회한 `profile_retrieved_at`, 가장 오래된 보유 데이터 조회 시각, 마지막·다음 보고 시각, 프로필 버전과 갱신·삭제 상태를 저장합니다. `personal_data_reporting_grants`는 앱 소유자의 암호화된 refresh token, 다음 재시도 시각과 마지막 보고 성공·오류를 저장합니다. 직원 OAuth 토큰은 이 테이블에 저장하지 않습니다.

보고서 JSON에는 사용자 필드별 `*_account_id`, 기본 조회 시각 `personal_data_retrieved_at`과 필드별 조회 시각 `personal_data_field_retrieved_at`을 저장하며 기존 화면 집계는 유지합니다. Atlassian의 `updated` 응답은 Jira에서 최신 이름을 다시 조회해 해당 사용자 필드와 조회 시각만 갱신하고, `closed` 응답은 이름을 삭제 표시로 바꿉니다. 자세한 처리 범위와 이력 보완은 [Jira 로그인](11_jira_login.md)을 참고하세요.

### sla_status_snapshots

프로젝트별 SLA 위반 임박 현황의 마지막 성공 결과를 한 행으로 저장합니다. `project_key`는 고유 키, `generated_at`은 실제 수집 시각이며 `payload` JSONB에 티켓·SLA 값·상태별 체류시간·개인정보 수집 메타데이터를 보관합니다. 더 오래된 결과는 최신 저장본을 덮어쓰지 않습니다. 최초 조회에서 복원하고 기존 결과를 즉시 반환하면서 필요한 갱신을 백그라운드로 실행합니다. 갱신 실패 시 마지막 저장본을 유지하며 저장·복원에 개인정보 처리 잠금과 최신 프로필 반영을 적용합니다. 자세한 동작은 [SLA 현황](15_sla_status.md)을 참고하세요.

### DB 밖의 데이터

파일 보관함은 `storage_data`, 감사로그는 `audit_logs` 볼륨에 저장합니다. Jira 조회 캐시는 프로세스 메모리, 화면의 테마·열 너비·정렬은 브라우저 localStorage입니다. PostgreSQL 백업만으로 이 데이터가 함께 보존되지는 않습니다. 전체 이슈의 마지막 저장본은 DB 백업에 포함됩니다.

## Domain aggregate

`Site`는 `DeploymentNode`, `PatchHistory`, `VisitHistory`, `AccessCredentials`를 소유합니다. 하위 dataclass는 frozen이며 Application 유스케이스가 새 값으로 교체한 뒤 aggregate를 저장합니다. ORM relationship은 `delete-orphan` cascade로 aggregate 저장 정책을 구현합니다.

`Report`는 `WidgetResult` map과 선택적 `AiAnalysis`를 가집니다. JSONB 변환은 `widget_serializer.py` adapter의 책임이고 Domain 모델은 JSONB나 SQLAlchemy를 알지 못합니다.

widget ID는 영속성 계약으로 유지합니다. `0013_reorder_dashboard_widget_ids.py`는 기존 보고서 JSONB의 이전 키를 새 순번으로 변환합니다. 화면에서는 월별 해결시간 SLA 다음에 평균 소요 시간 그래프 두 개를 표시하며, 두 그래프는 `w14` 데이터를 공유합니다. `w15`는 연간 전용 재배포 품질 집계이며 독립 재배포 현황의 `redeployment_reports`와 다른 데이터입니다.

### 평균 소요 시간

`w14.stage_issues`는 해결된 이슈별 key, 업무 유형, 현재 상태, 해결일, 상태별 체류 시간 합계(`by_stage_hours`)를 저장합니다. Jira 상태 변경 이력은 모든 페이지를 수집하며, 생성일부터 최종 해결일까지의 상태 구간을 계산합니다. 같은 상태로 재진입하면 해당 이슈의 체류 시간을 합산합니다. 그래프의 평균은 각 상태에 실제로 머문 이슈의 합산 시간 평균이며, 근무시간 달력이나 SLA 일시정지 규칙을 적용하지 않은 경과시간입니다.

화면의 기간·업무 유형·현재 상태 필터를 이슈별 집계에 적용합니다. 기간은 해결일 기준이며, 선택 기간에 해결된 이슈의 전체 처리 이력을 사용합니다. 요청 분류별 평균은 기존 `w14.by_type` 및 반기·현재 상태별 집계를 사용해 생성부터 해결까지의 시간을 표시합니다.

`stage_issues`가 없는 기존 보고서는 이력 미수집 안내를 표시합니다. 재수집하면 새 필드가 저장되며 JSONB에 대한 스키마 마이그레이션은 필요하지 않습니다. 이력 요청은 최대 5개씩 병렬 실행합니다. 일반 수집에서는 이력 캐시를 5분간 사용하고, 수동 새로고침은 이를 우회합니다. Jira 요청 실패나 잘린 페이지는 전파하여 정상 집계로 저장하지 않습니다. 개별 티켓의 잘못된 날짜·연결이 끊긴 상태 이력은 `ValueError`로 분리해 그 티켓의 `stage_issues`만 제외하고 키와 원인을 로그에 남깁니다. 유형별 평균과 정상 이슈는 유지하며, 이 경우 단계별 평균의 표본 수가 전체 해결 건수보다 작을 수 있습니다.

## Migration

마이그레이션은 `backend/alembic/versions`에 있으며 현재 head는 `0022`입니다. `0014`는 annual scope, `0017`은 SLA, `0018`은 재배포, `0019`는 개인정보 보고 계정·소유자 연결 테이블, `0020`은 전체 이슈의 마지막 저장본, `0021`은 SLA 현황의 마지막 저장본, `0022`는 개인정보 프로필 조회 시각을 추가합니다. Docker backend entrypoint는 서버 시작 전에 head까지 적용합니다. 백업·배포 절차는 [운영 가이드](10_operations.md)를 참고하세요.

`0016_remove_c_level_reports.py`는 제거된 C-Level 기능의 `c_level_comments`, `c_level_snapshots` 테이블과 저장된 데이터를 삭제합니다. 기존 DB의 revision을 인식할 수 있도록 `0015` 생성 이력은 유지합니다. `0016`을 downgrade하면 빈 테이블 구조만 복원되며 삭제된 데이터는 복구되지 않습니다. 기존 보고서·사이트·파일 데이터와 감사로그는 유지합니다.

```bash
cd backend
alembic upgrade head
```
