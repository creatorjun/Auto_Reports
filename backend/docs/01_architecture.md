# Backend Architecture

## 의존성 규칙

```text
                         ┌──────────────────┐
                         │      Domain      │
                         │ entity, value    │
                         └────────▲─────────┘
                                  │
                         ┌────────┴─────────┐
                         │   Application    │
                         │ use case, port   │
                         └──────▲────▲──────┘
                                │    │
                 ┌──────────────┘    └──────────────┐
        ┌────────┴─────────┐              ┌─────────┴────────┐
        │ Infrastructure   │              │   Presentation   │
        │ adapter, driver  │              │ HTTP, schema     │
        └────────▲─────────┘              └─────────▲────────┘
                 └──────────────┬───────────────────┘
                                │
                         ┌──────┴──────┐
                         │ Bootstrap   │
                         │ composition │
                         └─────────────┘
```

- `domain`은 표준 라이브러리 외 프레임워크를 import하지 않습니다.
- `application`은 `domain`과 `application` 내부만 import합니다.
- 저장소, 외부 API, 토큰, 캐시, 감사 로그, 파일 변환 계약은 Application 포트입니다.
- 외부 API 포트는 공급자의 원시 JSON을 반환하지 않고 `JiraIssue`, `JiraComment`, `PartnerMember` 같은 내부 경계 타입을 반환합니다.
- `infrastructure`는 포트를 구현하고 SQLAlchemy, httpx, APScheduler, 파일시스템을 소유합니다.
- `presentation`은 HTTP와 Pydantic 변환만 담당하고 구체 인프라 구현을 알지 못합니다.
- `bootstrap`과 `main.py`만 양쪽의 구체 구현을 조립합니다.

이 규칙은 `backend/tests/test_architecture.py`가 AST import graph로 검사합니다.

## 레이어별 구성

### Domain

`src/domain/entities`와 `src/domain/value_objects`가 보고서, 잡, 사이트, 위젯 모델과 핵심 값을 정의합니다. `constants.py`는 KST와 도메인 기본값을 제공합니다. 저장소 인터페이스나 외부 서비스 계약은 Domain에 두지 않습니다.

### Application

`src/application/ports`에 Jira, Service Desk, AI, 이메일, 저장소, 캐시, 인증 토큰, 감사, 파일 저장소와 변환기, 잡 실행 계약이 있습니다. `use_cases`는 이 추상화만 조합하며 FastAPI 요청 객체, SQLAlchemy 세션, APScheduler를 받지 않습니다.

Jira 필드 선택은 `JiraIssueField`로 표현합니다. `issuetype`, `resolutiondate`, `customfield_*`, SLA cycle, ADF와 rendered HTML 같은 공급자 표현의 해석은 Jira adapter 한 곳에만 있으며, Application은 불변 경계 타입의 속성만 사용합니다. Jira/Confluence 통합 검색 역시 Presentation에서 출력 포트를 직접 호출하지 않고 `SearchUseCase`를 통과합니다.

보고서 위젯 수집기는 시스템 시계를 직접 읽지 않습니다. 보고서 생성·갱신 경계에서 결정된 기준 시각을 전달받아 경과일과 미해결 처리 시간을 계산하므로, 과거/연간 보고서를 다시 생성해도 실행 시점에 따라 값이 바뀌지 않습니다.

사이트 하위 엔티티 갱신은 frozen dataclass를 직접 변경하지 않고 `dataclasses.replace`로 새 값을 만든 뒤 aggregate 전체를 저장합니다. 없는 aggregate나 하위 엔티티는 `EntityNotFoundError`로 표현하고 HTTP 404 매핑은 바깥 레이어에서 수행합니다.

### Infrastructure

- `persistence`: `Database`가 async engine과 session transaction을 소유하고 repository adapter가 ORM 매핑을 수행합니다.
- `external`: Jira, Gemini, SMTP adapter입니다.
- `storage`: 로컬 파일 adapter와 LibreOffice 문서 변환 adapter입니다.
- `cache`: 만료형 LRU 구현과 생성한 정리 task의 종료를 책임집니다.
- `scheduling`: cron 검증과 APScheduler 생성입니다.
- `job_runner.py`: 보고서 task와 동시 실행 정책을 소유합니다.
- `security`: JWT와 선택적 Fernet 자격증명 암호화입니다.

### Presentation

`src/presentation/api`는 FastAPI 라우터와 명시적 `ApiServices` 의존성을 사용합니다. Pydantic 변환은 `presentation/mappers`, 요청·응답 모델은 `presentation/schemas`, HTTP 보조 로직은 `presentation/http`에 있습니다. Application은 이 타입을 import하지 않습니다.

Presentation dependency는 이미 조립된 유스케이스 또는 요청 단위 factory만 소비합니다. SLA 대시보드처럼 보고서 저장소와 Jira 포트가 함께 필요한 유스케이스도 라우터에서 생성하지 않고 `Container.get_sla_dashboard()`가 조립합니다.

### Bootstrap

`src/bootstrap/container.py`는 설정에 맞는 adapter와 유스케이스 factory를 구성합니다. 전역 singleton이나 `app.state.container` service locator로 노출하지 않습니다. `main.py`가 프로세스 수준 `Database`, `Container`, `JobRunner`, scheduler와 `ApiServices`를 만들고 lifespan 종료 순서에 맞게 닫습니다.

