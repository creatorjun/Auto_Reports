코드를 철저히 분석했습니다. 전체 구조를 파악했으니 클린 아키텍처 관점의 정밀한 리팩토링 계획서를 작성합니다.

***

# Auto_Reports 클린 아키텍처 리팩토링 계획서

## 현황 진단 — 잘 된 것들

먼저 긍정적인 부분을 확인합니다. `domain/`, `application/`, `infrastructure/`, `presentation/` 4계층 디렉토리 구조가 이미 존재하고 , `JiraPort`, `AiPort` 같은 추상 인터페이스(Port)가 `domain/ports/`에 분리되어 있어 의존성 역전 원칙(DIP)의 뼈대는 갖춰져 있습니다 . `DateRange`, `AiAnalysis`, `WidgetId` 같은 Value Object들이 `frozen=True` dataclass나 StrEnum으로 올바르게 구현되어 있고 , `GenerateReportUseCase`가 추상 타입에만 의존하는 형태도 의도는 맞습니다 .

***

## 핵심 문제 진단

### 문제 1 — ReportCollector의 심각한 SRP 위반

현재 `report_collector.py`는 **20,369 바이트, 단일 클래스**에 15개 위젯 수집 로직이 전부 집약되어 있습니다 . `_collect_w1`, `_collect_w7`, `_collect_w10`, `_collect_w11`, `_collect_w12`, `_collect_w14`, `_collect_w15_w16_monthly` 등 각 위젯 수집 메서드가 모두 한 클래스 안에 있으며, 각 메서드는 수십~수백 줄의 독립적인 도메인 로직(날짜 계산, SLA 판정, issue 파싱)을 내포합니다. 이것은 **단일 책임 원칙(SRP)** 의 명백한 위반이며, 새 위젯 추가 시마다 이 파일이 변경되는 **Open/Closed Principle(OCP) 위반**이기도 합니다.

또한 `ReportCollector` 내부에서 `self._settings.sla_threshold_days`, `self._settings.sla_initial_response_field_id` 같은 인프라 설정값을 직접 참조하고 있어 , Application 계층이 Config(인프라 관심사)에 직접 결합되어 있는 구조입니다.

### 문제 2 — AiAnalyzer의 레이어 위치 오류

`AiAnalyzer`는 `application/services/ai_analyzer.py`에 위치하면서 내부에서 `WidgetId` 열거형으로 특정 위젯 데이터를 직접 파싱하고 AI 프롬프트 컨텍스트를 조립합니다 . 문제는 이 클래스가 `AiPort` 추상 인터페이스를 래핑하는 단순 위임자(Facade)에 불과한데, 프롬프트 템플릿과 컨텍스트 변환 로직이 `GeminiClient`(infrastructure)의 `PROMPT_TEMPLATE` 상수로 하드코딩되어 있다는 점입니다 . 프롬프트는 **도메인 정책**에 해당하는 것인데 인프라 어댑터 파일에 박혀 있어, AI 모델을 교체할 때 프롬프트까지 함께 이전해야 하는 구조입니다.

### 문제 3 — Container의 책임 과적재

`container.py`는 DI 컨테이너인데, `execute_in_background`와 `run_scheduled_job` 메서드가 같이 있어 **오케스트레이션 로직을 직접 실행**합니다 . DI 컨테이너는 객체 조립만 담당해야 하고, 잡 실행 상태 추적(`self._jobs: dict`)이나 비동기 실행은 별도 Application Service나 Scheduler로 분리해야 합니다. 현재는 `AsyncSessionLocal`을 Container가 직접 호출하고 있어 영속성 관리 책임까지 겹쳐 있습니다.

### 문제 4 — WidgetResult Entity의 타입 붕괴

`WidgetResult.breakdown`이 `dict[str, Any]`로 선언되어 있고 , 각 위젯마다 완전히 다른 구조의 딕셔너리를 담고 있습니다 — w1은 `{"by_type": ..., "issue_details": [...]}`, w7은 `{"_distribution": ..., "_issue_details": ...}`, w14는 `{"생성": ..., "해결": ..., "created_details": [...]}` 등. 이런 구조는 타입 시스템을 무력화하고, 컨슈머(presentation layer, ai_analyzer)가 런타임 KeyError에 취약해집니다. 도메인 엔티티의 내부 구조는 명시적이어야 합니다.

### 문제 5 — 파일 위치 오염 (`widget_id.py` 파일 헤더 누락)

`widget_id.py`에 경로 헤더 주석이 없고 , `jira_client.py`에도 경로 헤더가 없습니다 . 준희님의 코드 생성 규칙 5번 — 파일 최상단에 경로명/파일명 주석 — 이 일관되게 적용되지 않았습니다.

### 문제 6 — 루트 레벨 스크립트 오염

`backend/get_data.py`, `backend/test_sla_debug.py`가 패키지 외부에 스크립트로 존재합니다 . 이 파일들은 내부적으로 어떤 레이어를 침범하는지 불명확하고, 프로덕션 코드와 동일한 위치에 존재하는 것 자체가 아키텍처 경계를 흐립니다.

***

## 리팩토링 계획 — Phase별 실행 순서

### Phase 1 — WidgetResult 타입 강화 (도메인 계층)

**목표**: `dict[str, Any]` 를 제거하고 각 위젯 타입에 맞는 명시적 데이터 클래스를 도입합니다.

```
backend/src/domain/entities/
    widget.py          ← WidgetResult[T] (Generic) 또는 Union 타입
    widget_data.py     ← OverdueWidgetData, SlaWidgetData, MonthlyWidgetData 등
```

