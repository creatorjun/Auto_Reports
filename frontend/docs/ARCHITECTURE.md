# Frontend Architecture

문서 기준: 2026-10-21.

## 의존성 규칙

```text
main.tsx Composition Root
  ├─ Infrastructure API adapters ──┐
  └─ Presentation service provider ├─> Application ports ─> Domain
                                   └─> Presentation UI
```

- `domain`은 순수 TypeScript 모델이며 React, axios, Zustand를 import하지 않습니다.
- `application`은 Domain 모델을 사용하는 gateway 계약, 프레임워크 독립 오류와 대시보드 집계 서비스를 정의합니다.
- `infrastructure`는 Application gateway를 만족하는 axios adapter와 파일 미리보기 파서를 구현합니다.
- `presentation`은 UI, TanStack Query 훅, 상태와 컨텍스트를 소유하며 구체 API adapter를 import하거나 `fetch`, `EventSource`, `XMLHttpRequest`를 직접 사용하지 않습니다.
- `app`은 라우터와 앱 셸만 담당합니다.
- `main.tsx`만 인증 세션, 구체 API 구현과 파일 미리보기 파서를 조립해 `ApplicationServicesProvider`에 전달합니다.

`frontend/tests/architecture.test.mjs`가 레이어별 허용 import를 검사합니다.

## 서버 데이터 흐름

```text
사용자 액션
  -> Presentation component
  -> Presentation query hook
  -> Application gateway interface
  -> Infrastructure axios adapter
  -> FastAPI
  -> Domain response model
  -> TanStack Query cache
  -> UI render
```

컴포넌트와 훅은 `useApplicationServices()`로 gateway를 받습니다. 따라서 API 구현을 교체하거나 테스트 대역을 제공할 때 Presentation 코드를 수정하지 않습니다.

대시보드의 요청 유형·현재 상태·반기별 건수, SLA 비율과 처리 시간 평균은 `application/services/dashboardData.ts`에서 계산합니다. `useDashboardData`는 보고서별 필터 메타데이터와 선택 조건별 결과를 React `useMemo`로 보관하는 역할만 담당합니다. 연간 비교와 파트너 화면은 순수 `buildDashboardData` 서비스를 직접 사용하므로 React 훅 모듈에 업무 계산을 의존하지 않습니다. 기존 필터 지원 여부, 숨겨진 유형 포함 정책, 과거 데이터 fallback과 계산식은 유지합니다.

## 인증과 오류 경계

`main.tsx`는 `AuthSessionPort`를 구현하는 Zustand store adapter로 HTTP client를 한 번 구성합니다. axios interceptor는 access token을 주입합니다. 동시 401은 하나의 refresh Promise를 공유하며, 실패한 요청을 영구 대기시키지 않고 인증 상태를 지운 뒤 로그인 화면으로 이동합니다.

`LoginPage`, `AdminLoginPage`, `ProtectedRoute`는 `useAuthSession`으로 초기 세션을 복원합니다. 초기 복원도 interceptor와 같은 refresh Promise를 공유합니다. HTTP adapter는 인증 세대 번호로 이전 세션에서 시작한 성공·실패 응답을 차단하며, 로그아웃은 진행 중인 갱신 완료 후 cookie를 제거합니다. Presentation의 `authStore.sessionVersion`은 세션 종료와 새 로그인 시 변경하고 토큰 갱신에서는 유지합니다. SLA 위반·재배포 생성, SLA 현황·보안 뉴스 수동 갱신은 이 값을 캡처하여 같은 세션에만 결과를 반영합니다. 특히 캐시 조회 취소를 기다린 뒤 다시 확인합니다. 일반 보고서 완료 처리는 Layout의 수명이 끝난 뒤 캐시를 다시 만들지 않습니다. `/login`은 Jira 로그인만 표시하고 기존 admin·superadmin 입력은 직접 접속하는 `/admin`에서만 제공합니다. `/admin` 링크는 일반 로그인 화면과 메뉴에 표시하지 않습니다. Jira 인증은 `AuthGateway`를 통해 OAuth를 시작하고 callback은 백엔드에서 처리합니다.

운영 브라우저는 `https://10.1.43.100`에 접속하며 API도 같은 출처를 사용합니다. 서버가 발급한 refresh cookie는 `Secure`·HttpOnly로 전달하고 프런트엔드는 JWT를 영구 저장하지 않습니다. 내부 자체 서명 인증서의 클라이언트 신뢰와 OAuth callback 설정은 [Jira 로그인 운영 가이드](../../backend/docs/11_jira_login.md)에 따릅니다.

axios 오류는 Infrastructure에서 `RequestError`로 정규화됩니다. Presentation은 axios response 구조를 알지 않고 상태 코드와 detail만 처리합니다.

검색 UI는 자동완성과 전체 검색의 현재 작업·취소 신호를 소유합니다. 입력 변경·검색 닫기·unmount 시 이전 작업을 종료하고, 각 await 이후 신호와 요청 identity를 확인합니다. HTTP 라이브러리의 오류 이름에 의존하지 않으며 취소된 이전 응답이 현재 결과·로딩 상태·닫힌 검색창을 변경하지 않습니다.

파일 업로드와 바이너리 응답은 Application의 `UploadSource`와 `BinaryContent` 계약을 사용합니다. 따라서 Application 포트는 브라우저 `File`, `Blob`, `AbortSignal` 타입을 알지 않으며, FormData·Blob 수명·미리보기 변환 요청은 Infrastructure adapter가 담당합니다. 바이너리는 필요한 화면에서만 지연 읽고 object URL은 명시적 `close()`로 해제합니다.

