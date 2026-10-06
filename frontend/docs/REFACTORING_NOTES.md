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

## 2026-10-06 성능 검토

실행 코드 153개 파일의 의존 관계, 목록 순회·정렬, React 상태와 메모이제이션, 요청·타이머·객체 URL 수명, 동적 import와 배포 구성을 검토했습니다.

- 대시보드의 유형·상태·반기 지원 정보는 보고서가 바뀔 때만 계산합니다. 필터를 바꾸면 해당 선택에 따른 통계와 목록은 다시 계산하며, 새 보고서에는 변경된 선택지와 지원 범위를 적용합니다. 직접 호출하는 `buildDashboardData()`는 매번 전달한 보고서를 해석하므로 별도 전역 캐시가 없습니다.
- 이슈 관리와 컬럼 검색은 적용된 조건이 없으면 원본 목록을 재사용합니다. 호출자는 목록을 변경하지 않으며, 표시 정렬은 별도 배열에서 수행합니다. 빈 선택 집합은 계속 전체 해제를 뜻하고 공백 검색어는 전체 행을 표시합니다.
- 연간 상세 목록은 검색어가 없으면 전체 목록을 다시 정규화하지 않습니다. 검색·페이지 처리와 원본 목록의 독립성은 유지합니다.

3,000개 이슈를 사용하는 React 테스트 렌더러에서 필터를 반복 변경한 5회 중앙값은 약 1.29ms에서 0.40ms로 줄었습니다. 이 수치는 데이터 가공과 테스트 렌더러를 포함한 측정이며 실제 브라우저의 화면 표시 시간은 아닙니다. PDF·Excel의 모든 행과 필터 스냅샷, 전체 선택·해제, 라이센스와 숨겨진 유형 정책, 검색·정렬·페이지 상태는 기존 회귀 테스트로 함께 검증합니다.
