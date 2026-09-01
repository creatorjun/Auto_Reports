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
- `infrastructure`는 포트를 구현하고 SQLAlchemy, httpx, APScheduler, 파일시스템을 소유합니다.
- `presentation`은 HTTP와 Pydantic 변환만 담당하고 구체 인프라 구현을 알지 못합니다.
- `bootstrap`과 `main.py`만 양쪽의 구체 구현을 조립합니다.

이 규칙은 `backend/tests/test_architecture.py`가 AST import graph로 검사합니다.

## 레이어별 구성

### Domain

`src/domain/entities`와 `src/domain/value_objects`가 보고서, 잡, 사이트, 위젯 모델과 핵심 값을 정의합니다. `constants.py`는 KST와 도메인 기본값을 제공합니다. 저장소 인터페이스나 외부 서비스 계약은 Domain에 두지 않습니다.

### Application

`src/application/ports`에 Jira, Service Desk, AI, 이메일, 저장소, 캐시, 인증 토큰, 감사, 파일 저장소와 변환기, 잡 실행 계약이 있습니다. `use_cases`는 이 추상화만 조합하며 FastAPI 요청 객체, SQLAlchemy 세션, APScheduler, 로컬 경로를 받지 않습니다.

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

요청 단위 DB 유스케이스는 `Database.session()` context manager 안에서 만들어집니다. 정상 종료 시 commit, 예외 시 rollback이며 엔진은 FastAPI lifespan 종료 때 dispose됩니다. Jira HTTP client, 보고서 캐시, 잡 task도 각 소유자의 `aclose()`에서 정리됩니다.

파일시스템과 LibreOffice 같은 동기 I/O는 `StorageUseCase`가 `asyncio.to_thread` 경계를 통해 호출하므로 이벤트 루프를 차단하지 않습니다.

## 잡 실행과 SSE

`JobRunner.submit()`은 lock 안에서 실행권을 원자적으로 예약하고 중복 제출에는 `JobAlreadyRunningError`를 발생시킵니다. FastAPI `BackgroundTasks`가 아니라 JobRunner가 생성한 `asyncio.Task`를 추적하고 종료 시 취소·회수합니다. 저장소 I/O와 보고서 생성은 lock 밖에서 실행됩니다.

SSE는 조회한 `JobStatus`를 `wait_for_update()`에 전달합니다. 실행기는 대기자를 등록하기 전후로 상태를 다시 확인해 lost notification을 막고, 대기자 set은 종료 시 제거합니다.

## 검증

```bash
cd backend
python -m unittest discover -s tests -v
python -m compileall -q src tests
```
