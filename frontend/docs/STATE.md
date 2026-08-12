# Frontend State

| 상태 | 위치 | 소유 도구 |
|------|------|-----------|
| 서버 응답과 캐시 | `presentation/hooks` | TanStack Query |
| 인증 세션 | `presentation/state/authStore.ts` | Zustand persist |
| 선택·현재 보고서 | `presentation/state/reportStore.ts` | Zustand |
| 트리거 표시 상태 | `presentation/state/uiStore.ts` | Zustand |
| Jira 링크 설정 | `presentation/context/JiraContext.tsx` | React Context |
| Application gateway | `presentation/context/ApplicationServicesContext.tsx` | React Context |
| 폼·모달 상태 | 각 component | React state/form |

`authStore`는 `AuthSessionPort`에 필요한 token 조회, 설정, 제거 동작을 제공합니다. Infrastructure는 이 store를 import하지 않으며 `main.tsx`가 adapter를 구성합니다.

현재 access token은 `localStorage`에 persist됩니다. 내부망 운영에서도 CSP와 XSS 방어가 필요하며, 노출 범위가 커지면 메모리 기반 access token과 HttpOnly refresh cookie 조합으로 전환합니다.

Query key는 `presentation/config/queryKeys.ts`에서 중앙 관리합니다. UI 상태는 API 응답 모델과 섞지 않습니다.
