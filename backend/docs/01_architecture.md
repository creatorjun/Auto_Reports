# Backend Architecture

문서 기준: 2026-10-21. 전체 검토 범위와 수정 근거는 [백엔드 아키텍처 검토](17_backend_architecture_review.md)를 참고하세요.

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
- 저장소, 외부 API, 토큰, 캐시, 감사 로그, 파일 변환과 알림 렌더링 계약은 Application 포트입니다.
- 외부 API 포트는 공급자의 원시 JSON을 반환하지 않고 `JiraIssue`, `JiraComment`, `PartnerMember` 같은 내부 경계 타입을 반환합니다.
- `infrastructure`는 포트를 구현하고 SQLAlchemy, httpx, APScheduler, 파일시스템을 소유합니다.
- `presentation`은 HTTP·Pydantic 변환과 알림 레이아웃을 담당하고 구체 인프라 구현을 알지 못합니다.
- `bootstrap`과 `main.py`만 양쪽의 구체 구현을 조립합니다.

이 규칙은 `backend/tests/test_architecture.py`가 AST import graph와 구체 유스케이스 조립, 공급자 필드 ID, HTTP 작업 제출 경계로 검사합니다. import 검사만으로 업무 책임과 비동기 수명이 보장되지는 않으므로 유스케이스·취소·저장소 테스트를 함께 실행합니다.

## 레이어별 구성

### Domain

`src/domain/entities`와 `src/domain/value_objects`가 보고서, 잡, 사이트, 위젯 모델과 핵심 값을 정의합니다. `constants.py`는 KST와 도메인 기본값을 제공합니다. 저장소 인터페이스나 외부 서비스 계약은 Domain에 두지 않습니다.

### Application

`src/application/ports`에 Jira, Service Desk, AI, 이메일, 저장소, 캐시, 인증 토큰, 감사, 파일 저장소와 변환기, 잡 실행 계약이 있습니다. `use_cases`는 이 추상화만 조합하며 FastAPI 요청 객체, SQLAlchemy 세션, APScheduler를 받지 않습니다.

일반 Jira 포트의 필드 선택은 `JiraIssueField`로 표현합니다. `issuetype`, `resolutiondate`, `customfield_*`, SLA cycle, ADF와 rendered HTML 같은 공급자 표현은 Infrastructure의 `JiraClient`와 전용 SLA·재배포 source adapter에서 내부 경계 타입으로 변환합니다. Application은 원시 Jira JSON을 해석하지 않습니다. Jira/Confluence 통합 검색도 `SearchUseCase`를 통과합니다.

보고서 위젯 수집기는 생성·갱신 경계에서 정한 기준 시각을 전달받습니다. `ReportAssembler`는 조회 범위의 종료 시각(`now`)과 실제 수집 시각(`collected_at`)을 구분합니다. 최근 이슈의 경과일 등은 수집 시각을 사용하므로 과거 기간을 다시 생성해도 과거 시점의 상태를 완전히 재현하는 것은 아닙니다. 저장된 데이터만 다시 조회하는 것과 Jira를 재수집하는 것을 구분합니다.

사이트 하위 엔티티 갱신은 frozen dataclass를 직접 변경하지 않고 `dataclasses.replace`로 새 값을 만든 뒤 aggregate 전체를 저장합니다. 없는 aggregate나 하위 엔티티는 `EntityNotFoundError`로 표현하고 HTTP 404 매핑은 바깥 레이어에서 수행합니다.

할일·TAC 담당자 알림 유스케이스는 대상 이슈 선택, 라이선스 제외, 중복 알림 관리와 발송 요청을 담당합니다. 메일 HTML은 `IssueNotificationRendererPort`에 위임하며, Application은 HTML 레이아웃과 구체 렌더러를 알지 못합니다.

