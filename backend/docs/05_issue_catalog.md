# Clean Architecture Audit

검수 기준일: 2026-08-12
검수 범위: `backend/src`, 실행 진입점, 비동기 경계, 리소스 수명, 테스트와 문서

## 수정한 위반

| 항목 | 기존 문제 | 현재 구조 |
|------|-----------|-----------|
| 의존성 역전 | Application mapper가 Presentation Pydantic 스키마를 import | HTTP mapper를 `presentation/mappers`로 이동 |
| 포트 배치 | 외부 시스템과 저장소 계약이 Domain에 혼재 | 모든 유스케이스 경계 계약을 `application/ports`로 이동 |
| 프레임워크 누수 | Storage 유스케이스가 FastAPI `UploadFile`, subprocess, 파일시스템을 직접 사용 | `StoragePort`와 `DocumentConverterPort`를 주입하고 동기 I/O를 thread 경계로 격리 |
| 스케줄러 누수 | Application이 APScheduler를 직접 import | `infrastructure/scheduling` adapter로 이동 |
| Service Locator | 라우터 dependency가 구체 Container와 SQLAlchemy session을 조회 | 명시적 `ApiServices`와 유스케이스 async context factory로 교체 |
| 전역 DB | 모듈 전역 engine과 session factory | lifespan이 소유하는 `Database` 객체로 교체 |
| 잡 결합 | JobRunner가 Container와 SQLAlchemy를 직접 알고 FastAPI가 task를 소유 | 생성 callback과 repository 포트 주입, JobRunner가 task 수명 소유 |
| 동시성 | lock을 잡은 채 저장소 I/O, 제출 검사와 실행 예약 사이 race | lock은 원자적 예약에만 사용하고 외부 I/O는 lock 밖에서 실행 |
| 알림 | Event set/clear 타이밍으로 SSE 알림 유실 또는 dictionary 잔류 가능 | 알려진 상태 재검사와 실제 대기자 set으로 교체 |
| 불변식 위반 | Presentation이 frozen 하위 dataclass를 `setattr`로 변경 | SiteUseCase가 `replace`로 aggregate를 갱신 |
| 오류 매핑 | 유스케이스의 존재하지 않음 처리가 HTTP 예외와 결합 | Application 오류를 전역 HTTP handler가 404/409로 매핑 |
| 수명 관리 | HTTP client, cache background task, DB engine 종료 책임 불명확 | 각 adapter의 `aclose`와 lifespan 종료 순서를 명시 |

## 유지해야 할 운영 보안 조건

- 운영에서는 `COOKIE_SECURE=true`를 사용하고 HTTPS를 강제합니다.
- `CREDENTIAL_ENCRYPTION_KEY`가 없으면 사이트 접속 자격증명을 암호화하지 않으므로 운영 배포 전에 Fernet 키를 반드시 설정합니다.
- 브라우저 access token은 현재 localStorage에 있으므로 CSP와 XSS 방어를 유지하고, 외부 노출 범위가 커지면 메모리 저장 또는 HttpOnly cookie 전환을 검토합니다.

## 회귀 방지

`backend/tests/test_architecture.py`가 내부 레이어의 프레임워크 import와 의존 방향을 검사합니다. `test_site_use_case.py`와 `test_job_runner.py`는 불변 하위 엔티티 갱신, 없는 엔티티 오류, 알림 race와 잡 완료 상태를 검증합니다.