`WidgetResult`를 `Generic[T]`로 변경하거나, 위젯 종류별 전용 dataclass를 만들어 `breakdown: Any` 필드를 `data: OverdueWidgetData` 처럼 구체적인 타입으로 교체합니다. 이렇게 하면 `ai_analyzer.py`와 presentation layer의 `breakdown.get(...)` 런타임 접근이 컴파일 타임 타입 체크로 승격됩니다.

### Phase 2 — ReportCollector 분해 (Application 계층)

**목표**: 파일 하나에 몰려 있는 위젯 수집 로직을 위젯별 독립 클래스로 분리합니다.

```
backend/src/application/
    use_cases/
        generate_report.py
        get_report.py
    services/
        ai_analyzer.py
        report_assembler.py     ← 기존 collect() 진입점만 담당
    widgets/                    ← 신규 패키지
        base.py                 ← AbstractWidgetCollector(ABC)
        overdue_collector.py    ← W1
        sla_delay_collector.py  ← W5, W6, W7
        sla_monthly_collector.py← W12, W15, W16
        resolution_collector.py ← W10, W11
        count_collector.py      ← W2, W3, W4, W8, W9, W13
        created_vs_resolved_collector.py ← W14
```

`AbstractWidgetCollector`가 `collect(q: WidgetQuery) -> WidgetResult` 추상 메서드를 정의하고, `ReportAssembler`는 위젯 컬렉터 목록을 주입받아 `asyncio.gather`로 실행만 합니다. 이후 새 위젯 추가는 새 파일만 추가하면 되고 기존 파일은 변경하지 않아도 됩니다 — **OCP 달성**.

`Settings` 직접 참조는 각 위젯 컬렉터 생성 시 필요한 값만 생성자에 주입하는 방식으로 교체합니다. 예: `OverdueCollector(jira, sla_threshold_days=settings.sla_threshold_days)`.

### Phase 3 — 프롬프트 정책 이전 (Domain → Application 경계)

**목표**: `gemini_client.py`에 있는 `PROMPT_TEMPLATE` 상수를 Application 계층으로 이동합니다.

```
backend/src/application/
    services/
        ai_analyzer.py  ← PROMPT_TEMPLATE 상수 이전, 컨텍스트 조립 로직 보유
```

`GeminiClient`는 `AiPort.analyze(context: dict) -> AiAnalysis` 계약만 이행하고, 프롬프트를 어떻게 만드는지는 몰라야 합니다. Application이 프롬프트를 완성해서 인프라에 전달하는 방식으로 `AiPort` 시그니처도 `analyze(prompt: str) -> AiAnalysis`로 변경하는 것이 더 명확합니다.

### Phase 4 — Container 책임 분리 (Infrastructure 계층)

**목표**: DI 컨테이너에서 실행 로직을 제거합니다.

```
backend/src/infrastructure/
    container.py            ← 객체 조립만 담당, jobs/execute 제거
    job_runner.py           ← execute_in_background, run_scheduled_job 이전
```

`Container`는 `generate_report_use_case()`, `get_report_use_case()` 팩토리 메서드만 남기고, `JobRunner`가 `Container`를 주입받아 비동기 실행과 상태 추적을 담당합니다. `AsyncSessionLocal`의 직접 참조는 `JobRunner` 안으로 이전합니다.

### Phase 5 — 파일 정리 및 헤더 정규화

`backend/get_data.py`와 `backend/test_sla_debug.py`를 `backend/scripts/` 또는 `backend/tests/` 디렉토리로 이동합니다. 경로 헤더 주석이 누락된 `widget_id.py`, `jira_client.py` 두 파일에 헤더를 추가합니다.

***

## 리팩토링 전후 구조 비교

| 항목 | 현재 (AS-IS) | 목표 (TO-BE) |
|---|---|---|
| `report_collector.py` | 단일 파일, ~600줄, 15개 위젯 로직 | `widgets/` 패키지로 7개 파일 분산 |
| `WidgetResult.breakdown` | `dict[str, Any]` (타입 붕괴) | 위젯별 전용 dataclass |
| `PROMPT_TEMPLATE` | `gemini_client.py` (infrastructure) | `ai_analyzer.py` (application) |
| Container | 조립 + 실행 + 상태추적 혼합 | 조립만, 실행은 `JobRunner` 분리 |
| 위젯 추가 시 영향 | `report_collector.py` 수정 필수 | 새 파일 추가만으로 완결 |
| 테스트 용이성 | 전체 Collector mocking 필요 | 위젯 단위로 독립 테스트 가능 |
| 스크립트 파일 | `backend/` 루트 노출 | `backend/scripts/`, `tests/` 격리 |

***

## 의존성 방향 최종 정리

클린 아키텍처의 핵심은 의존성 방향이 항상 **안쪽(도메인)을 향해야** 한다는 것입니다. 현재 가장 위험한 흐름은 `ReportCollector`(application)가 `Settings`(infrastructure config)를 직접 임포트한다는 점 과, 프롬프트(application 정책)가 `GeminiClient`(infrastructure)에 있다는 점입니다 . 이 두 가지 방향 오염만 잡아도 전체 아키텍처 순수성이 크게 향상됩니다.

Phase 순서는 **1 → 2 → 3 → 4 → 5** 순으로 진행하되, Phase 1(타입 강화)이 Phase 2(Collector 분해) 시 타입 안전성을 보장하므로 반드시 선행되어야 합니다. 각 Phase 완료 후 현재 동작이 변하지 않음을 검증하는 회귀 테스트를 붙이는 것을 권장합니다.