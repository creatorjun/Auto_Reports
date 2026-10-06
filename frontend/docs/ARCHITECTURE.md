# Frontend Architecture

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

axios 오류는 Infrastructure에서 `RequestError`로 정규화됩니다. Presentation은 axios response 구조를 알지 않고 상태 코드와 detail만 처리합니다.

검색 UI는 자신이 생성한 취소 신호로 요청 수명을 판단하므로 HTTP 라이브러리의 오류 이름에 의존하지 않으며, 취소된 이전 응답이 현재 검색 결과나 로딩 상태를 변경하지 않습니다.

파일 업로드와 바이너리 응답은 Application의 `UploadSource`와 `BinaryContent` 계약을 사용합니다. 따라서 Application 포트는 브라우저 `File`, `Blob`, `AbortSignal` 타입을 알지 않으며, FormData·Blob 수명·미리보기 변환 요청은 Infrastructure adapter가 담당합니다. 바이너리는 필요한 화면에서만 지연 읽고 object URL은 명시적 `close()`로 해제합니다.

텍스트 인코딩과 CSV·Excel·Word 해석은 `PreviewParserPort`와 `infrastructure/preview/filePreviewParser.ts`를 통과합니다. xlsx와 mammoth는 어댑터에서 지연 로딩하며 화면에는 문자열, CSV 행, 시트별 HTML을 반환합니다. `FilePreviewModal`은 주입된 파서를 사용하고 로딩·오류·시트 선택·이전 요청 무시·종료 처리를 소유합니다. PDF canvas와 Markdown 렌더링은 화면 렌더러의 책임으로 유지합니다.

## UI 상태

- 원격 서버 상태: TanStack Query
- 인증, 선택 보고서, 트리거 표시, 사용자 테마: `presentation/state`의 Zustand store
- Jira URL과 Application gateway: `presentation/context`
- 폼과 모달: 컴포넌트 로컬 상태

라이트·다크 팔레트의 실제 색상 값은 `presentation/styles/palette.css` 한 곳에 있고, Tailwind와 Recharts는 동일한 CSS 변수를 사용합니다. 테마 선택은 `themeStore`가 로컬 저장소에 보존하며 `ThemeController`가 문서 루트의 `data-theme`에 반영합니다.

## 잡 진행

보고서 생성 요청 뒤 `reportApi.watchJob()`이 SSE를 우선 사용하고 연결 실패 시 지수 백오프 폴링으로 전환합니다. SSE URL에는 EventSource의 헤더 제한을 고려한 인증 query token이 포함되고 백엔드는 같은 토큰을 검증합니다. `useJobStream`은 Application subscription을 시작·종료하며 컴포넌트 unmount 때 연결과 타이머를 회수합니다.

## 검증

```bash
pnpm test:architecture
pnpm build
```

아키텍처 테스트는 TypeScript AST로 정적·상대·동적 import를 모두 확인하고, Presentation의 직접 네트워크 transport 사용과 Application 포트의 브라우저 파일 객체 누출을 차단합니다.

2026-10-06 검토에서는 기존 실행 코드 153개 파일의 import 그래프와 순환 참조, 조립 지점, 화면·훅·어댑터 호출 경로를 확인했습니다. 대시보드 업무 계산과 파일 형식 해석의 책임을 분리했고, Presentation의 xlsx·mammoth 의존 및 대시보드 집계 함수 재도입을 차단하는 검사를 추가했습니다. 프런트엔드 269개 테스트와 production build가 통과했습니다. 실제 Excel·DOCX 데이터를 사용한 파서 검증, 기존 전체 선택·해제, 필터와 PDF·Excel snapshot 회귀 테스트도 포함합니다.

Docker frontend 이미지 빌드 후 로컬 프런트엔드에 반영했습니다. 실제 2024 연간 보고서에서 전체 해제 시 선택 기간 지표가 0으로 바뀌고, 전체 선택 시 생성 748건·해결 573건으로 복원되는 것을 확인했습니다. 현재 보고서와 연간 비교표의 화면 렌더링도 확인했으며, 운영 서버는 배포하지 않았습니다.
