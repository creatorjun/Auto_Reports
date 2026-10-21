# Frontend 문서 인덱스

문서 기준: 2026-10-21.

현재 소스의 화면·계약을 정리합니다. [루트 README](../../README.md)에 전체 구성과 실행 방법이 있습니다.

| 문서 | 내용 |
|---|---|
| [사용 가이드](USER_GUIDE.md) | 현재 메뉴와 보고서 생성·필터·내보내기 |
| [아키텍처](ARCHITECTURE.md) | 의존 방향, 조립과 I/O 경계 |
| [디렉터리](DIRECTORY.md) | 주요 소스 위치와 확장 지점 |
| [도메인](DOMAIN.md) | 보고서·SLA·재배포 모델과 집계 정책 |
| [인프라](INFRASTRUCTURE.md) | API, 인증, PDF·Excel, 파일 파서 |
| [화면](PRESENTATION.md) | 페이지, 훅, 공통 표시 규칙 |
| [상태](STATE.md) | 캐시, 인증, 테마, 표 설정과 필터 수명 |
| [라우팅](ROUTING.md) | 메뉴 순서, 경로, 인증 가드 |
| [공통 디자인](SHARED.md) | 팔레트·3단계 글꼴·배지·로고 |
| [의존성](DEPENDENCIES.md) | package.json 선언, 빌드·검증 명령 |
| [구조 유지 기준](REFACTORING_NOTES.md) | 변경 이유, 회귀 방지와 유지보수 점검 |
| [데이터 흐름](data-flow.md) | 보고서별 수집·저장·표시 흐름 |
| [컴포넌트](components.md) | 공통 필터, 표, 차트, 내보내기·미리보기 |
| [보안 뉴스](../../backend/docs/13_security_news.md) | 공개 보안 정보 검색·필터, 출처 상태와 갱신 범위 |

백엔드 계약: [API](../../backend/docs/02_api_reference.md), [SLA 위반](../../backend/docs/08_sla_violation_report.md), [재배포 현황](../../backend/docs/09_redeployment_report.md), [감사로그](../../backend/docs/07_audit_logs.md), [운영](../../backend/docs/10_operations.md).

집중 관리 항목은 **SLA 현황 → SLA 위반 → 재배포 현황** 순서입니다. `/sla-status`의 SLA 현황은 잔여율 0% 이상 30% 미만인 미위반 티켓의 현재 수집 스냅샷이며, `/sla-violations`의 SLA 위반은 기간별로 생성·저장한 보고서입니다. 사용과 필터 기준은 [사용 가이드](USER_GUIDE.md), 조회·갱신 경계는 [데이터 흐름](data-flow.md)을 참고하세요.

## 검증

frontend 디렉터리에서 `pnpm install --frozen-lockfile`, `node --test tests/*.test.mjs`, `pnpm build`를 실행합니다. `pnpm test` 단일 스크립트는 없으며 전체 회귀 검사는 Node 명령을 사용합니다. 기능별 명령은 [의존성 문서](DEPENDENCIES.md#검증-명령)에 정리했습니다.

PDF·Excel은 대시보드·저장 보고서·연간 보고서·전체 이슈에서 지원합니다. 내보내기 시작 시 조건과 전체 일치 행을 고정하고 페이지 번호로 제한하지 않습니다. 독립 SLA 현황·SLA 위반·재배포 현황 페이지에 전용 PDF·Excel 내보내기는 없습니다.
