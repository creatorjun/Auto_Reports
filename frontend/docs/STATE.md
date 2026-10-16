# Frontend State

문서 기준: 2026-10-16.

| 상태 | 소유 위치 | 지속 범위 |
|---|---|---|
| 서버 요청·캐시 | `presentation/hooks`, TanStack Query | query key·staleTime에 따름 |
| 인증 | `state/authStore.ts`, Zustand persist | 브라우저 localStorage; refresh cookie는 서버 |
| 현재·선택 보고서 | `state/reportStore.ts` | 앱 메모리의 선택 ID와 현재 보고서 참조 |
| 일반 보고서 생성 | `context/ReportGenerationContext.tsx`, `state/uiStore.ts` | 인증된 Layout이 구독 소유, 메뉴 이동 중 유지 |
| 테마 | `state/themeStore.ts` | `auto-reports-theme` localStorage |
| 표 정렬·너비 | `hooks/useTablePreferences.ts` | `auto-reports-table:<key>` localStorage |
| 페이지 필터·검색·펼침·pagination | page/component React state | 해당 화면·보고서 수명 |
| 서비스/Jira URL | `ApplicationServicesContext`, `JiraContext` | Provider 수명 |

위 경로는 `src/presentation` 기준입니다. Infrastructure는 Zustand를 import하지 않고 `main.tsx`가 `AuthSessionPort`를 구성합니다. access token은 현재 localStorage에 저장되므로 HttpOnly cookie만 사용하는 방식으로 설명하지 않습니다.

## Query 소유

기본 보고서·인증·설정 등의 키는 `config/queryKeys.ts`, SLA 키는 `useSlaViolations.ts`의 `SLA_VIOLATION_KEYS`, 재배포·전체 이슈·감사로그 키는 해당 훅이 소유합니다. 모두 하나의 파일에 모여 있다고 가정하지 않습니다.

| 대상 | 갱신 정책 |
|---|---|
| 최신 일반 보고서 | 5분 staleTime 및 5분 화면 polling |
| 연간 보고서 | 현재 설정된 2026은 5분 polling, 나머지 연도는 자동 조회 안 함 |
| 보고서 ID | 5분 staleTime |
| 일반 히스토리 | 페이지별, 2분 staleTime |
| SLA 최신 | 진입 때 항상 조회, 포커스 재조회 없음 |
| SLA 이력 ID | 무한 staleTime, 자동 재조회 없음 |
| 재배포 최신 | 진입 때 조회, 60초 polling |
| 전체 이슈 | 수집 중 2초, 그 외 30초 polling |

서버 스케줄과 브라우저 polling은 별개입니다. 페이지 조회가 재배포 정기 생성이나 SLA 재생성을 요청하지 않습니다. SLA 생성 성공 시 최신·ID 캐시를 교체하고 이력 목록을 무효화합니다. 재배포 성공 시 최신 캐시를 교체합니다. 일반 보고서는 생성 완료 scope에 따라 일반·연간 query를 구분해 갱신합니다.

## SLA 필터와 표 설정

공통 유형·상태·반기와 추가 SLA 범위·상태·생성일/월·검색은 화면 상태입니다. 첫 진입/다른 보고서에서 닫힘·반려됨·보류 중 제외 기본값을 적용하며 같은 보고서 재조회 중에는 선택을 유지합니다. 공통 필터 변경은 차트 상태·날짜 선택을 지우고 상세 필터 초기화는 공통 필터를 유지합니다.

SLA 통합 표는 `sla-violations:combined`, 대시보드 최근 이슈 표는 `dashboard:recent-issues` 키를 사용합니다. SLA 표의 정렬·너비는 전체·최초응답·해결·동시 위반 카드 선택과 관계없이 하나의 설정을 공유합니다. 이전 SLA 분리 표의 `sla-violations:initial_response`, `sla-violations:resolution` 설정은 읽거나 이전하지 않으므로 통합 표는 기본 설정으로 시작합니다. 일반·저장·연간 대시보드의 최근 이슈는 같은 키입니다. 전체 이슈 화면은 이 키를 전달하지 않아 해당 영속 설정을 공유하지 않습니다.

저장값은 버전 1, 허용 컬럼·정렬 방향·최소 너비·합계를 검증합니다. 손상되거나 저장소 접근이 불가능하면 기본값으로 동작합니다. 필터·검색·페이지·티켓 데이터는 저장하지 않으며 PDF·Excel의 숨김 렌더링은 표 설정을 읽거나 덮어쓰지 않습니다. 설정은 계정별 서버 동기화가 아닌 같은 브라우저·origin 기준입니다.

테마는 `ThemeController`가 루트 `data-theme`로 반영합니다. 실제 색상과 폰트 값은 `config/designTokens.json`에만 정의합니다.
