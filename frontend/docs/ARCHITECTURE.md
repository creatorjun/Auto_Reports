# frontend/docs/ARCHITECTURE.md

# 아키텍처 개요

## 설계 철학

이 프론트엔드는 **Clean Architecture** 원칙을 React/TypeScript 환경에 적용한 구조입니다.  
의존 방향은 항상 **바깥(Presentation) → 안쪽(Domain)** 단방향이며, Domain 레이어는 외부에 의존하지 않습니다.

```
┌─────────────────────────────────────────────────────────┐
│  Presentation  (pages / components)                     │
│    ↓ 사용                                                │
│  Infrastructure  (api / hooks)                          │
│    ↓ 구현                                                │
│  Domain  (타입·인터페이스만, 의존 없음)                   │
│                                                         │
│  App  (router / store / context) — 수평 조율              │
│  Shared  (constants / utils / ui) — 횡단 관심사           │
└─────────────────────────────────────────────────────────┘
```

## 레이어 책임

### Domain (`src/domain/`)
- 순수 TypeScript 인터페이스·타입만 포함
- React, axios 등 외부 라이브러리 의존 **없음**
- 비즈니스 엔티티의 유일한 진실 원천(Single Source of Truth)

### Infrastructure (`src/infrastructure/`)
- **api/**: axios 기반 HTTP 클라이언트와 도메인별 API 함수
- **hooks/**: TanStack Query 기반 데이터 페칭·뮤테이션 훅
- Domain 타입을 import해 사용, Presentation으로 노출

### Presentation (`src/presentation/`)
- **pages/**: 라우트 단위 페이지 컴포넌트
- **components/**: 재사용 UI 컴포넌트 (layout / common / cards / charts / tables / storage)
- **styles/**: 전역 CSS (Tailwind base)
- Infrastructure 훅을 통해서만 서버 데이터 접근

### App (`src/app/`)
- **router.tsx**: React Router v6 라우트 정의
- **store/**: Zustand 전역 상태 슬라이스
- **context/**: React Context (JiraContext)

### Shared (`src/shared/`)
- 모든 레이어에서 자유롭게 참조 가능한 상수·유틸·UI 클래스 토큰
- 비즈니스 로직 포함 **금지**

## 데이터 흐름

```
사용자 액션
  → Presentation 컴포넌트
  → Infrastructure Hook (useQuery / useMutation)
  → Infrastructure API 함수
  → axios client (JWT 자동 주입, 401 자동 재발급)
  → FastAPI 백엔드
  ← 응답 데이터 (Domain 타입으로 변환)
  ← Hook 캐시 업데이트 (TanStack Query)
  ← 컴포넌트 리렌더
```

## 인증 흐름

```
로그인 성공
  → access_token → Zustand authStore (localStorage persist)
  → 모든 요청 헤더에 Bearer 자동 주입
  → 401 수신 시 /auth/refresh 자동 호출
  → 재발급 실패 시 clearAuth() + /login 리디렉션
```

## 비동기 잡 흐름 (보고서 생성)

```
트리거 버튼 클릭
  → POST /trigger/ → { job_id }
  → useJobStream.start(job_id)
    → SSE EventSource 연결 우선 시도
    → SSE 불가 시 Exponential Backoff 폴링으로 폴백
  → status 이벤트마다 UI 업데이트
  → done 이벤트 → report_id로 보고서 조회
```