런타임 설정은 `main.py`에서 한 번 해석해 adapter 생성자에 전달합니다. Infrastructure adapter는 `get_settings()`를 다시 호출하거나 자체 singleton factory를 만들지 않습니다.

## 트랜잭션과 리소스 수명

요청 단위 DB 유스케이스는 `Database.session()` context manager 안에서 만들어집니다. 정상 종료 시 commit, 예외 시 rollback이며 엔진은 FastAPI lifespan 종료 때 dispose됩니다. Jira와 Gemini HTTP client, 보고서 캐시, 잡 task도 각 소유자의 `aclose()`에서 정리됩니다. `Container`는 AI 포트의 수명을 소유하며, `AsyncExitStack`으로 한 리소스의 종료가 실패해도 나머지 종료를 수행합니다. Gemini SDK의 동기·비동기 전송 리소스 해제는 어댑터 안에서 처리합니다.

파일시스템과 LibreOffice 같은 동기 I/O는 `StorageUseCase`가 `asyncio.to_thread` 경계를 통해 호출하므로 이벤트 루프를 차단하지 않습니다.

## 잡 실행과 SSE

`JobRunner.submit()`은 lock 안에서 실행권을 원자적으로 예약하고 중복 제출에는 `JobAlreadyRunningError`를 발생시킵니다. FastAPI `BackgroundTasks`가 아니라 JobRunner가 생성한 `asyncio.Task`를 추적하고 종료 시 취소·회수합니다. 저장소 I/O와 보고서 생성은 lock 밖에서 실행됩니다.

SSE는 조회한 `JobStatus`를 `wait_for_update()`에 전달합니다. 실행기는 대기자를 등록하기 전후로 상태를 다시 확인해 lost notification을 막고, 대기자 set은 종료 시 제거합니다.

## 검증

### 2026-10-06 성능 검토

백엔드 실행 코드 135개 파일과 운영 스크립트 10개, 마이그레이션 15개를 대상으로 의존 관계, 반복 처리, DB 조회, 외부 요청, 비동기 작업과 리소스 수명을 검토했습니다. 프런트엔드 실행 코드 153개 파일, 스타일과 빌드·배포 설정도 함께 검토했습니다.

보고서 이력 API는 `GetReportUseCase.get_summaries()`와 `ReportRepository.find_summaries()`를 사용합니다. SQL adapter는 위젯 JSON을 조회하거나 복원하지 않고 요약에 필요한 열만 읽습니다. 기존 상세 조회와 전체 `Report`를 반환하는 `find_all()` 계약은 유지하며, 다른 저장소 구현에는 기존 전체 조회를 사용하는 기본 요약 구현을 제공합니다. 이력 응답 필드, 정렬, 페이지 처리, 시간대와 인증 계약은 동일합니다.

이슈 관리의 표시 목록은 성공한 Jira 동기화 또는 KST 날짜 변경 시 다시 계산합니다. 응답마다 별도 `RecentIssueDetail` 객체를 만들어 호출자의 변경이 이후 응답에 영향을 주지 않도록 합니다. Jira 동기화 주기, 증분 병합, 시간별 삭제 반영, 오류 시 기존 목록 유지와 종료 시 작업 취소는 유지합니다. 위젯 복원에는 상한이 있는 타입 메타데이터 캐시만 사용하며, 보고서 값과 가변 목록은 공유하지 않습니다.

로컬 DB에서 20건의 이력 조회 결과를 기존 경로와 비교해 응답 일치를 확인했습니다. 같은 데이터의 반복 조회 5회 중앙값은 기존 전체 조회 약 90ms, 요약 조회 약 1ms였습니다. 이는 해당 데이터와 로컬 환경에서 DB 조회 및 객체 가공을 측정한 값이며 운영 서버의 전체 HTTP 응답 시간을 뜻하지 않습니다.

3,000개 이슈 fixture를 동일 프로세스에서 기존 코드와 비교한 반복 조회 중앙값은 이슈 표시 목록 약 35.3ms에서 14.5ms, 위젯 복원 약 44.7ms에서 16.3ms였습니다. 표시 목록 캐시가 준비된 반복 조회 기준이며 최초 처리 시간이나 전체 HTTP 응답 시간을 뜻하지 않습니다. 추가된 표시 목록 캐시는 현재 이슈 수에 비례하는 메모리를 사용합니다.

검증 결과는 백엔드 217개와 프런트엔드 260개 테스트 통과, Python 구문 검사, 프런트엔드 production build, 두 Docker 이미지 build와 Compose 설정 검사입니다. 새 백엔드 이미지에서 lifespan 시작·종료와 health·이력·최신·연간 보고서 API를 확인했습니다. 로컬 화면에서는 검색 결과 52개 이슈의 키를 PDF와 Excel에 담긴 전체 행과 대조했습니다. 프런트엔드는 로컬에 반영했으며, 기존 이슈 캐시를 유지하기 위해 실행 중인 백엔드는 재시작하지 않았습니다. 운영 서버는 배포하지 않았습니다.

Jira 캐시의 만료 정책과 강제 갱신, 외부 요청 동시성, 파일 스트리밍·할당량 검사, 보고서 생성·알림, 인증·SSE 수명은 이번 변경 대상으로 삼지 않았습니다. 이 경로들은 기존 회귀 테스트와 의존·리소스 흐름 검토로 확인했습니다. 모든 외부 서비스와 운영 환경의 실제 실행을 보장하는 검증은 아닙니다.

```bash
cd backend
python -m unittest discover -s tests -v
python -m compileall -q src tests
```
