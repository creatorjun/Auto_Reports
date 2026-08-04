# backend/docs/01_architecture.md

# Backend Architecture

## 개요

이 프로젝트는 **Clean Architecture** 원칙을 기반으로 4개 레이어로 구성된 FastAPI 백엔드입니다.  
의존성은 항상 **외부 → 내부** 방향으로만 흐르며, 도메인 레이어는 어떤 외부 프레임워크에도 의존하지 않습니다.

```
Presentation  →  Application  →  Domain
                    ↑
             Infrastructure
```

---

## 레이어 구조

### 1. Domain Layer (`src/domain/`)

- **역할**: 비즈니스 핵심 엔티티와 규칙, 추상 포트(인터페이스) 정의
- **의존 금지**: 외부 라이브러리, FastAPI, SQLAlchemy 일절 사용 불가
- **구성**:

| 경로 | 설명 |
|------|------|
| `entities/job.py` | `JobRecord`, `JobStatus` (Enum: PENDING/RUNNING/DONE/ERROR) |
| `entities/report.py` | `Report` 도메인 엔티티 |
| `entities/site.py` | `Site`, `DeploymentNode`, `PatchHistory`, `VisitHistory`, `AccessCredentials`, `Credential`, `ContactInfo` |
| `repositories/job_repository.py` | Job 저장소 추상 인터페이스 |
| `repositories/report_repository.py` | Report 저장소 추상 인터페이스 |
| `ports/ai_port.py` | AI 분석기 추상 포트 |
| `ports/jira_port.py` | Jira 클라이언트 추상 포트 |
| `ports/storage_port.py` | 파일 스토리지 추상 포트 |
| `ports/report_analyzer_port.py` | 보고서 분석 추상 포트 |

---

### 2. Application Layer (`src/application/`)

- **역할**: 유스케이스 오케스트레이션, 도메인 포트를 조합해 비즈니스 흐름 구현
- **의존 허용**: Domain Layer만 의존 가능
- **구성**:

| 경로 | 설명 |
|------|------|
| `use_cases/generate_report.py` | 주간보고서 생성 유스케이스 (Jira 수집 → 위젯 조립 → AI 분석 → DB 저장) |
| `use_cases/get_report.py` | 보고서 조회 유스케이스 (캐시 우선 → DB 폴백) |
| `use_cases/site_use_cases.py` | 사이트 CRUD + 노드/패치/방문이력 관리 유스케이스 |
| `use_cases/partner_use_case.py` | Jira 파트너 조회 유스케이스 |
| `use_cases/storage_use_case.py` | 파일 업로드/다운로드/삭제 유스케이스 |
| `services/ai_analyzer.py` | `AiPort`를 주입받아 AI 분석 수행, `ai_enabled=False`면 스킵 |
| `services/report_assembler.py` | 위젯 컬렉터들을 병렬 실행해 보고서 데이터 조립 |
| `services/query_builder.py` | JQL 쿼리 빌더 (위젯 유형별 JQL 생성) |
| `services/query_config.py` | 쿼리 설정값 VO |
| `widgets/base.py` | 위젯 컬렉터 추상 베이스 클래스 |
| `widgets/collector_factory.py` | 위젯 컬렉터 팩토리 |
| `widgets/count_collector.py` | 이슈 카운트 위젯 |
| `widgets/created_vs_resolved_collector.py` | 생성 vs 해결 추이 위젯 |
| `widgets/monthly_collector.py` | 월별 이슈 위젯 |
| `widgets/monthly_count_collector.py` | 월별 카운트 위젯 |
| `widgets/recent_collector.py` | 최근 이슈 목록 위젯 |
| `widgets/resolution_collector.py` | 해결 현황 위젯 |
| `widgets/sla_delay_collector.py` | SLA 지연 이슈 위젯 |
| `ports/job_runner_port.py` | 백그라운드 잡 실행기 추상 포트 |
| `ports/report_cache_port.py` | 보고서 캐시 추상 포트 |
| `mappers/job_mapper.py` | JobRecord → JobStatusSchema 변환 |

---

### 3. Infrastructure Layer (`src/infrastructure/`)

- **역할**: 외부 시스템 연동 구현체 (DB, Jira, Gemini AI, 스케줄러 등)
- **구성**:

