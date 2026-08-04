# frontend/docs/INFRASTRUCTURE.md

# Infrastructure 레이어

## api/client.ts — axios 인스턴스

### 기본 설정

```ts
baseURL:         '/api/v1'
timeout:         30_000 ms
withCredentials: true   // HttpOnly 쿠키 (refresh_token) 전송
```

### Request Interceptor

`useAuthStore`에서 `accessToken`을 읽어 `Authorization: Bearer <token>` 헤더를 자동 주입합니다.

### Response Interceptor — 자동 토큰 재발급

```
401 수신
  → SKIP_REFRESH_URLS 해당 시 즉시 reject
  → isRefreshing 플래그로 동시 재발급 방지
  → POST /auth/refresh 호출
    → 성공: 새 토큰 저장 → 대기 큐 flush → 원 요청 재시도
    → 실패: redirectToLogin() → /login 리디렉션
```

`SKIP_REFRESH_URLS`: `['/auth/refresh', '/auth/login', '/auth/me']`

---

## api/authApi.ts

| 함수 | 메서드·경로 | 반환 |
|------|-------------|------|
| `login({ username, password })` | POST `/auth/login` | `TokenResponse` |
| `refresh()` | POST `/auth/refresh` | `TokenResponse` |
| `logout()` | POST `/auth/logout` | `void` |
| `me()` | GET `/auth/me` | `MeResponse` |

---

## api/reportApi.ts

| 함수 | 메서드·경로 | 반환 |
|------|-------------|------|
| `getLatest()` | GET `/reports/latest` | `ReportDetail \| null` |
| `getById(id)` | GET `/reports/:id` | `ReportDetail` |
| `getAll(limit, offset)` | GET `/reports/` | `ReportSummary[]` |
| `trigger(params?)` | POST `/trigger/` | `TriggerAccepted` |
| `getJobStatus(jobId)` | GET `/trigger/:id/status` | `JobStatus` |
| `getJobStreamUrl(jobId, token?)` | — (URL 생성) | `string` |
| `delete(id)` | DELETE `/reports/:id` | `void` |
| `getConfig()` | GET `/config` | `AppConfig` |

---

## api/siteApi.ts

| 함수 | 설명 |
|------|------|
| `getAll()` | 사이트 요약 목록 |
| `getById(id)` | 사이트 상세 |
| `create(payload)` | 사이트 생성 |
| `update(id, payload)` | 사이트 수정 |
| `delete(id)` | 사이트 삭제 |
| `addNode(siteId, payload)` | 노드 추가 |
| `updateNode(siteId, nodeId, payload)` | 노드 수정 |
| `deleteNode(siteId, nodeId)` | 노드 삭제 |
| `addPatchHistory(siteId, payload)` | 패치 이력 추가 |
| `updatePatchHistory(siteId, patchId, payload)` | 패치 이력 수정 |
| `deletePatchHistory(siteId, patchId)` | 패치 이력 삭제 |
| `addVisitHistory(siteId, payload)` | 방문 이력 추가 |
| `updateVisitHistory(siteId, visitId, payload)` | 방문 이력 수정 |
| `deleteVisitHistory(siteId, visitId)` | 방문 이력 삭제 |

---

## api/partnerApi.ts

| 함수 | 설명 |
|------|------|
| `getOrgs()` | 파트너 조직 목록 |
| `getMembers(orgId)` | 조직 멤버 목록 |
| `getIssues(orgId)` | 조직 미처리 이슈 목록 |

---

## api/searchApi.ts

| 함수 | 설명 |
|------|------|
| `search(query)` | Jira 이슈 검색 (키워드 기반) |

---

## api/storageApi.ts

| 함수 | 설명 |
|------|------|
| `list(path)` | 디렉토리 파일 목록 |
| `upload(path, file)` | 파일 업로드 (multipart) |
| `download(path)` | 파일 다운로드 |
| `delete(path)` | 파일 삭제 |
| `preview(path)` | 파일 미리보기 URL/데이터 |
| `mkdir(path)` | 디렉토리 생성 |
| `rename(oldPath, newPath)` | 파일/폴더 이름 변경 |

---

## hooks/useAuth.ts

```ts
useMe()      // GET /auth/me → { username, login_required }
useLogin()   // POST /auth/login → token 저장 + 쿼리 무효화
useLogout()  // POST /auth/logout → clearAuth + /login 이동
```

---

## hooks/useConfig.ts

```ts
useAppConfig()  // GET /config → AppConfig (jira_base_url)
```

JiraContext를 통해 하위 컴포넌트에 jiraBaseUrl 제공.

---

## hooks/useReport.ts

```ts
useLatestReport()          // 최신 보고서 조회
useReportById(id)          // ID로 보고서 조회
useAllReports(limit, offset)  // 보고서 목록
useTriggerReport()         // 보고서 생성 트리거 뮤테이션
useDeleteReport()          // 보고서 삭제 뮤테이션
```

---

## hooks/useJobStream.ts

잡 진행 상태를 **SSE 우선 / Exponential Backoff 폴링 폴백** 방식으로 모니터링합니다.

```ts
const { start, stop } = useJobStream({
  onStatus:   (s: JobStatus) => void,
  onComplete: (reportId: number | null) => void,
  onError:    (message: string) => void,
  onTimeout:  () => void,
})

start(jobId)  // SSE 연결 시작
stop()        // 연결 해제
```

**Exponential Backoff 설정**

| 상수 | 값 |
|------|---------|
| `EB_BASE_MS` | 1,000ms |
| `EB_MAX_MS` | 16,000ms |
| `EB_JITTER` | ±20% |
| `TIMEOUT_MS` | 300,000ms (5분) |

---

## hooks/useTrigger.ts

보고서 생성 전체 상태 머신:

```
idle → pending(트리거 호출 중) → running(잡 진행) → done(완료) → idle
                                                  → error
                                                  → timeout
```

---

## hooks/useStorage.ts

파일 스토리지 CRUD 훅. `useQuery` / `useMutation` 기반.  
업로드·삭제·이름변경·폴더생성 후 자동 목록 무효화.