`application/services/storageUploads.ts`는 용량 검증과 파일별 업로드 결과를 조합합니다. 일부 실패를 전체 성공으로 바꾸지 않으며 실패한 파일명을 화면에 전달합니다. `useUploadFiles`는 진행 상태·한 번의 업로드 실행·취소 컨트롤러·완료 타이머를 소유하고 화면 종료 시 정리합니다. `StorageGateway.upload`의 선택적 `CancellationSignal`을 Infrastructure가 HTTP 요청에 연결하며 청크 업로드 실패 시 임시 업로드 정리를 요청합니다.

텍스트 인코딩과 CSV·Excel·Word 해석은 `PreviewParserPort`와 `infrastructure/preview/filePreviewParser.ts`를 통과합니다. xlsx와 mammoth는 어댑터에서 지연 로딩하며 화면에는 문자열, CSV 행, 시트별 HTML을 반환합니다. `FilePreviewModal`은 주입된 파서를 사용하고 로딩·오류·시트 선택·이전 요청 무시·종료 처리를 소유합니다. PDF canvas와 Markdown 렌더링은 화면 렌더러의 책임으로 유지합니다.

## UI 상태

- 원격 서버 상태: TanStack Query
- 인증, 선택 보고서, 트리거 표시, 사용자 테마: `presentation/state`의 Zustand store
- Jira URL과 Application gateway: `presentation/context`
- 폼과 모달: 컴포넌트 로컬 상태

라이트·다크 팔레트의 실제 색상 값은 `presentation/config/designTokens.json` 한 곳에 있고, Tailwind와 Recharts는 동일한 CSS 변수를 사용합니다. 테마 선택은 `themeStore`가 로컬 저장소에 보존하며 `ThemeController`가 문서 루트의 `data-theme`에 반영합니다.

## 잡 진행

보고서 생성 요청 뒤 `reportApi.watchJob()`이 SSE를 우선 사용하고 연결 실패 시 하나의 지수 백오프 폴링으로 전환합니다. SSE URL에는 EventSource의 헤더 제한을 고려한 인증 query token이 포함되고 백엔드는 같은 토큰을 검증합니다. `Layout`의 `ReportGenerationProvider`가 구독을 소유하여 메뉴 이동 중에도 생성을 추적합니다. `useJobStream`은 Application subscription을 시작·종료하며 인증된 layout이 unmount되면 연결과 타이머를 회수합니다. Subscription은 진행 중인 폴링 요청도 취소하고 종료·시간 초과 이후의 응답과 이전 SSE 이벤트를 무시합니다. 완료한 보고서의 scope에 따라 최신 일반 보고서와 연간 전용 보고서 캐시를 구분해 갱신합니다.

## 검증

```bash
pnpm test:architecture
pnpm test:auth
pnpm build
```

아키텍처 테스트는 TypeScript AST로 정적·상대·동적 import를 모두 확인하고, Presentation의 직접 네트워크 transport 사용과 Application 포트의 브라우저 파일 객체 누출을 차단합니다.


## 현재 기능별 계산 경계

대시보드의 `application/services/dashboardData.ts`, 재배포의 `application/services/redeploymentReport.ts`, SLA 위반의 `domain/SlaViolationFilters.ts`·`SlaViolationOverview.ts`·`SlaViolationSort.ts`가 화면과 독립적으로 계산합니다. SLA 위반 요약과 차트 선택은 저장 보고서만 사용하므로 컴포넌트에서 별도 Jira 요청을 만들지 않습니다. 연간 일부 차트 상세는 `ReportGateway.getChartIssues`를 통해 현재 Jira를 조회하는 별도 계약입니다.

SLA 현황은 `domain/SLAStatus.ts`의 현재 스냅샷을 사용합니다. `application/services/slaStatus.ts`가 위젯·검색·상태·SLA 단계 필터와 정렬을 계산하고 `SlaStatusGateway`가 조회 계약을 정의합니다. `infrastructure/api/slaStatusApi.ts`를 `main.tsx`에서 주입하며 `useSlaStatus`가 60초 query 캐시, 수동 강제 새로고침, 요청 취소와 마지막 성공 데이터를 관리합니다. `SlaStatusPage`와 `components/sla-status`는 표시만 담당하며 기간별 저장 보고서를 만들지 않습니다.

일·주·월·연 날짜 계산은 `domain/ReportPeriod.ts`와 `application/services/reportPeriod.ts`를 공유합니다. 연간 전용 화면의 과거 연도 전체·현재 연도 오늘까지 집계 정책도 같은 Application service에 두며 컴포넌트는 반환된 생성 요청을 전달합니다. 일반 보고서 생성은 layout 소유 SSE 구독, SLA 위반·재배포 생성은 각 query mutation의 HTTP 응답으로 완료합니다. SLA 현황은 기간 생성 흐름에 참여하지 않습니다.

테마와 3단계 글자 크기·굵기는 단일 디자인 토큰에서 정의하고, 배지 색상은 의미별 mapping으로 참조합니다. 표의 너비·정렬 영속화는 Presentation의 `useTablePreferences`가 담당하며 Domain 계산이나 API payload에 넣지 않습니다.

과거 특정 검토의 파일 수·테스트 수·브라우저 결과는 현재 기능 보증으로 사용하지 않습니다. 변경 검증은 [구조 유지 기준](REFACTORING_NOTES.md)과 [운영 가이드](../../backend/docs/10_operations.md)에 따라 해당 작업의 결과로 기록합니다.
