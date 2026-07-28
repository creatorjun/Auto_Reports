# Auto Reports — 전체 컨텍스트 문서 (v2026.07.29)

레포지토리 최신 커밋 기준(`32cf216`) 실제 코드를 완전 탐색한 결과입니다.  
다른 세션에서 이 문서만 붙여넣으면 즉시 작업을 이어갈 수 있습니다.

---

## 1. 프로젝트 핵심 정보

| 항목 | 값 |
|---|---|
| 레포지토리 | [creatorjun/Auto_Reports](https://github.com/creatorjun/Auto_Reports) |
| 최신 커밋 | `32cf216` |
| 브랜치 | `main` 단일 직접 커밋 |
| 백엔드 엔트리 | `backend/src/main.py` |
| API prefix | `/api/v1` |
| 프레임워크 | FastAPI (Python) + React (TypeScript) |
| DB | PostgreSQL (asyncpg + SQLAlchemy async) |
| 컨테이너 | docker-compose.yml |

---

## 2. 실제 디렉터리 구조 (탐색 확인본)

```
Auto_Reports/
├── .env.example
├── .gitignore
├── Makefile
├── README.md
├── docker-compose.yml
├── summary.md                          ← 이 문서
├── docs/
├── backend/
│   └── src/
│       ├── main.py                     ← FastAPI 앱 엔트리, lifespan DI 배선
│       ├── shared/
│       │   └── audit_logger.py
│       ├── config/
│       ├── domain/
│       │   ├── entities/
│       │   │   ├── job.py
│       │   │   ├── report.py           ← NewReport dataclass
│       │   │   ├── site.py             ← Site 엔티티 + ContractType StrEnum
│       │   │   ├── widget.py           ← WidgetResult<T>
│       │   │   └── widget_data.py      ← 모든 위젯 데이터 dataclass
│       │   ├── ports/
│       │   │   ├── jira_port.py
│       │   │   └── ai_port.py
│       │   ├── repositories/
│       │   │   ├── job_repository.py
│       │   │   ├── report_repository.py
│       │   │   └── site_repository.py
│       │   └── value_objects/
│       │       └── widget_id.py        ← WidgetId StrEnum (w1~w14)
│       ├── application/
│       │   ├── ports/
│       │   │   ├── job_runner_port.py
│       │   │   └── report_cache_port.py ← get_or_revalidate() SWR 패턴
│       │   ├── mappers/
│       │   ├── scheduler/
│       │   │   └── report_scheduler.py
│       │   ├── services/
│       │   │   ├── ai_analyzer.py
│       │   │   ├── query_builder.py    ← ResolvedQueries (w1~w14 JQL)
│       │   │   ├── query_config.py     ← QueryConfig DTO
│       │   │   └── report_assembler.py ← asyncio.gather 병렬 수집
│       │   ├── use_cases/
│       │   │   ├── generate_report.py
│       │   │   ├── get_report.py
│       │   │   ├── site_use_cases.py
│       │   │   └── storage_use_case.py
│       │   └── widgets/
│       │       ├── base.py
│       │       ├── collector_factory.py
│       │       ├── count_collector.py
│       │       ├── created_vs_resolved_collector.py
│       │       ├── monthly_collector.py
│       │       ├── monthly_count_collector.py
│       │       ├── recent_collector.py
│       │       ├── resolution_collector.py
│       │       └── sla_delay_collector.py
│       ├── infrastructure/
│       │   ├── container.py            ← DI 배선 중심
│       │   ├── job_runner.py
│       │   ├── report_cache.py         ← ReportLruCache + SWR 백그라운드 갱신
│       │   ├── config/
│       │   │   └── settings.py
│       │   ├── external/
│       │   │   ├── jira_client.py      ← get_issue_counts_batch() + _count_cache
│       │   │   └── gemini_client.py
│       │   ├── persistence/
│       │   │   ├── database.py
│       │   │   ├── models.py
│       │   │   ├── site_models.py      ← Site SQLAlchemy ORM 모델
│       │   │   ├── site_repository_impl.py
│       │   │   ├── report_repository_impl.py
│       │   │   ├── job_repository_impl.py
│       │   │   └── widget_serializer.py
│       │   ├── security/
│       │   └── storage/
│       │       └── local_storage.py
│       └── presentation/
│           ├── api/v1/
│           │   ├── router.py           ← _protected APIRouter (인증 강제)
│           │   ├── auth.py
│           │   ├── reports.py
│           │   ├── trigger.py          ← SSE 스트림 엔드포인트
│           │   ├── sites.py            ← Site CRUD (20KB)
│           │   ├── storage.py          ← Chunked 업로드 API
│           │   ├── search.py
│           │   ├── config.py
│           │   └── deps.py
│           └── schemas/
│               ├── site_schema.py      ← SiteCreateRequest / SiteUpdateRequest / SiteResponse
│               └── report_schema.py
│
└── frontend/
    └── src/
        ├── main.tsx
        ├── app/
        │   ├── App.tsx
        │   ├── router.tsx              ← 모든 페이지 lazy() Suspense
        │   ├── context/
        │   └── store/
        ├── domain/                     ← TypeScript 도메인 타입
        │   ├── Config.ts
        │   ├── Issue.ts
        │   ├── Job.ts
        │   ├── Report.ts
        │   ├── Site.ts                 ← Site / ContractType 타입
        │   └── Storage.ts
        ├── infrastructure/
        │   ├── api/
        │   │   ├── client.ts           ← axios 인스턴스 + 인터셉터
        │   │   ├── authApi.ts
        │   │   ├── reportApi.ts
        │   │   ├── siteApi.ts
        │   │   ├── searchApi.ts
        │   │   └── storageApi.ts
        │   └── hooks/
        └── presentation/
            ├── pages/
            │   ├── DashboardPage.tsx   ← 차트 7개 + 모달 lazy()
            │   ├── HistoryPage.tsx
            │   ├── LoginPage.tsx
            │   ├── SiteManagementPage.tsx
            │   ├── SiteCreatePage.tsx  ← 사이트 생성/수정 (라이센스 드롭다운)
            │   ├── SiteDetailPage.tsx  ← 사이트 상세 (라이센스 유형 표시)
            │   ├── StoragePage.tsx
            │   └── StoragePreviewPage.tsx
            └── components/
                ├── auth/
                ├── cards/
                ├── charts/
                ├── common/
                ├── layout/
                │   ├── Header.tsx
                │   ├── Layout.tsx
                │   ├── MobileTabBar.tsx
                │   └── Sidebar.tsx
                ├── storage/
                └── tables/
```

---

## 3. Site 엔티티 — 현재 스펙

### 3-1. ContractType StrEnum (backend)

```python
# backend/src/domain/entities/site.py
class ContractType(StrEnum):
    OFFICIAL  = "정식라이센스"
    TEMPORARY = "임시라이센스"
```

### 3-2. Site 엔티티 주요 필드

```python
class Site:
    id: UUID
    name: str                       # 사이트명
    jira_project_key: str           # Jira 프로젝트 키
    contract_type: ContractType     # 정식라이센스 | 임시라이센스
    # ... (담당자, 연락처, 기타 설정 필드)
    created_at: datetime
    updated_at: datetime
```

### 3-3. Pydantic 스키마 (site_schema.py)

```python
class SiteCreateRequest(BaseModel):
    contract_type: ContractType     # 정식라이센스 | 임시라이센스
    # ...

class SiteUpdateRequest(BaseModel):
    contract_type: ContractType | None = None
    # ...

class SiteResponse(BaseModel):
    contract_type: ContractType
    # ...
```

### 3-4. 프론트엔드 타입 & UI (Site.ts / SiteCreatePage.tsx)

```typescript
// frontend/src/domain/Site.ts
export type ContractType = '정식라이센스' | '임시라이센스'

// SiteCreatePage.tsx — Zod 검증
const schema = z.object({
  contract_type: z.enum(['정식라이센스', '임시라이센스']).optional(),
  // ...
})

// 드롭다운 UI
<label>라이센스 (선택)</label>
<select>
  <option value="">선택 안함</option>
  <option value="정식라이센스">정식라이센스</option>
  <option value="임시라이센스">임시라이센스</option>
</select>

// SiteDetailPage.tsx — 상세 표시
<Row label="라이센스 유형" value={site.contract_type} />
```

---

## 4. WidgetId enum (widget_id.py)

```python
class WidgetId(StrEnum):
    YEARLY_CREATED         = "w1"
    YEARLY_RESOLVED        = "w2"
    CREATED_VS_RESOLVED    = "w3"
    ISSUE_REVIEW           = "w4"
    DATA_REQUEST           = "w5"
    RESULT_PENDING         = "w6"
    SLA_INITIAL_RESPONSE   = "w7"   # MonthlyCollector → SLA 초기 응답
    SLA_RESOLUTION_MONTHLY = "w8"   # MonthlyCollector → SLA 해결 월별
    SLA_MET_VS_VIOLATED    = "w9"
    SLA_DELAY_REASON       = "w10"
    AVG_RESOLUTION_TYPE    = "w11"
    RECENT_ISSUES          = "w12"
    MONTHLY_CREATED        = "w13"  # MonthlyCountCollector
    MONTHLY_RESOLVED       = "w14"  # MonthlyCountCollector
```

> ⚠️ w7/w8 = SLA 월별, w13/w14 = 생성/해결 월별 카운트 (서로 다른 Collector 사용)

---

## 5. Settings — 실제 필드 목록 (settings.py)

```python
# Jira
jira_base_url, jira_email, jira_api_token
sla_initial_response_field_id = "customfield_12152"
sla_resolution_field_id       = "customfield_12151"
jira_tac_assignee_field_id    = "customfield_10859"
jira_qa_assignee_field_id     = "customfield_12222"
project_key = "TACEA"

# DB
db_user, db_password, db_host, db_name
# database_url property: postgresql+asyncpg://...

# 스케줄
schedule_cron = "0 23 * * 5"    # 매주 금요일 23시 KST
tz = "Asia/Seoul"

# AI
gemini_api_key, ai_enabled = True

# 인증 (환경변수 alias 주의)
login: bool           alias="LOGIN"
admin_username: str   alias="ADMIN"
admin_password: str   alias="ADMIN_PASSWORD"
jwt_secret: str       alias="JWT_SECRET"
jwt_access_expire_minutes = 30
jwt_refresh_expire_days   = 7

# 스토리지
storage_dir = "/app/storage"

# 보존 정책
retention_weeks: int = 12

# 이슈 분류
issue_types     = ["인시던트", "개선", "CVE", "서비스 요청"]
active_statuses = [...]
closed_statuses = ["Closed", "반려됨", "중복 이슈", "취소됨"]
```

---

## 6. API 라우터 구조

```python
# router.py — /api/v1 prefix
router.include_router(auth.router)           # 인증 불필요
router.include_router(preview_router)        # storage preview만 공개

_protected = APIRouter(dependencies=[Depends(require_auth)])
_protected.include_router(reports.router)
_protected.include_router(trigger.router)    # SSE 스트림 엔드포인트
_protected.include_router(sites.router)      # Site CRUD
_protected.include_router(config.router)
_protected.include_router(search.router)
_protected.include_router(storage.router)    # 인증 보호
```

### API 엔드포인트 목록

| 라우터 | 주요 엔드포인트 |
|---|---|
| auth | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout` |
| reports | `GET /reports`, `GET /reports/{id}`, `POST /reports` |
| trigger | `POST /trigger`, `GET /trigger/{job_id}/stream` (SSE) |
| sites | `GET /sites`, `POST /sites`, `GET /sites/{id}`, `PUT /sites/{id}`, `DELETE /sites/{id}` |
| storage | `GET /storage/files`, `POST /storage/upload`, chunked upload init/chunk/complete/abort |
| search | `GET /search` |
| config | `GET /config` |

---

## 7. 라우팅 — 실제 페이지 경로

| 경로 | 컴포넌트 | 인증 |
|---|---|---|
| `/login` | LoginPage | ❌ |
| `/` | DashboardPage | ✅ |
| `/history` | HistoryPage | ✅ |
| `/reports/:id` | DashboardPage | ✅ |
| `/storage` | StoragePage | ✅ |
| `/storage/preview` | StoragePreviewPage | ✅ |
| `/sites` | SiteManagementPage | ✅ |
| `/sites/new` | SiteCreatePage | ✅ |
| `/sites/:id` | SiteDetailPage | ✅ |
| `/sites/:id/edit` | SiteCreatePage | ✅ |

---

## 8. 프론트엔드 도메인 타입 (Report.ts)

```typescript
interface WidgetResult {
  name: string
  total: number
  jql: string
  data: Record<string, unknown> | null
}

interface ReportDetail extends ReportSummary {
  widgets: Record<string, WidgetResult>  // key = "w1"~"w14"
  ai_analysis: AiAnalysis | null
}
```

---

## 9. Container.py — DI 배선

### base_collector_factory

| WidgetId | Collector | JQL 메서드 |
|---|---|---|
| YEARLY_CREATED | SimpleCountCollector | `w1_yearly_created()` |
| YEARLY_RESOLVED | SimpleCountCollector | `w2_yearly_resolved()` |
| CREATED_VS_RESOLVED | CreatedVsResolvedCollector | `w3_created_vs_resolved()` |
| ISSUE_REVIEW | SimpleWithDetailsCollector | `w4_issue_review()` |
| DATA_REQUEST | SimpleWithDetailsCollector | `w5_data_request()` |
| RESULT_PENDING | SimpleWithDetailsCollector | `w6_result_pending()` |
| SLA_MET_VS_VIOLATED | SlaMetVsViolatedCollector | `w9_sla()` |
| SLA_DELAY_REASON | SlaDelayCollector | 내부 구성 |
| AVG_RESOLUTION_TYPE | ResolutionCollector | `w11_resolution_resolved()` |
| RECENT_ISSUES | RecentCollector | `w12_recent()` |

### monthly_collector_factory

| WidgetId | Collector | 반환 |
|---|---|---|
| SLA_INITIAL_RESPONSE | MonthlyCollector | tuple → (w7, w8) |
| MONTHLY_CREATED | MonthlyCountCollector | tuple → (w13, w14) |

---

## 10. 주요 아키텍처 패턴

### 10-1. Background Refresh / SWR

```python
# report_cache_port.py
class ReportCachePort(ABC):
    async def get_or_revalidate(self, key, ttl, revalidate_fn) -> T:
        # 캐시 HIT → 즉시 반환 + 백그라운드 갱신 트리거
        # 캐시 MISS → revalidate_fn() 결과 저장 후 반환

# report_cache.py
class ReportLruCache(ReportCachePort):
    maxsize = 50
    ttl = 600s  # stale 구간에서 asyncio.create_task()로 갱신
```

### 10-2. SSE + Exponential Backoff 폴링

```python
# trigger.py — 신규 엔드포인트
GET /api/v1/trigger/{job_id}/stream
# → StreamingResponse, text/event-stream
# 이벤트: status(pending/running), done(완료), timeout(15s keepalive)
# 헤더: X-Accel-Buffering: no
```

```typescript
// useJobStream.ts — 클라이언트 전략
// 1순위: EventSource (SSE) — 단일 HTTP 커넥션 유지
// 2순위: EB 폴링 폴백 — delay = min(1000 * 2^n, 16000) * jitter(±20%)
```

### 10-3. Jira N+1 해결

```python
class JiraClient:
    _count_cache: dict[str, int]           # 요청 내 JQL 결과 캐시
    _count_locks: dict[str, asyncio.Lock]  # 동시 중복 요청 차단

    async def get_issue_counts_batch(self, jqls: list[str]) -> list[int]:
        """N개 JQL을 asyncio.gather 1회로 처리, 캐시 재사용"""
```

### 10-4. 히스토리 보존

```python
# settings.py
retention_weeks: int = 12   # 기본 12주 보존

# report_repository_impl.py
async def cleanup_old_reports(self, retention_weeks: int) -> int:
    """retention_weeks 이전 보고서 자동 삭제"""
```

### 10-5. Chunked 업로드 (storage.py)

```
POST /storage/upload/init    → upload_id 발급
POST /storage/upload/chunk   → 청크 전송
POST /storage/upload/complete → 병합 완료
DELETE /storage/upload/abort  → 업로드 취소
```

---

## 11. 번들 청크 분리 현황 (Lazy Load)

| 청크 | 적용 대상 |
|---|---|
| 차트 (7개) | 첫 렌더 시 개별 요청 |
| 테이블 모달 (8개) | 카드 클릭 시 개별 요청 |
| GenerateReportModal | 버튼 클릭 시 요청 |
| 페이지 전체 | router.tsx에서 모든 페이지 lazy() |

---

## 12. 주요 설계 결정 & 주의사항

| 항목 | 실제 결정 | 비고 |
|---|---|---|
| API prefix | `/api/v1` | main.py에서 마운트 |
| Storage 인증 | **보호됨** (preview만 공개) | router.py |
| 계약 유형 필드명 | `contract_type` | DB 컬럼명 동일 (String 타입) |
| 라이센스 값 | `정식라이센스` / `임시라이센스` | ContractType StrEnum |
| 라이센스 라벨 | 생성/수정: "라이센스 (선택)", 상세: "라이센스 유형" | SiteCreatePage / SiteDetailPage |
| 월별 수집 | MonthlyCollector → tuple(w7, w8) | assembler에서 언패킹 |
| w13/w14 | MonthlyCountCollector → tuple | 동일 패턴 |
| 캐시 | ReportLruCache(maxsize=50, ttl=600s) + SWR | |
| DB 보존 | retention_weeks=12 (기본) | |
| SLA 필드 탐지 | `schema.type == "sd-servicelevelagreement"` | 자동 탐지 |
| Storage quota | `STORAGE_LIMIT_BYTES = 2TB` | storage.py |
| 해결일시 | `updated` 필드 사용 | `resolutiondate` null 대응 |

---

## 13. 새 기능 추가 체크리스트

### 새 위젯(wN) 추가 순서

```
1. widget_id.py              → WidgetId enum에 wN 추가
2. widget_data.py            → 데이터 dataclass 추가
3. widgets/xxx_collector.py  → AbstractWidgetCollector 구현
4. query_builder.py          → ResolvedQueries에 wN_xxx() JQL 추가
5. container.py              → _base_collector_factory 또는
                                _monthly_collector_factory에 CollectorEntry 추가
6. report_assembler.py       → monthly tuple 언패킹 로직 수정 필요 시
7. presentation/schemas/     → Pydantic 스키마 추가
8. frontend/domain/          → TypeScript 타입 추가
9. infrastructure/api/       → API 호출 추가
10. infrastructure/hooks/    → useXxx 훅 추가
11. presentation/pages/      → 컴포넌트 연결 + lazy() 래핑
```

### 새 모달 추가 순서

```
1. tables/XxxModal.tsx 생성
   - props: { isOpen, onClose, issues: XxxDetail[] }
   - ESC: useEffect + keydown
   - 배경클릭: e.target === e.currentTarget
   - 행클릭: window.open(`${jiraBase}/${issue.key}`, '_blank', 'noreferrer')
2. DashboardPage.tsx에서 lazy() + Suspense fallback={<ModalFallback />}로 등록
3. showXxx state + SummaryCard onClick 연결
```

### 새 Site 필드 추가 순서

```
1. domain/entities/site.py          → Site dataclass 필드 추가
2. infrastructure/persistence/
   └── site_models.py               → SQLAlchemy 컬럼 추가
   └── site_repository_impl.py      → 쿼리 로직 반영
3. presentation/schemas/site_schema.py → Pydantic 스키마 추가
4. frontend/src/domain/Site.ts      → TypeScript 타입 추가
5. frontend/src/infrastructure/api/siteApi.ts → 필요 시 파라미터 추가
6. frontend/src/presentation/pages/
   └── SiteCreatePage.tsx           → 입력 필드 추가
   └── SiteDetailPage.tsx           → 표시 Row 추가
```
