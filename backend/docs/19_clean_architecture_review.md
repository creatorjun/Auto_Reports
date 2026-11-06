# 전체 클린 아키텍처 검토

검토일: 2026-10-29.

## 검토 범위와 방법

수정 후 `backend/src` Python 252개와 `frontend/src` TypeScript·TSX 238개 전체에 정적 계층 검사를 수행했습니다. 백엔드 운영 스크립트 13개와 Alembic Python 파일 25개도 구문·의존성 목록에 포함했습니다. 임시 발표자료 생성 코드와 산출물, 설치된 외부 라이브러리는 서비스 아키텍처 범위에서 제외했습니다.

전수 정적 검사와 함께 보고서 생성·차트 상세·재배포 수집, 파트너 조회, 이슈 동기화, SLA 상세 조회, 저장소·인증·검색, API와 조립 진입점, 프론트엔드 서비스 주입·내보내기 경계를 대조했습니다. 모든 파일의 모든 업무 규칙을 형식 검증했다는 의미는 아닙니다.

| 계층 | 백엔드 | 프론트엔드 | 확인한 경계 |
|---|---:|---:|---|
| Domain | 31 | 30 | 역방향 의존, 프레임워크 의존, 공급자 문법·출력 형식 책임 |
| Application | 91 | 16 | 포트, 유스케이스, 쿼리 생성, 외부 I/O와 런타임 의존 |
| Infrastructure | 78 | 22 | 포트 구현, 외부 형식 변환, 캐시·저장소, 프레젠테이션 역참조 |
| Presentation | 47 | 167 | HTTP·화면 어댑터, 유스케이스 위임, 직접 네트워크 호출 |
| 조립·진입점 | 5 | 3 | 구현체 생성과 주입, 운영 스크립트 호환성 |

## 발견한 위반과 수정

| 문제 | 수정 |
|---|---|
| Application의 구체 `WidgetQueryBuilder`가 Jira 문법과 외부 필드 설정을 소유 | 구현과 `QueryConfig`를 `infrastructure/external`로 이동. Application에는 `ReportQueryPort`와 `ResolvedQueries` 계약을 두고 bootstrap에서 구현을 주입 |
| 재배포 수집기가 정렬 JQL을 직접 연결 | `w15_redeployment_details()` 계약으로 위임 |
| 파트너·SLA·이슈 동기화 유스케이스가 JQL을 직접 생성 | 불변 `IssueSelection`과 `IssueOrder`로 조회 의도를 전달. `JiraClient` 경계에서만 JQL로 변환 |
| Domain이 PDF·Excel의 색상·SVG·표 너비 DTO를 소유 | `application/dto/DashboardExport.ts`로 옮기고 포트·화면·내보내기 어댑터의 참조 갱신 |
| 계층 검사에서 조립 루트 재참조와 core 전체 브라우저 API 사용의 일부 누락 | 백엔드 `main`, 프론트엔드 `main.tsx` 명시 확장자까지 검사. core 전체의 DOM 타입·브라우저 API 사용과 JQL 생성 검사 추가 |

`IssueSelection` 변환은 계정 ID의 따옴표·역슬래시 이스케이프를 맡습니다. 빈 작성자/키 선택과 잘못된 키·조회 기간이 무제한 조회로 변환되지 않도록 거부합니다. 기존 정상 입력의 조회 조건·정렬·캐시 키는 유지합니다.

보고서의 `jql`·`source_jqls`는 조회 근거를 보존하는 기존 데이터 계약이므로 유지했습니다. 기존 문자열 쿼리도 어댑터가 계속 받습니다. 핵심 계층은 해당 문자열의 Jira 문법을 생성하거나 해석하지 않습니다. HTTP 응답, DB 스키마, 보고서 저장 형식은 바꾸지 않았습니다.

2026-10-21 검토에서 유지했던 Application의 JQL 생성은 이번 검토에서 분리했습니다. 예전 검토 문서의 해당 설명은 당시 상태를 기록한 것입니다.

## 검증

- 백엔드 전체: 1,299개 발견, 1,246개 통과, 53개 생략, 실패 0개.
- 생략 사유: 격리 PostgreSQL 연결이 필요한 테스트 51개, POSIX/Linux 전용 테스트 2개. 해당 환경의 통합 검증은 수행하지 않았습니다.
- 새 쿼리 경계 테스트 6개: 기존 문법 호환, 이스케이프, 빈/잘못된 선택 거부, 모든 조회 진입점의 HTTP payload, 문자열/구조화 조건 간 캐시 공유.
- 프론트엔드 전체 694개 통과, 실패·생략 0개. TypeScript·Vite 프로덕션 빌드 통과. PDF 라이브러리의 큰 번들 경고는 남아 있습니다.
- 운영 스크립트의 쿼리 설정 생성자 호환 검사 통과. 운영 보정 스크립트나 실제 Jira 변경 요청은 실행하지 않았습니다.

로컬 실행 증거와 전체 소스 목록은 `output/clean-architecture-validation/`에 있습니다. Python 3.12의 로컬 `venv`와 프론트엔드 lockfile 의존성으로 실행했습니다. 코드 검증 결과이며 운영 배포 결과가 아닙니다.

```powershell
cd backend
..\venv\Scripts\python.exe -m unittest discover -s tests
cd ../frontend
node --test tests/*.test.mjs
pnpm build
```
