# backend/docs/03_data_model.md

# Data Model

## 데이터베이스: PostgreSQL (asyncpg)

---

## ORM 모델 (`src/infrastructure/persistence/`)

### reports 테이블

```sql
CREATE TABLE reports (
    id          SERIAL PRIMARY KEY,
    week_start  DATE NOT NULL,
    week_end    DATE NOT NULL,
    report_date VARCHAR NOT NULL,
    widgets     JSONB NOT NULL,
    ai_analysis JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_reports_created_at ON reports (created_at);
```

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | 자동 증가 ID |
| week_start | DATE | 보고서 대상 주의 시작일 |
| week_end | DATE | 보고서 대상 주의 종료일 |
| report_date | VARCHAR | 보고서 생성일 문자열 (표시용) |
| widgets | JSONB | 위젯 데이터 직렬화 (widget_serializer.py 참조) |
| ai_analysis | JSONB | Gemini AI 분석 결과 (nullable) |
| created_at | TIMESTAMPTZ | 생성 시각 (인덱스됨) |

---

### jobs 테이블

```sql
CREATE TABLE jobs (
    job_id     VARCHAR PRIMARY KEY,
    status     VARCHAR NOT NULL,
    report_id  INTEGER,
    error      VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| 컬럼 | 타입 | 설명 |
|------|------|------|
| job_id | VARCHAR PK | UUID 문자열 |
| status | VARCHAR | pending / running / done / error |
| report_id | INTEGER | 완료 시 연결된 reports.id (nullable) |
| error | VARCHAR | 오류 메시지 (nullable) |
| created_at | TIMESTAMPTZ | 잡 생성 시각 |
| updated_at | TIMESTAMPTZ | 마지막 상태 변경 시각 |

---

### sites 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| site_name | VARCHAR NOT NULL | 사이트명 |
| maintenance_company | VARCHAR | 유지보수 회사명 |
| customer_contact | JSONB | 고객 담당자 (ContactInfo) |
| maintenance_contact | JSONB | 유지보수 담당자 (ContactInfo) |
| contract_start_date | DATE | 계약 시작일 |
| contract_end_date | DATE | 계약 종료일 |
| contract_type | VARCHAR | 계약 유형 Enum |
| status | VARCHAR | 사이트 상태 Enum |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

---

### deployment_nodes 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| site_id | INTEGER FK → sites.id | |
| hostname | VARCHAR NOT NULL | |
| role | VARCHAR | NodeRole Enum (master/worker/db/etc.) |
| cpu_cores | INTEGER | |
| cpu_threads | INTEGER | |
| memory_total_gb | FLOAT | |
| disk_total_gb | FLOAT | |
| os_type | VARCHAR | |
| os_version | VARCHAR | |
| ip_address | VARCHAR | |
| disk_free_gb | FLOAT | |
| disk_updated_at | TIMESTAMPTZ | 디스크 정보 마지막 수집 시각 |

---

### patch_histories 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| site_id | INTEGER FK → sites.id | |
| issue_link | VARCHAR | Jira 이슈 링크 |
| patch_date | DATE | 패치 적용일 |
| patch_file_link | VARCHAR | 패치 파일 링크 |
| patch_type | VARCHAR | PatchType Enum |
| applied_by | VARCHAR | 적용자 |
| result_status | VARCHAR | ResultStatus Enum |
| rollback_date | DATE | 롤백일 (nullable) |
| note | TEXT | 비고 |

---

### visit_histories 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| site_id | INTEGER FK → sites.id | |
| visit_datetime | TIMESTAMPTZ | 방문 일시 |
| engineer_name | VARCHAR | 엔지니어 이름 |
| engineer_phone | VARCHAR | 엔지니어 연락처 |
| request_content | TEXT | 요청 내용 |
| action_content | TEXT | 조치 내용 |

---

## 도메인 엔티티 구조 (Domain Entities)

### Site

```python
@dataclass
class Site:
    id: int | None
    site_name: str
    maintenance_company: str | None
    customer_contact: ContactInfo | None
    maintenance_contact: ContactInfo | None
    contract_start_date: date | None
    contract_end_date: date | None
    contract_type: ContractType | None
    status: SiteStatus | None
    nodes: list[DeploymentNode]
    patch_histories: list[PatchHistory]
    visit_histories: list[VisitHistory]
    access_credentials: AccessCredentials | None
    created_at: datetime | None
    updated_at: datetime | None
```

### AccessCredentials

```python
@dataclass
class AccessCredentials:
    cli: Credential | None   # SSH 접속 정보
    web: Credential | None   # 웹 관리 콘솔
    db: Credential | None    # 데이터베이스
    vpn: Credential | None   # VPN
    note: str | None

@dataclass
class Credential:
    username: str | None
    password: str | None
    ip: str | None
    port: int | None
```

**주의**: `access_credentials`는 DB에 암호화 없이 JSONB로 저장됩니다.  
운영 환경에서는 반드시 DB 암호화 또는 별도 시크릿 관리 도입을 권장합니다.

---

## JSONB 위젯 데이터 구조 (widgets 컬럼)

`widget_serializer.py`가 담당하며 아래 키를 가진 딕셔너리로 직렬화됩니다.

```json
{
  "count": { ... },
  "created_vs_resolved": { ... },
  "monthly": { ... },
  "monthly_count": { ... },
  "recent": { ... },
  "resolution": { ... },
  "sla_delay": { ... }
}
```

---

## Alembic 마이그레이션

마이그레이션 파일은 `backend/alembic/versions/`에 위치합니다.  
새 모델 변경 시:

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```
