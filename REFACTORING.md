# Auto_Reports 마스터피스 권짇 클린 아키텍처 개선 계획서 v2

> **상태**: Phase 1다의점 5 모두 완료. 이 문서는 다음 단계 개선 과제를 정의한다.

---

## 현황 진단 — 완료된 것들

- [x] `WidgetResult.breakdown: dict[str, Any]` → `data: T` 제네릭 타입 강화
- [x] `ReportCollector` 단일 파일 → `widgets/` 패키지로 분해
- [x] `PROMPT_TEMPLATE` Infrastructure → Application 이전
- [x] `Container` 에서 실행 로직 제거, `JobRunner` 도입
- [x] 루트 스크립트를 `backend/scripts/` 로 격리

---

## 다음 단계 개선 과제 — 근본 문제에서 시작

---

### 과제 A — `JobRunner._jobs` 인메모리 상태 저장소 교체

**문제**: `JobRunner._jobs: dict[str, dict]` 는 서버 메모리에만 존재한다. 서버가 재시작되면 모든 job 상태가 소멸되고, 멀티프로세스 환경(Docker 스케일링, Kubernetes)에서는 다른 인스턴스가 job 상태를 조회할 수 없다. 모든 상태가 고어진 `plain dict` 로 관리되어 타입 안전성도 없다.

**목표**:
```
backend/src/domain/entities/job.py     ← JobStatus StrEnum, JobRecord dataclass 신규
backend/src/domain/repositories/job_repository.py  ← JobRepository(ABC) 포트
backend/src/infrastructure/persistence/
    job_repository_impl_memory.py      ← 인메모리 구현 (DefaultJobRepository)
    job_repository_impl_db.py          ← PostgreSQL JSONB 구현 (선택)
backend/src/infrastructure/persistence/models.py  ← JobORM 새 테이블 추가 (선택)
```

`JobRunner` 단`_jobs dict`를 `JobRepository` 포트로 교체한다. 제스터 주입으로 `JobRepository` 구현체를 바꿀 수 있어 테스트에서는 In-Memory, 프로덕션에서는 DB 구현체를 사용할 수 있다.

```python
# domain/entities/job.py
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

class JobStatus(StrEnum):
    RUNNING = "running"
    DONE    = "done"
    ERROR   = "error"

@dataclass
class JobRecord:
    job_id: str
    status: JobStatus
    report_id: Optional[int] = None
    error: Optional[str] = None
```

---

### 과제 B — `WidgetQueryBuilder` 설정 직접 결합 제거

**문제**: `WidgetQueryBuilder.__init__(self, settings: Settings)` 는 Application 서비스가 `Settings`(인프라 Config)에 직접 의존한다. 미래에 `project_key`나 `issue_types`가 DB나 외부 API에서 온다면 Application 에 바로 취약점이 된다. 또한 `w8_yearly_created`, `w9_yearly_resolved`를 보면 `"2026-01-01"` 같은 연도가 하드코딩되어 있다.

**목표**:
```
backend/src/application/services/query_config.py   ← QueryConfig dataclass 신규
```

```python
# application/services/query_config.py
from dataclasses import dataclass

@dataclass(frozen=True)
class QueryConfig:
    project_key: str
    issue_types: list[str]
    active_statuses: list[str]
    closed_statuses: list[str]
    sla_threshold_days: int
    year_start: int  # w8/w9 연도 시작 대신 하드코딩 제거
```

`Container`가 `Settings`에서 `QueryConfig`를 조립하여 `WidgetQueryBuilder`에 주입한다. 이로써 Application 에서 `Settings` import가 완전히 사라진다.

---

### 과제 C — `Presentation → Domain dataclass` 직접 개방

**문제**: `reports.py`에서 `dataclasses.asdict(v.data)` 를 호출하는 것은 Presentation 에서 Domain Entity 내부 구조를 직접 파기하는 행위다. Application 에 직렉한 Mapper(Assembler)가 없다는 못이다. 마찬가지로 `WidgetResultSchema.data: dict[str, Any]` 도 Presentation 에서 타입이 무너진다.

**목표**:
```
backend/src/application/mappers/report_mapper.py   ← ReportMapper 신규
backend/src/presentation/schemas/report_schema.py  ← WidgetDataSchema 타입체 도입
```

