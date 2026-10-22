# Backend 문서 인덱스

문서 기준: 2026-10-14 · 구현 커밋 `e280b75`.

2026-10-14 소스 기준입니다. 제품 기능 개요와 구현 커밋은 [루트 README](../../README.md), 화면 사용법은 [사용 가이드](../../frontend/docs/USER_GUIDE.md)를 참고하세요.

| 문서 | 내용 |
|---|---|
| [아키텍처](01_architecture.md) | 레이어 경계, 조립, 트랜잭션과 리소스 수명 |
| [백엔드 아키텍처 검토](17_backend_architecture_review.md) | 2026-10-21 전체 소스 검토 범위, 확인된 책임·수명 위반과 회귀 검사 |
| [백엔드 성능 검토](18_backend_performance_review.md) | 2026-10-21 전체 소스 검토, 기능을 유지한 SQL·HTTP·집계 최적화와 전후 측정 |
| [API](02_api_reference.md) | 인증, 일반·연간 보고서, 차트 상세, SLA·재배포, 전체 이슈와 관리 API |
| [데이터 모델](03_data_model.md) | 저장 테이블, 보고서 scope, JSONB와 migration |
| [환경 설정](04_environment_and_config.md) | 실제 설정 기본값, Compose 적용, 스케줄과 선택 기능 |
| [검수 기준](05_issue_catalog.md) | 유지할 구조적 계약과 기능별 회귀 검사 |
| [감사로그](07_audit_logs.md) | 관리자 권한, 기록, 보존·이전 |
| [SLA 현황](15_sla_status.md) | 잔여율 30% 미만의 위반 임박 티켓과 상태별 체류시간 |
| [SLA 위반](08_sla_violation_report.md) | 생성·집계·저장, 요약·차트·필터, 티켓 상세 |
| [재배포 현황](09_redeployment_report.md) | 수집 기준, 원인·월별 탐색, 매일 08시 KST 갱신 |
| [운영·배포](10_operations.md) | 실행, 백업, migration, 배포와 검증 |
| [Jira 로그인](11_jira_login.md) | OAuth 앱 등록, 기존 관리자 로그인, JWT 자동 로그인과 검증 |
| [SLA 일일 알림](12_sla_digest.md) | 매일 09시 잔여 30% 이하 티켓 요약, 위반 이력 제외, 현재 SLA 설정과 메일 미리보기 |
| [CVE 취약점 대응·보안 뉴스](13_security_news.md) | NVD·CISA KEV 버전 정보, 보안 뉴스 한 줄 요약 목록, 영구 캐시와 호출 제한 |

일반·연간 보고서는 `reports`를 공유하고, SLA와 재배포는 각각 별도 테이블을 사용합니다. SLA 이력은 불변 저장본이고 재배포는 당일 저장본을 대체합니다. API 명세와 화면 필터 건수의 의미는 해당 기능 문서를 함께 확인합니다.

C-Level은 삭제된 기능이며 예전 DB revision 호환을 위한 migration 이력만 유지합니다. Rovo/A2A 연결·분석은 현재 기능이 아닙니다.
