# frontend/docs/REFACTORING_NOTES.md

# 코드 검수 결과 및 리팩토링 가이드

검수 기준일: 2026-08-05

---

## 긍정적 평가

- Clean Architecture 4계층 분리가 일관성 있게 적용되어 있습니다.
- Domain 레이어가 순수 타입만 포함하며 외부 의존성이 없습니다.
- axios 인터셉터에서 JWT 자동 재발급 로직이 올바르게 구현되어 있습니다 (동시 401 처리 큐 포함).
- `useJobStream`의 SSE 우선 / Exp. Backoff 폴링 폴백 패턴이 견고합니다.
- `shared/constants.ts`와 `shared/ui.ts`로 UI 토큰이 중앙 관리되어 있습니다.
- Lazy Loading + ErrorBoundary 조합으로 코드 스플리팅이 적절히 적용되어 있습니다.

---

## 개선 권장 사항

### 1. 중복 타입 제거 — BaseIssue 추상화

**현황**: `Issue.ts`의 `RecentIssue`와 `Partner.ts`의 `PartnerIssue`가 동일한 필드 구조를 가집니다.

```ts
// 권장: domain/Issue.ts
export interface BaseIssue {
  key:          string
  summary:      string
  type:         string
  status:       string
  stage_index:  number
  created:      string
  elapsed_days: number
  reporter:     string
  tac_team:     string
}

export type RecentIssue  = BaseIssue
export type PartnerIssue = BaseIssue  // Partner.ts에서 import
```

---

### 2. Report.ts — 파일 상단 경로 주석 누락

**현황**: `src/domain/Report.ts`에 `// frontend/src/domain/Report.ts` 주석이 없습니다.  
**조치**: 다른 파일과 일관성을 위해 첫 줄에 추가 권장.

---

### 3. 대형 페이지 분리 권장

| 파일 | 크기 | 권장 분리 |
|------|------|----------|
| `StoragePage.tsx` | ~36.5KB | 파일 브라우저 + 미리보기 훅을 별도 커스텀 훅으로 분리 |
| `SiteDetailPage.tsx` | ~36KB | 각 탭(노드/패치/방문)을 별도 컴포넌트로 분리 |
| `DashboardPage.tsx` | ~16.5KB | 위젯 섹션(카드/차트/테이블)별 서브컴포넌트 분리 |
| `SiteCreatePage.tsx` | ~20KB | 각 폼 섹션을 별도 컴포넌트로 분리 |

---

### 4. accessToken localStorage 저장 보안 검토

**현황**: `authStore`가 `persist` 미들웨어로 `accessToken`을 `localStorage`에 저장합니다.  
**리스크**: XSS 공격 시 토큰 탈취 가능.  
**권장**: 팀 내부 시스템이므로 현재 수준 유지 가능. 외부 노출 시 HttpOnly 쿠키 기반으로 전환 고려.

---

### 5. tables/ statusBadge.tsx — 파일명 컨벤션 불일치

**현황**: `tables/statusBadge.tsx`는 소문자로 시작하지만, 다른 컴포넌트 파일은 PascalCase입니다.  
**권장**: `StatusBadge.tsx`로 이름 변경. (`common/StatusBadge.tsx`와 역할 중복 여부 함께 검토)

---

### 6. 모달 컴포넌트 추상화 수준 향상

**현황**: `tables/` 폴더의 9개 모달이 유사한 구조를 반복합니다 (`IssueModalShell` 활용 중).  
**권장**: 컬럼 정의 배열을 props로 받는 제네릭 `IssueTableModal<T>` 컴포넌트로 통합 검토.

---

### 7. 환경변수 기반 API baseURL 관리

**현황**: `client.ts`의 `baseURL`이 `'/api/v1'`로 하드코딩되어 있습니다.  
**권장**: `import.meta.env.VITE_API_BASE_URL`로 환경변수화.

```ts
baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
```

---

### 8. TanStack Query — QueryKey 상수화

**현황**: `['me']`, `['reports', 'latest']` 등 쿼리 키가 각 훅에 문자열로 분산되어 있습니다.  
**권장**: `shared/queryKeys.ts` 파일로 중앙 관리.

```ts
// shared/queryKeys.ts
export const QUERY_KEYS = {
  me:            ['me'],
  latestReport:  ['reports', 'latest'],
  reportById:    (id: number) => ['reports', id],
  allReports:    (limit: number, offset: number) => ['reports', 'all', limit, offset],
  config:        ['config'],
  sites:         ['sites'],
  siteById:      (id: number) => ['sites', id],
  partnerOrgs:   ['partners', 'orgs'],
  partnerIssues: (orgId: string) => ['partners', 'issues', orgId],
} as const
```

---

### 9. useJobStream — callbacks ref 처리

**현황**: `useJobStream`에 전달되는 `callbacks` 객체가 매 렌더마다 새로 생성될 경우  
`useCallback` 의존성 문제가 발생할 수 있습니다.  
**권장**: `callbacks`를 `useRef`로 래핑.

```ts
const callbacksRef = useRef(callbacks)
useEffect(() => { callbacksRef.current = callbacks })
// 내부에서 callbacksRef.current.onStatus?.() 형태로 호출
```

---

### 10. 미사용 가능성 — StoragePreviewPage

**현황**: `StoragePreviewPage`는 `StoragePage` 내 `FilePreviewModal`과 기능이 중복될 수 있습니다.  
**권장**: 실제 사용 경로를 확인 후 미사용 시 제거 검토.