`ReportMapper.to_detail_schema(report: Report) -> ReportDetailSchema` 같은 전담 매퍼를 Application 에 두어 Presentation 이 Domain 내부를 모르게 한다. `WidgetResultSchema.data` 필드도 `dict[str, Any]` 대신 `Union[OverdueWidgetSchema, SlaDelayWidgetSchema, ...]` 모델로 교체하여 API 답변 타입도 명시적으로 만든다.

---

### 과제 D — `ReportRepositoryImpl` 내부 피클-디피클 직접 구현 분리

**문제**: `report_repository_impl.py` 안에 `_dict_to_dataclass`, `_coerce_field`, `_serialize_widget`, `_deserialize_widget`, `_WIDGET_DATA_TYPE_MAP` 같은 복잡한 직렬화 로직이 몰려 있다. 이 코드는 Repository의 정의라기보다 정로에 가깝다. Repository 역할은 저장/조회인데, 직렬화 전략까지 번들리는 것은 SRP 위반이다.

**목표**:
```
backend/src/infrastructure/persistence/
    widget_serializer.py   ← _serialize_widget, _deserialize_widget, _WIDGET_DATA_TYPE_MAP 이전
    report_repository_impl.py  ← 저장/조회 SQL 로직만 잔류
```

---

### 과제 E — `Report` 엔티티 가변성 문제

**문제**: `Report.id: Optional[int]` 는 `None`으로 시작해 DB에 저장된 후 뮣도로 `report.id = orm.id`로 외부에서 할당된다. Mutable dataclass의 이 패턴은 `id`가 엔티티 식별자로서 언제부터 유효한지 쭬적하기 어렵다.

**목표**: 두 가지 엔티티를 명확히 분리한다.

```python
# domain/entities/report.py
@dataclass(frozen=True)
class NewReport:      # 아직 저장되지 않은 보고서, id 없음
    week_start: date
    week_end: date
    report_date: str
    widgets: dict[str, WidgetResult] = field(default_factory=dict)
    ai_analysis: Optional[AiAnalysis] = None

@dataclass(frozen=True)
class Report(NewReport):   # DB 저장 후 식별자를 가진 보고서
    id: int = 0
    created_at: Optional[datetime] = None
```

Repository.save는 `NewReport` 수신, `Report` 반환. Use Case가 반환구조만 수신하면 엔티티가 다시 변이될 수 없다는 보장이 생긴다.

---

### 과제 F — Settings `config/` 레이어 소속문제

**문제**: `src/config/settings.py`는 독립 레이어이지만, 기술적으로는 인프라의 관심사다. DB 접속명, Jira API 토큰 등 인프라에 관한 모든 정보를 일괄 포함하므로 인프라에 있는 것이 더 자연스럽다. 실제로 Application 로직은 `Settings`를 `import`하지 않고 `QueryConfig`(과제 B) 같은 Application 전용 DTO를 통해 필요한 값만 받아야 한다.

**목표**:
```
backend/src/config/  →  backend/src/infrastructure/config/
    settings.py 위치 이동
```

Application과 Domain은 `Settings`를 응직도 import하지 않는 구조를 목표로 한다. 모든 세부 설정값은 `Container`가 `Settings`로부터 추출해서 Application DTO로 변환한 후 주입한다.

---

### 과제 G — `AiAnalyzer.analyze()` 동기 메서드 문제

**문제**: `GenerateReportUseCase.execute()`에서 `self._analyzer.analyze(report)`를 `await` 없이 호출한다. 결과적으로 Gemini API HTTP 요청이 동기 코루틴을 블록한다. FastAPI는 비동기를 기반으로 하는데 동기 I/O는 이벤트 루프 전체를 잡는 심각한 성능 문제다.

**목표**:
```python
# domain/ports/ai_port.py
class AiPort(ABC):
    @abstractmethod
    async def analyze(self, prompt: str) -> AiAnalysis: ...  # 비동기로 변경

# application/services/ai_analyzer.py
async def analyze(self, report: Report) -> Optional[AiAnalysis]:
    ...
    return await self._ai.analyze(prompt)  # await 추가
```

`GeminiClient.analyze`도 `httpx.AsyncClient`를 이미 사용 중이므로 `async def`로 바꾸면 충돌 없이 적용된다. Use Case에서도 `await self._analyzer.analyze(report)`로 수정한다.

---

### 과제 H — 시스템 테스트 부재

