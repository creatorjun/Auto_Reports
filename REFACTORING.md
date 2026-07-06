## backend 유스케이스 · 서비스

| 파일 | 현재 문제 (근거) | 수정안 |
|---|---|---|
| `backend/src/infrastructure/external/jira_client.py` | `requests.Session`(동기 라이브러리)으로 Jira를 호출하며, `get_issue_count`/`get_issues`가 매번 개별 HTTP 요청을 순차 실행합니다 . async 엔드포인트 안에서 동기 I/O가 실행되면 그 시간 동안 전체 이벤트 루프가 멈춰 다른 요청도 함께 지연됩니다. | `requests` → `httpx.AsyncClient`로 교체하고, 커넥션 풀을 재사용하도록 클라이언트를 싱글턴으로 유지합니다. 모든 메서드를 `async def`로 바꿔 `report_collector`에서 `asyncio.gather`로 동시 호출할 수 있게 합니다. |
| `backend/src/application/services/report_collector.py` | `_collect_w1`이 `issue_types`(4종) × `active_statuses`(10종) 조합마다 개별 `get_issue_count` 호출을 순차 실행합니다. W5·W6·W7의 `_breakdown`도 동일하게 항목별 순차 호출입니다. 위젯 13종을 합치면 보고서 1건 생성에 60회 이상의 순차 Jira 왕복이 발생합니다 . | 1) W1은 카운트 40회 대신 `get_issues`로 원본 이슈를 한 번만 가져와 유형×상태별로 로컬에서 집계하도록 바꿉니다. 2) 나머지 위젯도 `collect()` 내부에서 `asyncio.gather(*tasks)`로 동시에 호출해 순차 대기 시간을 없앱니다. 3) 위젯 간 공통 JQL 조건(base, thr, closed)은 한 번만 계산해 재사용합니다. |
| `backend/src/application/use_cases/generate_report.py` | `collect()`와 `analyze()`가 순차 실행되며, 둘 다 완료돼야 `repository.save()`가 호출됩니다 . 구조 자체는 문제없으나 수집이 비동기화되면 여기도 `await self._collector.collect(now)` 형태로 시그니처를 바꿔야 합니다. | `collect`를 async 메서드로 바꾸고, AI 분석에 실패해도 원시 데이터는 저장되도록 `try/except`로 부분 실패를 허용합니다. |
| `backend/src/presentation/api/v1/trigger.py` | `BackgroundTasks`를 인자로 받지만 실제로는 사용하지 않고, `await use_case.execute()`를 요청-응답 흐름에서 그대로 기다립니다 . 위 60여 회 순차 호출이 끝나야 응답이 오므로, 프론트엔드 axios 타임아웃(60000ms)에 걸릴 위험이 있습니다 . | 엔드포인트는 즉시 `202 Accepted` + `job_id`만 반환하고, 실제 생성은 `background_tasks.add_task(...)` 또는 별도 워커로 넘깁니다. 진행 상태 조회용 `/trigger/{job_id}/status` 엔드포인트를 추가해 프론트가 폴링하도록 합니다. |
| `backend/src/application/scheduler/report_scheduler.py` + `container.py` | `run_scheduled_job`이 API 서버와 동일한 asyncio 이벤트 루프에서 실행됩니다 . 수집기가 동기 I/O를 포함하는 한, 매주 금요일 23시 스케줄 실행 중 헬스체크·조회 API가 함께 멈출 수 있습니다. | 위 A안(비동기 Jira 클라이언트)을 먼저 적용하고, 장기적으로는 스케줄러를 backend 프로세스에서 분리해 별도 worker 컨테이너로 옮깁니다. |

## docker-compose.yml

| 서비스 | 현재 상태 (근거) | 수정안 |
|---|---|---|
| 전체 구성 | `db`, `backend`, `frontend` 3개 서비스만 정의되어 있고, 큐나 워커, 캐시 계층이 없습니다 . `trigger.py`가 동기화 방식으로 남아 있는 한 backend 컨테이너가 보고서 생성 요청 하나로 장시간 점유됩니다. | `redis` 서비스와 `worker` 서비스(Celery/RQ 기반)를 추가합니다. `trigger.py`는 `redis`에 job을 enqueue만 하고, `worker`가 `report_collector`/`ai_analyzer`를 실행해 결과를 DB에 저장하도록 분리합니다. |
| `backend` healthcheck | `curl -sf http://localhost:8000/api/health`로 15초마다 헬스체크를 하지만 , 보고서 생성 중 이벤트 루프가 블로킹되면 헬스체크 자체도 실패해 `restart: unless-stopped` 정책과 충돌할 수 있습니다. | A안(비동기 클라이언트) 적용이 최우선 전제이며, 그래도 완화책으로 `healthcheck.timeout`을 늘리기보다 워커 분리를 통해 backend는 항상 가벼운 요청만 처리하게 만드는 것이 근본 해법입니다. |

## 프론트엔드 페이지 · 훅

| 파일 | 현재 문제 (근거) | 수정안 |
|---|---|---|
| `frontend/src/infrastructure/hooks/useReport.ts` | `useAllReports`가 `limit`/`offset` 파라미터를 받지 않고 항상 기본값(20건)만 조회합니다 . | `useAllReports(page: number)`처럼 페이지 인자를 받아 `reportApi.getAll(limit, offset)`에 전달하고, `HistoryPage`에 "더 보기"/페이지네이션 UI를 추가합니다. |
| `frontend/src/presentation/pages/HistoryPage.tsx` | 데스크톱 테이블과 모바일 리스트를 동시에 렌더링하며(둘 다 항상 DOM에 존재, CSS로만 숨김), `date-fns`의 `format()`을 각 행마다 인라인 호출합니다 . 데이터가 20건이라 현재는 체감되지 않지만, 페이지네이션 없이 항목이 늘면 두 배의 DOM 노드가 계속 쌓입니다. | 1) `useAllReports`에 페이지 상태를 연결해 목록을 100건 이상으로 늘려도 안전하게 만듭니다. 2) 반응형 레이아웃을 하나의 컴포넌트로 통합하거나, 최소한 `formattedDate`를 `useMemo`로 캐싱해 리렌더 시 재계산을 줄입니다. |
| `frontend/src/infrastructure/api/reportApi.ts` / `client.ts` | axios `timeout: 60000`이 하드코딩돼 있고 , `trigger()` 호출이 현재 백엔드 동기 처리 방식과 맞물려 있습니다. | 트리거 API가 위 202 Accepted 방식으로 바뀌면 `trigger()`는 즉시 응답을 받으므로 타임아웃 걱정이 사라집니다. `useTrigger.ts`는 성공 시 `job_id`를 받아 `useQuery`로 상태를 짧은 간격(예: 2초)으로 폴링하도록 확장합니다. |

## 적용 순서 제안

가장 먼저 `jira_client.py`를 `httpx.AsyncClient`로 바꾸고 `report_collector.py`에서 `asyncio.gather`를 적용하는 것이 투자 대비 효과가 가장 큽니다. 이 두 파일만 고쳐도 보고서 생성 시간이 순차 60여 회 왕복에서 병렬 처리로 크게 줄어들며, 다른 API 요청이 함께 멈추는 문제도 완화됩니다 . 그다음 `trigger.py`를 비동기 job 방식으로 바꾸고 `docker-compose.yml`에 워커를 분리하면, 이후 스케줄러도 안전하게 분리할 수 있는 구조가 만들어집니다 . 프론트엔드 페이지네이션은 우선순위상 마지막이지만, 데이터가 계속 누적되는 히스토리 특성상 늦지 않게 반영해두는 것이 좋습니다 .