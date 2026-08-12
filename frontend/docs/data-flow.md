# Frontend Data Flow

## Query와 mutation

```text
Component
  -> presentation hook
  -> Application gateway
  -> axios Infrastructure adapter
  -> /api/v1 FastAPI
  -> Domain model
  -> TanStack Query cache
  -> Component render
```

UI는 구체 API module을 import하지 않습니다. `main.tsx`가 auth, reports, sites, storage, partners, search adapter를 `ApplicationServicesProvider`에 주입하고 hook은 context에서 필요한 gateway만 꺼냅니다.

## Report generation

```text
Generate modal
  -> ReportGateway.trigger
  -> job_id
  -> useJobStream SSE
  -> status update
  -> done report_id
  -> report queries invalidate
```

SSE 연결이 실패하면 지수 백오프 polling으로 전환합니다. hook cleanup은 EventSource, timer, abort 상태를 정리합니다.

## Authentication

```text
login
  -> access token in auth store
  -> request interceptor Authorization header
  -> 401
  -> one shared refresh Promise
  -> retry or clear session and redirect
```

Infrastructure는 Zustand store를 직접 import하지 않습니다. Composition Root가 `AuthSessionPort` adapter를 제공합니다. HTTP 오류는 `RequestError`로 정규화되어 UI에 전달됩니다.

## Jira links

`JiraContext`가 `/config` 응답의 base URL에서 browse URL을 만들고 이슈 UI가 이를 사용합니다. 회사별 URL을 component에 하드코딩하지 않습니다.
