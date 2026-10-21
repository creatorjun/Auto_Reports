# 구조 유지 기준과 변경 기록

문서 기준: 2026-10-21.

과거 리팩터링에서 정리한 경계를 현재 기능에 맞춰 유지합니다. 과거 실행 파일 수·테스트 개수·벤치마크를 현재 배포 결과로 사용하지 않습니다.

| 변경 이유 | 현재 유지할 구조 |
|---|---|
| Presentation의 구체 API 결합 | ApplicationServices gateway와 Provider 주입 |
| axios의 인증 store 결합 | main.tsx에서 AuthSessionPort 조립 |
| HTTP 라이브러리 오류 누출 | RequestError로 정규화 |
| 동시 401 대기열 미종료 | 하나의 refresh Promise 공유, 실패 시 reject·세션 제거 |
| 화면 훅에 대시보드 계산 혼합 | application/services/dashboardData.ts |
| UI에서 문서 형식 직접 해석 | PreviewParserPort + infrastructure/preview |
| 전역 Shared로 의존 방향 우회 | Domain·Application·Presentation의 책임별 배치 |
| 일반/연간 보고서 최신 상태 혼동 | scope별 query 및 생성 완료 처리 |
| SLA 상세만으로 전체 파악 어려움 | 순수 요약·추이·검색 정책과 선택 가능한 개요 컴포넌트 |
| 현재 SLA 주의 티켓과 저장 위반 보고서의 혼동 | `/sla-status` 현재 스냅샷과 `/sla-violations` 기간별 저장 이력의 모델·gateway·query 분리 |
| 페이지별 색상·타이포그래피 불일치 | designTokens.json, 공통 배지, 3단계 크기·굵기 |
| 표 재진입 시 설정 유실 | useTablePreferences의 목록별 localStorage 검증·복원 |
| UI에 연간 집계 범위·다중 업로드 정책 혼합 | reportPeriod·storageUploads Application service |
| 로그아웃·검색 종료 뒤 늦은 응답 반영 | HTTP 인증 세대 검사, Presentation 세션 버전·요청 identity 검사 |
| 보고서 구독 종료 후 polling 지속 | subscription 소유 취소 신호·단일 fallback·종료 뒤 callback 차단 |

대시보드 필터 메타데이터는 보고서가 바뀔 때 계산하고 선택 조건의 결과는 useMemo로 보관합니다. 전체 이슈·컬럼 검색은 조건이 없으면 원본 목록을 재사용하므로 호출자가 배열이나 행을 변경해서는 안 됩니다. 정렬과 내보내기는 별도 배열/스냅샷을 사용합니다.

## 현재 기능 범위

C-Level 화면·로직은 제거했습니다. 선택적 Rovo Automation 분석 결과는 기존 AI 종합 분석 카드에서 요약·문제점·병목·개선 제안으로 표시하며 A2A 분석은 제공하지 않습니다. 기존 `/sla-dashboard`는 장기 이슈, `/sla-violations`는 SLA 위반이며 신규 `/sla-status`가 SLA 현황을 담당합니다. 집중 관리 메뉴는 SLA 현황 → SLA 위반 → 재배포 현황 순서입니다. 히스토리는 페이지를 유지하고 대메뉴에서만 제거했습니다.

재배포 현황은 매일 08시 KST, SLA 위반은 기간별 수동 생성입니다. SLA 위반 카드·차트·검색은 저장된 데이터에서 계산하고 과거 보고서의 값을 현재 Jira로 덮어쓰지 않습니다. SLA 현황은 잔여율 0% 이상 30% 미만인 미위반 티켓의 현재 수집 스냅샷이며 일반 조회의 60초 캐시와 수동 강제 새로고침을 사용합니다. 생성 기간·저장 이력은 없고 실패 시 마지막 성공 목록을 유지합니다. 일반 보고서와 연간 일부 상세 차트의 현재 Jira 조회도 별도 계약입니다.

## 검증과 유지보수

`tests/architecture.test.mjs`가 import 방향·직접 네트워크 호출·주석 규칙을 검사합니다. SLA·재배포·보고서 생성·필터·내보내기·표 설정은 각 회귀 테스트에서 확인합니다. 전체 실행은 `node --test tests/*.test.mjs`, TypeScript와 번들 검증은 `pnpm build`입니다.

연도 전환 시 `config/annualReports.ts`의 연도 목록·자동 조회 대상과 서버의 현재 연도 갱신 정책을 함께 확인합니다. 메뉴·API·데이터 정책을 변경하면 [사용 가이드](USER_GUIDE.md), [라우팅](ROUTING.md), [데이터 흐름](data-flow.md), 관련 백엔드 문서를 함께 갱신합니다. 문서에 실제 서버 검증 결과를 쓸 때에는 수행 날짜와 코드·DB revision, 테스트 범위를 명시합니다.