| 경로 | 설명 |
|------|------|
| `container.py` | **DI 컨테이너** — 앱 전체 의존성 조립 (싱글턴 패턴) |
| `config/settings.py` | `pydantic-settings` 기반 환경변수 설정 (`.env` 로드) |
| `persistence/database.py` | SQLAlchemy async engine + session factory |
| `persistence/models.py` | `ReportORM`, `JobORM` — SQLAlchemy Mapped 모델 |
| `persistence/site_models.py` | `SiteORM`, `DeploymentNodeORM`, `PatchHistoryORM`, `VisitHistoryORM` |
| `persistence/report_repository_impl.py` | `ReportRepository` 구현체 |
| `persistence/job_repository_impl.py` | `JobRepository` 구현체 |
| `persistence/site_repository_impl.py` | `SiteRepository` 구현체 (가장 복잡한 구현체) |
| `persistence/widget_serializer.py` | 위젯 데이터 JSONB 직렬화/역직렬화 |
| `external/jira_client.py` | `httpx.AsyncClient` 기반 Jira REST API v3 클라이언트 |
| `external/gemini_client.py` | Google Gemini API 클라이언트 |
| `factories/jira_factory.py` | Jira 클라이언트 팩토리 |
| `factories/ai_factory.py` | AI 클라이언트 팩토리 |
| `factories/widget_collector_factory.py` | 위젯 컬렉터 팩토리 래퍼 |
| `job_runner.py` | `JobRunnerPort` 구현체 — asyncio.Lock 기반 단일 잡 실행 보장 |
| `report_cache.py` | LRU 캐시 구현체 (`ReportCachePort`) |
| `security/jwt_service.py` | JWT access/refresh 토큰 발급·검증 |
| `storage/local_storage.py` | `StoragePort` 로컬 파일시스템 구현체 |
| `scheduler.py` | APScheduler 기반 cron 스케줄러 |

---

### 4. Presentation Layer (`src/presentation/`)

- **역할**: HTTP 요청/응답 처리, Pydantic 스키마 검증, FastAPI 라우터
- **구성**:

| 경로 | 설명 |
|------|------|
| `api/v1/auth.py` | 로그인/로그아웃/토큰 갱신/me 엔드포인트 |
| `api/v1/trigger.py` | 보고서 트리거 + SSE 스트림 |
| `api/v1/reports.py` | 보고서 조회 엔드포인트 |
| `api/v1/sites.py` | 사이트 CRUD + 노드/패치/방문이력 서브리소스 |
| `api/v1/partners.py` | 파트너 조회 엔드포인트 |
| `api/v1/storage.py` | 파일 업로드/다운로드 엔드포인트 |
| `api/deps.py` | FastAPI `Depends` 헬퍼 함수들 |
| `api/v1/deps.py` | v1 전용 `Depends` 헬퍼 함수들 |
| `schemas/report_schema.py` | 보고서 관련 Pydantic 스키마 |
| `schemas/site_schema.py` | 사이트 관련 Pydantic 스키마 |
| `schemas/partner_schema.py` | 파트너 관련 Pydantic 스키마 |

---

## 의존성 주입 방식

`Container` 클래스가 앱 시작 시 모든 의존성을 조립하고 `app.state.container`에 보관합니다.  
`AsyncSession`이 필요한 유스케이스는 요청마다 `Container`의 팩토리 메서드로 생성합니다.

```
app.state.container (Container)
    └─ _jira: JiraPort (JiraClient)
    └─ _ai: AiPort (GeminiClient | NullAi)
    └─ _report_cache: ReportCachePort (ReportLruCache)
    └─ _jwt_service: JwtService
    └─ _storage_use_case: StorageUseCase
    └─ _partner_use_case: PartnerUseCase
    └─ generate_report_use_case(session) → GenerateReportUseCase  [요청당 생성]
    └─ get_report_use_case(session)      → GetReportUseCase        [요청당 생성]
    └─ site_use_case(session)            → SiteUseCase             [요청당 생성]
```

---

## 비동기 처리 및 잡 실행 모델

보고서 생성은 오래 걸리는 작업이므로 FastAPI `BackgroundTasks`로 비동기 실행합니다.  
`JobRunner`는 `asyncio.Lock`으로 **동시에 1개 잡만 실행**되도록 보장합니다.  
클라이언트는 `GET /trigger/{job_id}/stream` SSE 엔드포인트로 진행 상황을 실시간으로 수신합니다.

```
POST /trigger/          → 202 Accepted (job_id 반환)
GET  /trigger/{id}/status   → 폴링 방식 상태 조회
GET  /trigger/{id}/stream   → SSE 스트림 (실시간 상태 push)
```

---

## 스케줄링

`Settings.schedule_cron` (기본값: `"0 23 * * 5"` — 매주 금요일 23:00 KST)에 따라  
APScheduler가 `JobRunner.run_scheduled_job()`을 자동 실행합니다.