**문제**: `backend/` 전체에 `pytest` 테스트가 단 한 개도 없다. 클린 아키텍처는 배포 시 동작을 보장하는 자동화된 테스트 없이 추상적 설청만 갖추면 의미없다.

**목표**:
```
backend/tests/
    unit/
        domain/
            test_report_entity.py        ← NewReport/Report 불변성 검증
            test_widget_data.py          ← dataclass 직렬화/디직렬화 화람테스트
        application/
            test_generate_report_uc.py   ← UseCase 루트 유닛 테스트 (Mock Port)
            test_ai_analyzer.py          ← 프롬프트 생성 로직 단위 테스트
            widgets/
                test_overdue_collector.py
                test_sla_delay_collector.py
    integration/
        test_report_repository.py        ← 실제 DB 라운드트립 (testcontainers-python)
    conftest.py
    requirements-test.txt
```

특히 `GenerateReportUseCase`는 `JiraPort`, `AiPort`, `ReportRepository` 모두 Mock으로 대체 가능하므로 외부 의존 없이 실행할 수 있는 이상적인 단위 테스트 대상이다.

---

### 과제 I — `JobStatusSchema.status` 타입 엄격화

**문제**: `JobStatusSchema.status: str` 로 선언되어 있어 API 컨슈머가 `"running"`, `"done"`, `"error"` 이외의 값을 받는 경우를 사전에 차단하지 못한다.

**목표**: 과제 A에서 만든 `JobStatus` StrEnum을 Pydantic 스키마에도 직접 사용한다.

```python
# presentation/schemas/report_schema.py
from src.domain.entities.job import JobStatus

class JobStatusSchema(BaseModel):
    job_id: str
    status: JobStatus          # str → StrEnum
    report_id: Optional[int] = None
    error: Optional[str] = None
```

---

### 과제 J — `config/` 에 경로 헤더 누락

**문제**: `backend/src/config/settings.py`에 경로 헤더 주석이 없다. 파일헤더 규칙(5번) 엄수.

**목표**: 파일 최상단에 `# backend/src/config/settings.py` 추가.

---

## 실행 순서

| Phase | 과제 | 위험도 | 우선순위 |
|---|---|---|---|
| A | `_jobs dict` → `JobRepository` 포트 | 높음 | ★★★★★ |
| B | `WidgetQueryBuilder` 설정 직접 결합 제거 | 중간 | ★★★★ |
| C | Presentation → Domain 직접 개방 차단, Mapper 도입 | 높음 | ★★★★★ |
| D | `ReportRepositoryImpl` 직렬화 로직 분리 | 낙음 | ★★★ |
| E | `Report` 엔티티 가변성 문제 | 높음 | ★★★★★ |
| F | `config/` → `infrastructure/config/` 이동 | 낙음 | ★★★ |
| G | `AiPort.analyze` 동기 → 비동기 | 중간 | ★★★★ |
| H | 테스트 코드 게체 | 낙음 | ★★★ |
| I | `JobStatusSchema.status` StrEnum 엄격화 | 낙음 | ★★ |
| J | `settings.py` 헤더 주석 | 낙음 | ★ |

단순한 포맸�인 I, J는 모든 Phase와 밟행해 길지직선으로 처리할 수 있다.
A → B → G → E → C → D → F → H 순서가 구조적 보완성이 가장 높다.

---

## 마스터피스 다다른 기준

어떤 Phase를 실행하든 아래 다섯 가지 기준이 모두 치툼 때 `Auto_Reports`는 몈플리스틸 수준이라 할 수 있다.

1. **의존성 방향**: Domain ← Application ← Infrastructure, 역방향 import이 단 한 건도 없다.
2. **포트 순수성**: JiraPort, AiPort, ReportRepository, JobRepository 등 모든 외부 의존이 ABC 인터페이스 뒤에 숨어 있다.
3. **가변성 제어**: Domain Entity는 `frozen=True` dataclass로, 상태 변이는 도메인 서비스나 유즈 케이스로만 가능하다.
4. **테스트 성은낥**: 모든 필수 비즈니스 로직이 외부 I/O 없이 단위 테스트 가능하다.
5. **타입 안전성**: API 요청/응답도 `dict[str, Any]`가 없으며, 실마다 Pydantic 또는 dataclass 명세로 바인드된다.
