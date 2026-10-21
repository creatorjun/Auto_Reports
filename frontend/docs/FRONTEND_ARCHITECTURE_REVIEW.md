# 프론트엔드 클린 아키텍처 검토

검토일: 2026-10-21. 기준 커밋: `6f9fca7df4e6ab952e8692176d54237faa87b23e`.

## 범위와 방법

기준 소스의 TypeScript·TSX 223개 파일 전문을 검토했습니다. CSS 4개와 디자인 토큰 JSON, 라우터·조립 진입점, 빌드·배포 설정 및 관련 테스트를 함께 확인했습니다. 새 업로드 서비스가 추가되어 변경 후 TypeScript·TSX는 224개입니다.

| 경계 | 기준 파일 수 | 검토 내용 |
|---|---:|---|
| Domain | 30 | 모델·업무 정책·필터·정렬의 외부 의존 |
| Application | 13 | 유스케이스·gateway·취소·바이너리·업로드 계약 |
| Infrastructure | 21 | HTTP·인증·SSE·파서·PDF/Excel·자원 수명 |
| Presentation | 156 | 화면 20, 훅 19, 컨텍스트 4, 상태 4, 컴포넌트 95, 설정 8, 유틸리티 6 |
| App·조립 진입점 | 3 | 라우팅·권한·서비스 주입 |

AST로 상대·별칭·동적 import 그래프를 확인하고 실제 호출 경로 및 비동기 자원의 생성·종료를 추적했습니다. 역방향 레이어 의존과 내부 순환 참조는 발견되지 않았습니다. 아래 수정은 폴더 이름이나 파일 크기가 아닌 실제 책임 혼합과 수명 위반에 한정합니다.

```text
main.tsx → Infrastructure adapters → Application ports → Domain
        → Presentation providers/hooks/components → Application services
app     → Presentation routes/layout
```

## 확인한 문제와 수정

| 문제 | 수정 | 검증 시나리오 |
|---|---|---|
| 연간 전용 화면이 과거 연도 전체·현재 연도 오늘까지 집계 정책을 직접 계산 | `reportPeriod.annualReportDateRange`로 이동 | 과거·현재·미래 연도, KST 날짜 경계, 기존 생성 요청 |
| 업로드 훅이 용량·일괄 처리 정책을 소유하고 `allSettled` 실패를 무시 | `storageUploads` Application service에서 용량·파일별 결과 처리, 실패 파일명 전달 | 일부 실패, 용량 부족, 성공 파일 유지 |
| 업로드 사전 검사 중 중복 실행과 화면 종료 후 타이머·요청 잔존 | 훅이 단일 실행·취소·진행 표시·타이머를 소유, gateway에 선택적 취소 계약 전달 | 동시 실행, unmount, 로그아웃, 청크 읽기 중 취소·임시 업로드 정리 |
| 종료된 보고서 subscription이 늦은 polling 응답을 전달하거나 다시 timer 생성 | adapter 소유 AbortController, await 이후 active 확인, 한 번의 polling 전환, 폐기된 SSE 무시 | close·deadline 이후 성공/실패, 중복 SSE 오류, 정상 완료·재시도 |
| 이전 인증 세션의 HTTP 200 응답과 캐시 취소 후 완료 처리가 새 세션에 유입 | HTTP 성공 응답에도 인증 세대 확인, Presentation 세션 버전·Layout 생존 확인 | 로그아웃·새 로그인 후 늦은 조회/생성 응답, cache clear 중 완료, 일반 메뉴 이동·토큰 갱신 유지 |
| 검색 입력 변경·닫기·화면 종료 후 이전 요청이 결과를 다시 표시 | 검색 작업 identity와 취소 신호, debounce·blur 타이머 회수 | 입력 삭제·변경, 연속 전체 검색, Esc·blur·unmount, 정상 결과 표시 |

실패 시나리오는 지연 응답과 제어 가능한 타이머를 사용해 기존 코드에서 먼저 재현했습니다. 실제 HTTP client, React 훅·컴포넌트, QueryClient와 Application service를 대상으로 회귀 검사를 추가했습니다.

## 유지한 계약

- 일반 주·월·연 보고서와 연간 전용 보고서의 기존 집계 범위, 필터·정렬·내보내기 스냅샷을 유지합니다.
- 인증 갱신·로그아웃 직렬화와 기억한 Jira 계정 로그인, 개인정보 보고 연결의 권한 범위를 유지합니다.
- SLA 위반·재배포 생성은 같은 세션의 일반 메뉴 이동 후에도 캐시 반영을 유지합니다.
- HTTP·Blob·File·FormData·SSE·문서 라이브러리는 Infrastructure, 진행 표시·타이머·화면 생존은 Presentation, 업무 정책은 Application에 둡니다.
- `URL` 같은 브라우저·Node 공통 파싱 API, 차트 좌표·표시 비율·라벨·테마·표 UI 정렬을 불필요한 포트로 바꾸지 않습니다.
- 새로운 런타임 의존성, DB migration, 백엔드 변경은 없습니다.

## 검증

변경 전 전체 회귀 검사 554개와 TypeScript·Vite 빌드가 통과했습니다. 변경 후 Windows에서 전체 601개(실패·생략 0개), TypeScript·Vite 프로덕션 빌드 및 diff 검사가 통과했습니다. Linux와 운영 화면 확인 결과는 별도의 배포 기록에 남깁니다.

```bash
node --test tests/*.test.mjs
pnpm build
pnpm test:architecture
pnpm test:auth
pnpm test:storage
pnpm test:report-generation
```

운영 반영은 같은 소스의 Linux 빌드·전체 테스트 후 프론트엔드 컨테이너만 교체합니다. 백엔드·DB 컨테이너, 환경 설정, TLS 설정, DB revision 보존과 공개 HTTPS의 실제 HTML·JavaScript bundle 일치를 확인합니다. 보고서 생성·파일 업로드의 오류 주입은 자동 테스트에서 검증하며 운영 데이터에 시험용 보고서나 파일을 만들지 않습니다.

전문 검토 목록과 실행 증거는 작업 디렉터리의 `output/frontend-architecture-validation/`에 보관합니다. 일반 사용 화면 검증은 자동 테스트 및 소스 검토와 별도의 증거로 기록합니다.