SLA 일일 알림은 `SlaDigestSourcePort`가 제공한 Jira 현재 주기의 목표·잔여 시간과 티켓 전체 위반 이력으로 `NotifySlaDigestUseCase`가 대상을 선택합니다. `SlaDigestRendererPort`는 단계별 HTML을 렌더링하고 기존 `EmailPort`로 한 통을 전송합니다. `Container`가 구현을 조립하며 소유한 HTTP 클라이언트를 종료합니다. 스케줄러는 보고서 생성·갱신과 독립적으로 매일 09:00 KST 실행합니다.

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

`presentation/email/issue_notification_renderer.py`는 알림 레이아웃을 렌더링합니다. `Container`가 이 구현을 알림 유스케이스에 주입하며, 기준 시각은 유스케이스가 전달합니다. SMTP 전송은 기존 Email 포트와 Infrastructure adapter를 그대로 사용합니다.

Presentation dependency는 이미 조립된 유스케이스 또는 요청 단위 factory만 소비합니다. 장기 이슈처럼 보고서 저장소와 Jira 포트가 함께 필요한 유스케이스도 라우터에서 생성하지 않고 `Container.get_sla_dashboard()`가 조립합니다.

### Bootstrap

`src/bootstrap/container.py`는 설정에 맞는 adapter와 유스케이스 factory를 구성합니다. `WidgetCollectorFactory`도 bootstrap에서 수집기를 조립합니다. 재배포용 Jira 필드 ID는 Infrastructure가 소유하며 JQL 필드 참조를 `QueryConfig`에 주입합니다. 전역 singleton이나 `app.state.container` service locator로 노출하지 않습니다. `main.py`가 프로세스 수준 `Database`, `Container`, `JobRunner`, scheduler와 `ApiServices`를 만들고 lifespan 종료 순서에 맞게 닫습니다.

개인정보 보고는 `PersonalDataReportingService`가 소유자 승인 상태, 재시도, 삭제·최신 이름 갱신, 수집과 보고 순서를 관리합니다. DB 스냅샷과 PostgreSQL advisory lock은 output port 구현이며, repository와 외부 API 및 유스케이스 조립은 Container에서 수행합니다. 로그인 알림 권한은 조회·해제 계약과 레거시 OAuth 쓰기 계약을 분리하여 영속 로그인에 지원하지 않는 저장 메서드를 요구하지 않습니다.

번역 재시도 간격, 요청 한도 오류에 대한 시도 횟수 복원과 안내는 Application 정책입니다. SQLite adapter는 같은 트랜잭션 안에서 현재 상태를 읽고 정책 결과를 반영하며 예약·완료의 원자성을 유지합니다. AI 입력 요약과 샘플링도 Application이 소유하고 도메인 위젯은 프롬프트를 렌더링하지 않습니다.

런타임 설정은 `main.py`에서 한 번 해석해 adapter 생성자에 전달합니다. Infrastructure adapter는 `get_settings()`를 다시 호출하거나 자체 singleton factory를 만들지 않습니다.

## 트랜잭션과 리소스 수명

요청 단위 DB 유스케이스는 `Database.session()` context manager 안에서 만들어집니다. 정상 종료 시 commit, 예외 시 rollback이며 엔진은 FastAPI lifespan 종료 때 dispose됩니다. Jira와 Gemini HTTP client, 보고서 캐시, 잡 task도 각 소유자의 `aclose()`에서 정리됩니다. `Container`는 AI 포트의 수명을 소유하며, `AsyncExitStack`으로 한 리소스의 종료가 실패해도 나머지 종료를 수행합니다. Gemini SDK의 동기·비동기 전송 리소스 해제는 어댑터 안에서 처리합니다.

`Container.open()`은 초기화 완료 전부터 정리 범위를 설정합니다. 중간 생성 실패 시 이미 생성한 자원을 회수하며, 하나의 종료 오류가 나머지 자원 정리를 막지 않습니다. DB 엔진은 별도로 main이 소유합니다.

캐시의 공유 조회 작업은 캐시가 소유합니다. 개별 요청 취소는 다른 대기자에게 전파되지 않고, 무효화·종료는 이전 작업을 취소하여 늦게 반환된 값의 재삽입을 막습니다. 보고서 캐시의 백그라운드 조회는 Container에서 주입한 callback이 독립 DB 세션을 열고 닫습니다. HTTP 요청의 repository 세션을 백그라운드 작업에 넘기지 않습니다.

