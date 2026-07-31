# docs/refactoring-plan.md

## 백엔드 성능 분석 및 리팩토링 계획

---

## P0 — 즉시 수정 (성능 크리티컬)

### 1. Container 생명주기 오염 — 매 요청마다 객체 트리 재생성

**문제:** `generate_report_use_case(session)` 호출 시 `WidgetQueryBuilder`, `ReportAssembler`, `AiAnalyzer`가 매 요청마다 새로 생성됨. 이 객체들은 stateless이므로 불필요한 인스턴스 생성 오버헤드 발생.

**수정 대상:** `app/infrastructure/container.py`

**수정 방향:**
```python
class Container:
    def __init__(self, settings: Settings):
        ...
        self._query_builder = WidgetQueryBuilder(self._query_config)
        self._assembler = ReportAssembler(
            query_builder=self._query_builder,
            base_collector_factory=self._base_collector_factory,
            monthly_collector_factory=self._monthly_collector_factory,
        )
        self._analyzer = AiAnalyzer(ai=self._ai, enabled=settings.ai_enabled)

    def generate_report_use_case(self, session: AsyncSession) -> GenerateReportUseCase:
        return GenerateReportUseCase(
            assembler=self._assembler,
            analyzer=self._analyzer,
            repository=ReportRepositoryImpl(session),
            cache=self._report_cache,
            retention_weeks=self._settings.report_retention_weeks,
        )
```

---

### 2. report_assembler.py — 하드코딩된 WidgetId 분기 (OCP 위반)

**문제:** Collector가 `tuple`을 반환하는 경우 어떤 `WidgetId`에 매핑되는지를 `ReportAssembler`가 직접 알고 있어야 함. 새 위젯 추가 시 if-else 분기를 수동으로 수정해야 하는 OCP 위반.

**수정 대상:** `app/application/report_assembler.py`, `app/domain/collector_entry.py`

**수정 방향:**
```python
@dataclass
class CollectorEntry:
    widget_ids: list[WidgetId]
    collector: object

# Assembler에서 분기 없이 처리
for entry, result in zip(all_entries, all_results):
    if isinstance(result, tuple):
        for wid, res in zip(entry.widget_ids, result):
            widgets[wid] = res
    else:
        widgets[entry.widget_ids[0]] = result
```

---

## P1 — 중요 성능 이슈

### 3. jira_client.py — 페이지네이션 순차 요청 (N+1 패턴)

**문제:** Jira REST API 기본 `maxResults=50` 제한으로 인해 전체 이슈 조회 시 `총 이슈 수 / 50` 번의 직렬 HTTP 요청 발생 가능.

**수정 대상:** `app/infrastructure/jira/jira_client.py`

**수정 방향:**
```python
async def _fetch_all_parallel(self, jql: str, fields: str) -> list[dict]:
    first = await self._get(jql, fields, start_at=0, max_results=100)
    total = first["total"]
    if total <= 100:
        return first["issues"]

    tasks = [
        self._get(jql, fields, start_at=i, max_results=100)
        for i in range(100, total, 100)
    ]
    pages = await asyncio.gather(*tasks)
    return first["issues"] + [issue for page in pages for issue in page["issues"]]
```

---

### 4. ReportLruCache — Cache Stampede 미대응

**문제:** 캐시 동시 만료 시 여러 요청이 동시에 캐시 miss를 감지하고 모두 Jira API를 호출하는 Cache Stampede 발생 가능.

**수정 대상:** `app/infrastructure/cache/report_lru_cache.py`

**수정 방향:**
```python
class ReportLruCache:
    def __init__(self, ...):
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_or_set(self, key: str, factory: Callable) -> Any:
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = self._cache.get(key)
            if cached is not None:
                return cached
            result = await factory()
            self._cache.set(key, result)
            return result
```

---

### 5. report_assembler.py — asyncio.gather 두 번 분리 호출

**문제:** base collectors와 monthly collectors를 별도의 `asyncio.gather`로 두 번 호출. 두 그룹 간 의존성이 없으므로 전체 수집 시간이 불필요하게 증가.

**수정 대상:** `app/application/report_assembler.py`

**수정 방향:**
```python
all_collectors = [e.collector for e in base_entries] + [c for _, c in monthly_pairs]
all_results = await asyncio.gather(*[c.collect() for c in all_collectors], return_exceptions=True)
```

---

## P2 — 구조 개선

### 6. count_collector.py — 파일 내 클래스 혼재

**문제:** `SimpleCountCollector`, `SimpleWithDetailsCollector`, `SlaMetVsViolatedCollector` 세 클래스가 하나의 파일에 혼재. SLA 도메인 로직 분리 필요.

**수정 대상:** `app/application/widgets/count_collector.py`

**수정 방향:** `sla_count_collector.py`로 SLA 관련 클래스 분리.

---

### 7. container.py — 캐시 TTL 상수를 Settings으로 이전

**문제:** `_CACHE_FRESH_TTL`, `_CACHE_STALE_TTL`이 모듈 레벨 상수로 하드코딩되어 환경별 튜닝 불가.

**수정 대상:** `app/infrastructure/container.py`, `app/config/settings.py`

**수정 방향:** `Settings` 클래스에 `cache_fresh_ttl: int = 600`, `cache_stale_ttl: int = 120` 추가.

---

## P3 — 안정성 / 운영 품질

### 8. asyncio.gather — 단일 Collector 오류 시 전체 수집 실패

**문제:** 하나의 collector 예외가 전체 `gather`를 실패시킴.

**수정 대상:** `app/application/report_assembler.py`

**수정 방향:**
```python
results = await asyncio.gather(
    *[e.collector.collect() for e in entries],
    return_exceptions=True
)
for entry, result in zip(entries, results):
    if isinstance(result, Exception):
        logger.error(f"Widget {entry.widget_id} 수집 실패: {result}")
        widgets[entry.widget_id] = WidgetResult.error(entry.widget_id)
    else:
        widgets[entry.widget_id] = result
```

---

### 9. gemini_client.py — AI 분석 타임아웃 미설정

**문제:** AI API 호출에 타임아웃이 없어 수십 초 지연 시 전체 요청 블로킹 가능.

**수정 대상:** `app/infrastructure/ai/gemini_client.py`

**수정 방향:**
```python
result = await asyncio.wait_for(self._ai.generate_async(prompt), timeout=30.0)
```

---

## 우선순위 실행 순서

| 순서 | 파일 | 작업 | 효과 |
|---|---|---|---|
| 1 | `container.py` | Assembler/Analyzer 싱글턴화 | 객체 생성 오버헤드 제거 |
| 2 | `report_assembler.py` | 단일 gather 통합 + return_exceptions=True | 수집 시간 단축 + 안정성 |
| 3 | `jira_client.py` | 페이지네이션 병렬화 | API 왕복 횟수 대폭 감소 |
| 4 | `report_assembler.py` + `collector_entry.py` | CollectorEntry 다중 WidgetId 지원 | OCP 준수, 확장성 확보 |
| 5 | `report_lru_cache.py` | Single-flight 패턴 적용 | Cache Stampede 방지 |
| 6 | `gemini_client.py` | 타임아웃 설정 | AI 응답 지연 차단 |
| 7 | `count_collector.py` | SLA 클래스 분리 | 파일 책임 단순화 |
| 8 | `settings.py` | 캐시 TTL 상수 이전 | 환경별 튜닝 가능 |
