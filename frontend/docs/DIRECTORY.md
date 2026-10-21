# Frontend Directory

문서 기준: 2026-10-21.

주요 구조이며 전체 파일 목록은 저장소 소스를 기준으로 합니다.

```text
frontend/
├── package.json / pnpm-lock.yaml / pnpm-workspace.yaml
├── Dockerfile / nginx.conf / vite.config.ts / tailwind.config.js
├── tests/                         Node 회귀 검사
├── docs/
└── src/
    ├── main.tsx                   구체 gateway·parser·exporter 조립
    ├── app/                       App.tsx, router.tsx
    ├── assets/                    테마별 PNG 로고, PDF 글꼴·라이선스
    ├── domain/                    보고서, SLA, 재배포, 이슈·사이트·인증 모델
    ├── application/
    │   ├── errors/                RequestError
    │   ├── ports/                 ApplicationServices, AuthSessionPort, PreviewParserPort
    │   └── services/              dashboardData, reportPeriod, slaStatus, slaViolationReport,
    │                              redeploymentReport, auditLog
    ├── infrastructure/
    │   ├── api/                   인증·보고서·SLA·재배포·전체 이슈·감사·관리 adapter
    │   ├── export/                PDF·Excel exporter와 문서 직렬화
    │   └── preview/               Word·Excel·CSV·텍스트 파서
    └── presentation/
        ├── pages/                 route 진입점
        ├── components/            공통 UI, 위젯, SLA·재배포·연간·관리 화면
        ├── hooks/                 Query, mutation, 표·검색 상태
        ├── state/                 auth, theme, report, ui store
        ├── context/               서비스 주입, Jira, 생성 추적, 내보내기
        ├── config/                designTokens, 색상·필터·연도·query 설정
        ├── utils/                 표시·표·내보내기 도우미
        └── styles/                공통 CSS
```

## 변경 위치

| 변경 내용 | 시작 위치 |
|---|---|
| 메뉴 순서·hover | `src/presentation/components/layout/Sidebar.tsx`, `MobileTabBar.tsx` |
| 집중 관리 하위 메뉴 | `src/presentation/config/focusManagement.ts` |
| 연도 목록·프런트엔드 자동 조회 대상 | `src/presentation/config/annualReports.ts` |
| 라우트·권한 | `src/app/router.tsx`, `src/presentation/components/auth` |
| 색상·글꼴 크기·굵기 | `src/presentation/config/designTokens.json`, `issueBadgeColors.ts` |
| 브랜드 | `src/presentation/components/common/BrandLogo.tsx`, `src/assets` |
| SLA 현황 모델·계산 | `src/domain/SLAStatus.ts`, `src/application/services/slaStatus.ts` |
| SLA 현황 조회·화면 | `src/infrastructure/api/slaStatusApi.ts`, `src/presentation/hooks/useSlaStatus.ts`, `src/presentation/pages/SlaStatusPage.tsx`, `src/presentation/components/sla-status` |
| SLA 위반 요약·검색·추이 | `src/domain/SlaViolationOverview.ts`, `src/presentation/components/sla-violations` |
| 재배포 집계·선택 | `src/application/services/redeploymentReport.ts`, `src/presentation/pages/RedeploymentPage.tsx` |
| API 계약 | `src/application/ports/ApplicationServices.ts` → `src/infrastructure/api` → `src/main.tsx` |
| 공통 표 저장 설정 | `src/presentation/hooks/useTablePreferences.ts` |

새 외부 연동은 Application 계약부터 정의하고 Infrastructure에서 구현합니다. React 훅과 표시 상태는 Presentation에 둡니다. `src/shared` 폴더는 사용하지 않습니다. 모델별 역할은 [DOMAIN](DOMAIN.md), 컴포넌트 책임은 [components](components.md)에 있습니다.
