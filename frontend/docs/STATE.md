# frontend/docs/STATE.md

# 전역 상태 관리

## 상태 관리 전략

| 구분 | 도구 | 용도 |
|------|------|------|
| 서버 상태 | TanStack Query v5 | API 데이터 페칭·캐싱·동기화 |
| 클라이언트 전역 상태 | Zustand v4 | 인증 정보, UI 상태, 선택된 보고서 |
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
- `partialize`: `loginRequired` 는 persist 제외
- `clearAuth()`: 로그아웃 또는 토큰 재발급 실패 시 호출
- 초기값: `loginRequired: true` (기본 로그인 필요)

**주의**: `accessToken` 이 localStorage 에 저장됩니다. XSS 위험 고려 시 HttpOnly 쿠키 전환을 검토하세요. ([REFACTORING_NOTES.md](./REFACTORING_NOTES.md) 참조)

---

## reportStore (`src/app/store/reportStore.ts`)

```ts
interface ReportStore {
  selectedReportId: number | null
  setSelectedReportId(id: number | null): void
  currentReport: ReportDetail | null
  setCurrentReport(r: ReportDetail | null): void
}
```

- `selectedReportId`: HistoryPage에서 보고서 선택 → DashboardPage에서 해당 보고서 표시
- `currentReport`: 현재 화면에 렌더링 중인 보고서 전체 데이터 캐시
- persist 없음 (세션 내 임시 상태)

---

## uiStore (`src/app/store/uiStore.ts`)

```ts
interface UiStore {
  isTriggerLoading: boolean
  setTriggerLoading(v: boolean): void
  triggerMessage: string | null
  setTriggerMessage(msg: string | null): void
}
```

- `isTriggerLoading`: 보고서 생성 잡 실행 중 여부 (Header TriggerButton 스피너 제어)
- `triggerMessage`: 잡 완료/오류 메시지 (UI 피드백)
- persist 없음

> **참고**: Sidebar 열림/닫힘은 별도 `uiStore` 없이 각 레이아웃 컴포넌트 로컬 상태로 관리됩니다.

---

## JiraContext (`src/app/context/JiraContext.tsx`)

```ts
interface JiraContextValue {
  jiraBase:   string   // 예: 'https://seculayer.atlassian.net'
  jiraBrowse: string   // 예: 'https://seculayer.atlassian.net/browse'
}

// 사용
const { jiraBase, jiraBrowse } = useJira()
```

- `JiraProvider` 로 감싸진 트리에서 `useJira()` 훅으로 값 소비
- `useConfig()` 로 서버에서 `jira_base_url` 조회 후 `useMemo` 로 `jiraBase` / `jiraBrowse` 파생
- 이슈 키 클릭 시 `${jiraBrowse}/${key}` 로 링크 생성

---

## TanStack Query 설정

`src/main.tsx` 에서 `QueryClient` 생성 후 `QueryClientProvider` 로 전달:

```ts
new QueryClient({
  defaultOptions: {
    queries: {
      retry:     2,
      staleTime: 5 * 60 * 1000,   // 5분
    }
  }
})
```

> `App.tsx` 는 `RouterProvider` 만 포함하며, `QueryClientProvider` 래핑은 `main.tsx` 에서 담당합니다.
