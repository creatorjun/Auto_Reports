# Auto Reports — 전체 컨텍스트 문서 (v2026.07.12-r2)

레포지토리 최신 커밋 기준(`65b11e1`) 실제 코드를 완전 탐색한 결과입니다.  
다른 세션에서 이 문서만 붙여넣으면 즉시 작업을 이어갈 수 있습니다.

---

## 1. 프로젝트 핵심 정보

| 항목 | 값 |
|---|---|
| 레포지토리 | [creatorjun/Auto_Reports](https://github.com/creatorjun/Auto_Reports) |
| 최신 커밋 | `65b11e1` |
| 브랜치 | `main` 단일 직접 커밋 |
| 백엔드 엔트리 | `backend/src/main.py` |
| API prefix | `/api/v1` (router.py 기준) |

---

## 2. 오늘(2026-07-12) 반영된 커밋 전체 목록

| 커밋 SHA | 메시지 | 분류 |
|---|---|---|
| [`65b11e1`](https://github.com/creatorjun/Auto_Reports/commit/65b11e11a23dca791825987697a8d4befefd468e) | fix: TriggerButton collapsed prop 복원 — TS2322 빌드 에러 해결 | 버그픽스 |
| [`7fd3683`](https://github.com/creatorjun/Auto_Reports/commit/7fd368320c536438029ad853a027b25b2bcdb5bf) | perf: 모달 Lazy Load 적용으로 초기 번들 크기 감소 | 성능 |
| [`631888d`](https://github.com/creatorjun/Auto_Reports/commit/631888d41b3eb19ca3469bc502b7e007b11db6e8) | feat: SSE + Exponential Backoff 폴링으로 API 요청 70% 감소 | 기능 |
| [`6b9e0dd`](https://github.com/creatorjun/Auto_Reports/commit/6b9e0dd4c2c2f0b760359c6a4ef46b7b2797aefa) | feat: DB 보고서 히스토리 보존 정략 로직 추가 (retention_weeks 기반) | 기능 |
| [`cf0d6e9`](https://github.com/creatorjun/Auto_Reports/commit/cf0d6e962fe36cfdebba20be4d08b2a56b29d5c0) | feat: Background Refresh 캐시 패턴 구현 (stale-while-revalidate) | 기능 |
| [`af3897c`](https://github.com/creatorjun/Auto_Reports/commit/af3897c21a0607c779710bc8b47c738d8591f508) | fix: Jira N+1 해결 — JQL 배치 평탄화 + 요청 내 캐시 레이어 추가 | 버그픽스 |
| [`7795e5e`](https://github.com/creatorjun/Auto_Reports/commit/7795e5ebb84560539c94129017b400a60145f733) | feat: Chunked 업로드 API 추가 | 기능 |
| [`8c91b01`](https://github.com/creatorjun/Auto_Reports/commit/8c91b010fc32abba3e44b091cedc709e668cbf37) | fix: storage.router → _protected 이동, Storage 인증 누락 수정 | 보안 |

---

## 3. 실제 디렉터리 구조 (탐색 확인본)

```
Auto_Reports/
├── 프로젝트-개요.md                    ← 이 문서
├── backend/src/
│   ├── main.py
│   ├── config/
│   ├── shared/                        ← 공용 상수 (KST 등)
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── job.py
│   │   │   ├── report.py              ← NewReport dataclass
│   │   │   ├── widget.py              ← WidgetResult<T>
│   │   │   └── widget_data.py         ← 모든 위젯 데이터 dataclass
│   │   ├── ports/
│   │   │   ├── jira_port.py           ← get_issue_counts_batch() 추가됨
│   │   │   └── ai_port.py
│   │   ├── repositories/
│   │   └── value_objects/
│   │       └── widget_id.py           ← WidgetId StrEnum
│   ├── application/
│   │   ├── ports/
│   │   │   └── report_cache_port.py   ← get_or_revalidate() 추가됨 (SWR 패턴)
│   │   ├── mappers/
│   │   │   └── job_mapper.py          ← retry_after 힌트 추가됨
│   │   ├── scheduler/
│   │   ├── services/
│   │   │   ├── ai_analyzer.py
│   │   │   ├── query_builder.py       ← ResolvedQueries (w1~w14 JQL)
│   │   │   ├── query_config.py        ← QueryConfig DTO
│   │   │   └── report_assembler.py    ← asyncio.gather 병렬 수집
│   │   ├── use_cases/
│   │   │   ├── generate_report.py
│   │   │   └── get_report.py
│   │   └── widgets/
│   │       ├── base.py
│   │       ├── collector_factory.py
│   │       ├── count_collector.py
│   │       ├── created_vs_resolved_collector.py
│   │       ├── monthly_collector.py
│   │       ├── monthly_count_collector.py  ← 배치 평탄화 적용됨
│   │       ├── recent_collector.py
│   │       ├── resolution_collector.py
│   │       └── sla_delay_collector.py
│   ├── infrastructure/
│   │   ├── container.py
│   │   ├── report_cache.py            ← ReportLruCache + SWR 백그라운드 갱신
│   │   ├── config/
│   │   │   └── settings.py            ← retention_weeks 필드 추가됨
│   │   ├── external/
│   │   │   ├── jira_client.py         ← get_issue_counts_batch() + _count_cache 추가됨
│   │   │   └── gemini_client.py
│   │   └── persistence/
│   │       └── report_repository_impl.py  ← 히스토리 보존 + cleanup_old_reports() 추가됨
│   └── presentation/
│       ├── api/v1/
│       │   ├── router.py              ← storage.router → _protected 이동됨
│       │   ├── auth.py
│       │   ├── reports.py
│       │   ├── trigger.py             ← GET /trigger/{job_id}/stream SSE 엔드포인트 추가됨
│       │   ├── config.py
│       │   ├── search.py
│       │   ├── storage.py             ← Chunked 업로드 API (init/chunk/complete/abort) 추가됨
│       │   └── deps.py
│       └── schemas/
│
└── frontend/src/
    ├── main.tsx
    ├── app/
    │   ├── App.tsx
    │   ├── router.tsx                 ← 모든 페이지 lazy() (기존 유지)
    │   ├── context/
    │   └── store/
    ├── domain/
    │   ├── Config.ts
    │   ├── Issue.ts
    │   ├── Job.ts
    │   ├── Report.ts
    │   └── Storage.ts
    ├── infrastructure/
    │   ├── api/
    │   │   ├── client.ts
    │   │   ├── authApi.ts
    │   │   ├── reportApi.ts           ← getJobStreamUrl() 헬퍼 추가됨
    │   │   ├── searchApi.ts
    │   │   └── storageApi.ts
    │   └── hooks/
    │       ├── useAuth.ts
    │       ├── useConfig.ts
    │       ├── useJobStream.ts         ← 신규: SSE 우선 + EB 폴백
    │       ├── useReport.ts
    │       ├── useStorage.ts
    │       └── useTrigger.ts          ← useJobStream 기반으로 교체됨
    └── presentation/
        ├── pages/
        │   ├── DashboardPage.tsx      ← 차트 7개 + 모달 8개 → lazy() + Suspense
        │   ├── HistoryPage.tsx
        │   ├── LoginPage.tsx
        │   ├── StoragePage.tsx
        │   └── StoragePreviewPage.tsx
        └── components/
            ├── auth/
            ├── cards/
            ├── charts/                ← 7개 모두 lazy() 청크 분리됨
            ├── common/
            │   ├── ErrorBoundary.tsx
            │   ├── GenerateReportModal.tsx
            │   ├── IssueModalShell.tsx
            │   ├── LazyGenerateReportModal.tsx  ← 신규: lazy() 래퍼
            │   ├── LoadingSpinner.tsx
            │   ├── RefreshButton.tsx
            │   ├── SearchWidget.tsx
            │   ├── StatusBadge.tsx
            │   └── TriggerButton.tsx   ← collapsed?: boolean prop 복원됨
            ├── layout/
            │   ├── Header.tsx
            │   ├── Layout.tsx
            │   ├── MobileTabBar.tsx
            │   └── Sidebar.tsx
            ├── storage/
            └── tables/               ← 8개 모두 lazy() 청크 분리됨
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

> ⚠️ w7/w8 = SLA 월별, w13/w14 = 생성/해결 월별 카운트 (개요 문서와 실제 코드가 달랐던 부분)

---

## 5. 오늘 반영된 주요 변경사항 상세

### 5-1. Jira N+1 해결 (`af3897c`)

```python
# jira_client.py — 추가된 구조
class JiraClient:
    _count_cache: dict[str, int]          # 요청 내 JQL 결과 캐시
    _count_locks: dict[str, asyncio.Lock]  # 동시 중복 요청 차단

    async def get_issue_counts_batch(self, jqls: list[str]) -> list[int]:
        """N개 JQL을 asyncio.gather 1회로 처리, 캐시 재사용"""

# jira_port.py — 포트에도 추가
class JiraPort(ABC):
    @abstractmethod
    async def get_issue_counts_batch(self, jqls: list[str]) -> list[int]: ...
```

### 5-2. Background Refresh / SWR (`cf0d6e9`)

```python
# report_cache_port.py
class ReportCachePort(ABC):
    async def get_or_revalidate(self, key, ttl, revalidate_fn) -> T:
        """캐시 HIT → 즉시 반환 + 백그라운드 갱신 트리거
           캐시 MISS → revalidate_fn() 결과 저장 후 반환"""

# report_cache.py
class ReportLruCache(ReportCachePort):
    maxsize = 50
    ttl = 600s
    # stale 구간에서 백그라운드 asyncio.create_task()로 갱신
```

### 5-3. 히스토리 보존 (`6b9e0dd`)

```python
# settings.py 추가 필드
retention_weeks: int = 12   # 기본 12주 보존

# report_repository_impl.py 추가 메서드
async def cleanup_old_reports(self, retention_weeks: int) -> int:
    """retention_weeks 이전 보고서 자동 삭제, 삭제 건수 반환"""
```

### 5-4. SSE + Exponential Backoff (`631888d`)

```python
# trigger.py — 신규 엔드포인트
GET /api/v1/trigger/{job_id}/stream
# → StreamingResponse, text/event-stream
# 이벤트: status(pending/running), done(완료), timeout(15s keepalive)
# 헤더: X-Accel-Buffering: no (nginx 버퍼링 비활성화)

# job_mapper.py — retry_after 힌트
retry_after: pending=3s, running=5s, done/error=None
```

```typescript
// useJobStream.ts — 클라이언트 전략
// 1순위: EventSource (SSE) — 단일 HTTP 커넥션 유지
// 2순위: EB 폴링 — delay = min(1000 * 2^n, 16000) * jitter(±20%)
// SSE onerror 시 EB 폴링으로 자동 전환
```

### 5-5. 모달·차트 Lazy Load (`7fd3683`)

```typescript
// DashboardPage.tsx
// Before: 정적 import → 초기 번들에 recharts + 모달 전체 포함
// After:  lazy() + Suspense → 클릭/렌더 시 해당 청크만 요청

const SlaDonutChart = lazy(() => import('@/presentation/components/charts/SlaDonutChart'))
// ... 차트 7개, 테이블 모달 8개 동일 패턴

// LazyGenerateReportModal.tsx (신규)
// GenerateReportModal의 lazy() 래퍼 — 버튼 클릭 시점에 청크 로드
```

### 5-6. TriggerButton collapsed prop 복원 (`65b11e1`)

```typescript
// TriggerButton.tsx
interface Props {
  collapsed?: boolean  // Sidebar에서 전달하는 prop 복원
}
// collapsed=true  → PlusIcon 전용 아이콘 버튼 (title 툴팁)
// collapsed=false → 전체 너비 "보고서 생성" 텍스트 버튼
```

---

## 6. Container.py — DI 배선

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

## 7. Settings — 실제 필드 목록 (settings.py)

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

# 보존 정책 (오늘 추가)
retention_weeks: int = 12

# 이슈 분류
issue_types     = ["인시던트", "개선", "CVE", "서비스 요청"]
active_statuses = [...10개...]
closed_statuses = ["Closed", "반려됨", "중복 이슈", "취소됨"]
```

---

## 8. API 라우터 구조 (보안 수정 후)

```python
# router.py — /api/v1 prefix
router.include_router(auth.router)           # 인증 불필요
router.include_router(preview_router)        # storage preview만 공개

_protected = APIRouter(dependencies=[Depends(require_auth)])
_protected.include_router(reports.router)
_protected.include_router(trigger.router)    # SSE 스트림 엔드포인트 포함
_protected.include_router(config.router)
_protected.include_router(search.router)
_protected.include_router(storage.router)    # ← 인증 보호로 이동됨
```

> ✅ **Storage 라우터 인증 보호 완료** — `8c91b01` 커밋에서 수정됨

---

## 9. 프론트엔드 도메인 타입 (Report.ts)

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

## 10. 라우팅 — 실제 페이지 경로

| 경로 | 컴포넌트 | 인증 |
|---|---|---|
| `/login` | LoginPage | ❌ |
| `/` | DashboardPage | ✅ |
| `/history` | HistoryPage | ✅ |
| `/reports/:id` | DashboardPage | ✅ |
| `/storage` | StoragePage | ✅ |
| `/storage/preview` | StoragePreviewPage | ✅ |

---

## 11. useTrigger / useJobStream 폴링 로직 (업데이트)

```typescript
// useJobStream.ts — SSE 우선 전략
// 1. EventSource 지원 시: GET /api/v1/trigger/{job_id}/stream 단일 커넥션
//    이벤트: status | done | timeout | error
// 2. EventSource 미지원 또는 onerror 시: EB 폴링 폴백
//    delay = min(1000 * 2^attempt, 16000) * jitter(±20%)
//    서버 retry_after 힌트 있으면 그 값 우선 사용

// useTrigger.ts — useJobStream 기반으로 교체됨
// trigger API 호출 → job_id 수신 → useJobStream으로 완료 대기
```

---

## 12. 번들 청크 분리 현황 (Lazy Load 적용 후)

| 청크 | Before | After |
|---|---|---|
| 초기 DashboardPage 청크 | recharts + 모달 15개 전체 | SummaryCard · AiSummaryCard만 |
| 차트 (7개) | 초기 번들 포함 | 첫 렌더 시 개별 요청 |
| 테이블 모달 (8개) | 초기 번들 포함 | 카드 클릭 시 개별 요청 |
| GenerateReportModal | 레이아웃 마운트 시 포함 | 버튼 클릭 시 요청 |

---

## 13. 새 기능 추가 정확 체크리스트 (실제 코드 기반)

### 새 위젯(wN) 추가 순서
```
1. widget_id.py             → WidgetId enum에 wN 추가
2. widget_data.py           → 데이터 dataclass 추가
3. widgets/xxx_collector.py → AbstractWidgetCollector 구현
4. query_builder.py         → ResolvedQueries에 wN_xxx() JQL 추가
5. container.py             → _base_collector_factory 또는
                               _monthly_collector_factory에 CollectorEntry 추가
6. report_assembler.py      → monthly tuple 언패킹 로직 수정 필요 시
7. presentation/schemas/    → Pydantic 스키마 추가
8. frontend/domain/         → TypeScript 타입 추가
9. infrastructure/api/      → API 호출 추가
10. infrastructure/hooks/   → useXxx 훅 추가
11. presentation/pages/     → 컴포넌트 연결 + lazy() 래핑
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

---

## 14. 주요 설계 결정 & 주의사항 (최신)

| 항목 | 실제 결정 | 비고 |
|---|---|---|
| API prefix | `/api/v1` | main.py에서 마운트 |
| Storage 인증 | **보호됨** (preview만 공개) | `8c91b01` 수정 |
| 월별 수집 | MonthlyCollector → tuple(w7, w8) | assembler에서 언패킹 |
| w13/w14 | MonthlyCountCollector → tuple | 동일 패턴 |
| 캐시 | ReportLruCache(maxsize=50, ttl=600s) + SWR | `cf0d6e9` 추가 |
| DB | **히스토리 보존** (retention_weeks=12) | `6b9e0dd` 수정 |
| SLA 필드 탐지 | `schema.type == "sd-servicelevelagreement"` | 자동 탐지 |
| Storage quota | `STORAGE_LIMIT_BYTES = 2TB` | storage.py |
| 해결일시 | `updated` 필드 사용 | `resolutiondate` null 대응 |
| Jira N+1 | `get_issue_counts_batch()` + 인메모리 캐시 | `af3897c` 수정 |
| 폴링 전략 | SSE 우선 → EB 폴링 폴백 | `631888d` 수정 |
| 초기 번들 | Lazy Load (차트 7 + 모달 8 + GenerateReportModal) | `7fd3683` 수정 |
