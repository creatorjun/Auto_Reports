# 구조 유지·검수 기준

문서 기준: 2026-10-14 · 구현 커밋 `e280b75`.

2026-10-14 소스의 책임 분리와 회귀 검사 위치입니다. 과거 리팩터링 결과 목록을 현재 구현의 유지 기준으로 정리했으며, 이 표 자체가 신규 운영 실행 검증 결과는 아닙니다.

| 유지할 계약 | 소유 위치와 검사 |
|---|---|
| Domain은 표준 라이브러리, Application은 Domain·Application만 참조 | `tests/test_architecture.py` |
| 외부 연동·저장 계약은 Application 포트, HTTP 모델은 Presentation | `application/ports`, `presentation/mappers`, `presentation/schemas` |
| 구체 구현과 수명 조립은 진입점 | `bootstrap/container.py`, `main.py`, `tests/test_container_lifecycle.py` |
| DB 정상 commit·예외 rollback·종료 dispose | `infrastructure/persistence/database.py` |
| frozen 사이트 하위 엔티티는 replace 후 aggregate 저장 | `tests/test_site_use_case.py` |
| job 예약 중복 방지, lock 밖 I/O, SSE 대기자 종료 | `tests/test_job_runner.py` |
| 알림 유스케이스와 HTML 렌더링 분리 | `application/ports/issue_notification_renderer_port.py`, `presentation/email/issue_notification_renderer.py` |
| 잘못된 상태 이력만 단계별 시간에서 제외, 외부 요청 오류 전파 | `application/widgets/resolution_collector.py` |
| 일반·연간 scope와 최신 조회·보존 구분 | `application/use_cases/generate_report.py`, `application/use_cases/refresh_report.py`, `infrastructure/persistence/report_repository_impl.py` |
| SLA 생성일 범위·위반 이력·저장 스냅샷 유지 | `tests/test_sla_violation_workflow.py` 및 `test_sla_violation*.py` |
| 재배포 완료/진행 중 분리·08시 기준·당일 대체·중복 방지 | `tests/test_redeployment_report.py` |

위 표의 소스 경로는 `backend/src` 기준이며 테스트 경로는 `backend` 기준입니다. 정확한 구현 파일과 모든 회귀 검사는 [아키텍처](01_architecture.md), [데이터 모델](03_data_model.md) 및 각 기능 문서를 함께 확인합니다.

## 운영 설정과 접근 제어

일반 API 인증은 `LOGIN`, 감사로그는 추가 `SUPERADMIN` 검사를 사용합니다. HTTPS 환경의 `COOKIE_SECURE`, 사이트 접속 정보의 `CREDENTIAL_ENCRYPTION_KEY`, 실제 origin의 `CORS_ORIGINS`를 배포 환경에 맞게 설정합니다. access token은 현재 브라우저 localStorage에 보존되며 이를 HttpOnly 전용 인증으로 설명하지 않습니다.

파일 시스템·문서 변환 동작은 thread 경계와 adapter가 소유합니다. HTTP client, 캐시 task, 이슈 동기화 task, job, DB engine과 로그 핸들러는 소유 객체가 종료합니다. 새 기능 추가 시 정상·예외·취소 경로의 수명을 함께 확인합니다.

## 변경 검증

```bash
cd backend
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

문서 변경만으로 운영 API·DB를 변경하지 않습니다. 기능 수정 시 관련 회귀 검사, 전체 경계 검사, 필요한 실제 서비스 검증을 구분하여 기록합니다. 오래된 성능 측정치를 현재 운영 성능으로 인용하지 않습니다.