파일시스템과 LibreOffice 같은 동기 I/O는 `StorageUseCase`가 `asyncio.to_thread` 경계를 통해 호출하므로 이벤트 루프를 차단하지 않습니다.

## 잡 실행과 SSE

`TriggerReportUseCase`는 수동 보고서의 일간 및 전체 주간·월간·연간 기간, 최근 저장본 재실행, 캐시 우회와 작업 제출을 담당합니다. HTTP 라우트는 요청·응답, 오류와 감사 로그를 처리합니다.

`JobRunner.submit()`은 lock 안에서 실행권을 원자적으로 예약하고 중복 제출에는 `JobAlreadyRunningError`를 발생시킵니다. 예약 저장 도중 요청이 취소되어도 실행권을 해제합니다. FastAPI `BackgroundTasks`가 아니라 JobRunner가 생성한 `asyncio.Task`를 추적하고 종료 시 취소·회수합니다. 저장소 I/O와 보고서 생성은 lock 밖에서 실행됩니다.

SSE는 조회한 `JobStatus`를 `wait_for_update()`에 전달합니다. 실행기는 대기자를 등록하기 전후로 상태를 다시 확인해 lost notification을 막고, 대기자 set은 종료 시 제거합니다.

## 보고서와 캐시의 경계

일반·연간 보고서는 `ReportScope`로 구분하고 `JobRunner`와 `ReportAssembler`를 공유합니다. 생성은 새 행을 저장하며 주기 갱신은 최신 일반 보고서와 현재 연도 전용 보고서의 위젯을 같은 ID에 갱신합니다. `scope=annual`은 최신 일반 보고서 조회와 자동 보존 정리에서 제외됩니다.

SLA 위반은 `SlaViolationReportUseCase`가 기간별 티켓 수집과 저장을 담당하며 일반 보고서 job/SSE와 분리된 HTTP 요청입니다. 재배포 현황은 별도 수집·저장 포트와 DB advisory lock을 사용하고, 스케줄러는 매일 08시 KST 및 시작 시 보충 작업을 등록합니다. 자세한 동시성·저장 계약은 [SLA](08_sla_violation_report.md)와 [재배포](09_redeployment_report.md)에 있습니다.

전체 이슈와 SLA 현황은 저장소 포트가 제공한 DB 스냅샷을 복구하고 유스케이스가 백그라운드 갱신을 관리합니다. 전체 이슈는 30초 최소 갱신 간격, 2분 중첩 증분 조회, 1시간 경과 후 전체 재수집을 사용합니다. 응답의 목록 객체는 복사하여 호출자 변경이 내부 캐시를 오염시키지 않게 합니다.

일반 보고서 w14의 상태 이력 계산은 잘못된 티켓 이력의 `ValueError`만 잡아 해당 이슈의 단계별 시간에서 제외하고 로그를 남깁니다. Jira 요청 실패·잘린 페이지 같은 공급자 오류는 전파합니다. SLA 위반의 불완전 이력은 위반 티켓 자체를 제외하지 않고 미확인 상세·경고로 보존합니다. 두 계약을 혼동하지 않습니다.

보고서 목록 조회는 `find_summaries()`에서 위젯 JSON을 읽거나 복원하지 않습니다. 저장 위젯 복원은 타입 메타데이터만 제한적으로 캐시하고 가변 보고서 값을 전역 공유하지 않습니다.

## 검증

현재 구조의 유지 기준은 [검수 기준](05_issue_catalog.md)에 정리합니다. 과거 특정 날짜의 파일 수·벤치마크·테스트 통과 수는 현재 배포 보증으로 사용하지 않습니다.

```bash
cd backend
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

운영 반영은 이 검사와 별도로 이미지 기동, DB revision, health와 필요한 실제 Jira 수집을 확인합니다. [운영 가이드](10_operations.md)를 참고하세요.
