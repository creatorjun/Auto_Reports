# Frontend Architecture

## 의존성 규칙

```text
main.tsx Composition Root
  ├─ Infrastructure API adapters ──┐
  └─ Presentation service provider ├─> Application ports ─> Domain
                                   └─> Presentation UI
```

- `domain`은 순수 TypeScript 모델이며 React, axios, Zustand를 import하지 않습니다.
- `application`은 Domain 모델을 사용하는 gateway 계약과 프레임워크 독립 오류만 정의합니다.
- `infrastructure`는 Application gateway를 만족하는 axios adapter입니다.
- `presentation`은 UI, TanStack Query 훅, 상태와 컨텍스트를 소유하며 구체 API adapter를 import하지 않습니다.
- `app`은 라우터와 앱 셸만 담당합니다.
- `main.tsx`만 인증 세션과 구체 API 구현을 조립해 `ApplicationServicesProvider`에 전달합니다.

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

## 인증과 오류 경계

`main.tsx`는 `AuthSessionPort`를 구현하는 Zustand store adapter로 HTTP client를 한 번 구성합니다. axios interceptor는 access token을 주입합니다. 동시 401은 하나의 refresh Promise를 공유하며, 실패한 요청을 영구 대기시키지 않고 인증 상태를 지운 뒤 로그인 화면으로 이동합니다.

axios 오류는 Infrastructure에서 `RequestError`로 정규화됩니다. Presentation은 axios response 구조를 알지 않고 상태 코드와 detail만 처리합니다.

## UI 상태

- 원격 서버 상태: TanStack Query
- 인증, 선택 보고서, 트리거 표시, 사용자 테마: `presentation/state`의 Zustand store
- Jira URL과 Application gateway: `presentation/context`
- 폼과 모달: 컴포넌트 로컬 상태

라이트·다크 팔레트의 실제 색상 값은 `presentation/styles/palette.css` 한 곳에 있고, Tailwind와 Recharts는 동일한 CSS 변수를 사용합니다. 테마 선택은 `themeStore`가 로컬 저장소에 보존하며 `ThemeController`가 문서 루트의 `data-theme`에 반영합니다.

## 잡 진행

보고서 생성 요청 뒤 `useJobStream`이 SSE를 우선 사용하고 연결 실패 시 지수 백오프 폴링으로 전환합니다. SSE URL에는 EventSource의 헤더 제한을 고려한 인증 query token이 포함되고 백엔드는 같은 토큰을 검증합니다.

## 검증

```bash
pnpm test:architecture
pnpm build
```
