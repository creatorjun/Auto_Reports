# Frontend Clean Architecture Audit

검수 기준일: 2026-08-12
검수 범위: `frontend/src`, 타입 계약, 인증·SSE 비동기 경계, 빌드 구성, 문서

| 기존 문제 | 리팩터링 결과 |
|-----------|---------------|
| Presentation이 구체 API module을 직접 import | `ApplicationServices` gateway와 Provider 주입 |
| Infrastructure hook이 React, Zustand, Presentation 타입에 의존 | hook과 store를 Presentation으로 이동하고 Domain 모델 분리 |
| axios client가 구체 auth store를 import | `AuthSessionPort`를 Composition Root에서 주입 |
| Presentation이 axios 오류 구조를 해석 | Infrastructure가 `RequestError`로 정규화 |
| 동시 401 queue 실패 시 Promise가 영구 대기 | 단일 refresh Promise를 공유하고 실패를 명시적으로 reject |
| 컴포넌트 타입이 dashboard hook의 데이터 계약 | Dashboard 모델을 Domain으로 이동 |
| 검색 타입이 API adapter 내부에 위치 | Search 모델을 Domain으로 이동 |
| 모든 레이어가 참조하는 `shared` catch-all | 표시 상수·query key·formatter를 Presentation 소유로 이동 |
| App 폴더가 router, context, store를 혼합 | App은 router와 shell만 유지하고 state/context는 Presentation으로 이동 |
| 사이트 하위 변경 응답 타입이 백엔드와 불일치 | 전체 `SiteDetail` 반환 계약으로 정정 |
| lockfile과 자동 의존 규칙 검사 부재 | pnpm lockfile과 Node architecture test 추가 |

현재 의존 방향과 파일 주석 규칙은 `frontend/tests/architecture.test.mjs`로 강제합니다. TypeScript `noEmit` 검사와 Vite production build도 최종 검증에 포함합니다.
