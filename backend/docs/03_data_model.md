# Data Model

PostgreSQL과 SQLAlchemy async ORM을 사용합니다. 영속성 모델은 `src/infrastructure/persistence`, 프레임워크 독립 모델은 `src/domain`에 있습니다.

## Tables

### reports

| Column | Type | 설명 |
|--------|------|------|
| id | integer PK | 자동 증가 ID |
| week_start, week_end | date | 보고 범위 |
| report_date | varchar | 표시용 보고서 날짜 |
| widgets | jsonb | widget serializer 결과 |
| ai_analysis | jsonb nullable | AI 요약, 위험, 권고, sentiment |
| created_at | timestamptz | 생성 시각, index |

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

## Domain aggregate

`Site`는 `DeploymentNode`, `PatchHistory`, `VisitHistory`, `AccessCredentials`를 소유합니다. 하위 dataclass는 frozen이며 Application 유스케이스가 새 값으로 교체한 뒤 aggregate를 저장합니다. ORM relationship은 `delete-orphan` cascade로 aggregate 저장 정책을 구현합니다.

`Report`는 `WidgetResult` map과 선택적 `AiAnalysis`를 가집니다. JSONB 변환은 `widget_serializer.py` adapter의 책임이고 Domain 모델은 JSONB나 SQLAlchemy를 알지 못합니다.

widget ID는 대시보드에서 처음 렌더링되는 순서인 연간 생성·해결, 기간 생성·해결, 진행 상태, 최근 이슈, 월별 현황, 월별 SLA, 분석 차트 순으로 w1부터 w14까지 부여합니다. `0013_reorder_dashboard_widget_ids.py`는 기존 보고서 JSONB의 이전 키를 새 순번으로 변환합니다.

## Migration

마이그레이션은 `backend/alembic/versions`에 있습니다.

```bash
cd backend
alembic upgrade head
```
