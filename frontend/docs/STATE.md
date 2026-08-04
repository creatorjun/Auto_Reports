# frontend/docs/STATE.md

# 전역 상태 관리

## 상태 관리 전략

| 구분 | 도구 | 용도 |
|------|------|------|
| 서버 상태 | TanStack Query v5 | API 데이터 페칭·캐싱·동기화 |
| 클라이언트 전역 상태 | Zustand v4 | 인증 정보, UI 상태, 선택된 보고서 ID |
| 컴포넌트 로컬 상태 | `useState` / `useReducer` | 폼, 모달 열림/닫힘 등 |

---

## authStore (`src/app/store/authStore.ts`)

```ts
interface AuthState {
  accessToken:   string | null
  username:      string | null
  loginRequired: boolean

  setAuth(token: string, username: string): void
  setLoginRequired(v: boolean): void
  clearAuth(): void
}
```

- `persist` 미들웨어 사용 → `localStorage['auth-storage']` 에 `{ accessToken, username }` 저장
- `partialize`: `loginRequired`는 persist 제외
- `clearAuth()`: 로그아웃 또는 토큰 재발급 실패 시 호출

**주의**: `accessToken`이 localStorage에 저장됩니다. XSS 위험 고려 시 HttpOnly 쿠키 전환을 검토하세요. ([REFACTORING_NOTES.md](./REFACTORING_NOTES.md) 참조)

---

## reportStore (`src/app/store/reportStore.ts`)

```ts
interface ReportState {
  selectedReportId: number | null
  setSelectedReportId(id: number | null): void
}
```

- HistoryPage에서 보고서 선택 → DashboardPage에서 해당 보고서 표시
- persist 없음 (세션 내 임시 상태)

---

## uiStore (`src/app/store/uiStore.ts`)

```ts
interface UiState {
  sidebarOpen: boolean
  toggleSidebar(): void
  setSidebarOpen(v: boolean): void
}
```

- 데스크톱 Sidebar 열림/닫힘 제어
- persist 없음

---

## JiraContext (`src/app/context/JiraContext.tsx`)

```ts
const JiraContext = React.createContext<{ jiraBaseUrl: string }>({
  jiraBaseUrl: DEFAULT_JIRA_BASE_URL
})
```

- `useAppConfig()` 로 서버에서 `jira_base_url` 조회 후 Context 제공
- 이슈 키 클릭 시 `${jiraBaseUrl}/browse/${key}` 로 링크 생성

---

## TanStack Query 설정

`src/app/App.tsx` 에서 `QueryClient` 생성:

```ts
new QueryClient({
  defaultOptions: {
    queries: {
      staleTime:            5 * 60 * 1000,   // 5분
      gcTime:               10 * 60 * 1000,  // 10분
      retry:                1,
      refetchOnWindowFocus: false,
    }
  }
})
```
