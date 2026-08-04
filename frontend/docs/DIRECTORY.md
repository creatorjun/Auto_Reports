# frontend/docs/DIRECTORY.md

# 디렉토리 구조

```
frontend/
├── Dockerfile                        # 프로덕션 Docker 이미지
├── nginx.conf                        # SPA 라우팅 + /api 프록시 설정
├── index.html                        # Vite HTML 엔트리
├── package.json                      # 의존성 및 스크립트
├── vite.config.ts                    # Vite 빌드 설정 (경로 alias @ = src/)
├── tailwind.config.js                # Tailwind 커스텀 토큰
├── tsconfig.json                     # TypeScript 설정
├── postcss.config.js
├── docs/                             # ← 현재 문서 폴더
└── src/
    ├── main.tsx                      # React 앱 마운트 엔트리
    │
    ├── app/                          # 앱 레벨 설정
    │   ├── App.tsx                   # QueryClientProvider + RouterProvider 조합
    │   ├── router.tsx                # 전체 라우트 정의 (lazy + ProtectedRoute)
    │   ├── context/
    │   │   └── JiraContext.tsx       # jiraBaseUrl 전역 Context
    │   └── store/
    │       ├── authStore.ts          # 인증 상태 (Zustand + persist)
    │       ├── reportStore.ts        # 선택된 보고서 ID 상태
    │       └── uiStore.ts            # 사이드바 열림/닫힘 상태
    │
    ├── domain/                       # 순수 타입 레이어
    │   ├── Config.ts                 # AppConfig (jira_base_url)
    │   ├── Issue.ts                  # RecentIssue
    │   ├── Job.ts                    # TriggerAccepted, JobStatus, TriggerParams
    │   ├── Partner.ts                # PartnerOrg, PartnerMember, PartnerIssue
    │   ├── Report.ts                 # ReportSummary, ReportDetail, AiAnalysis, WidgetResult
    │   ├── Site.ts                   # SiteStatus, SiteDetail, DeploymentNode, PatchHistory, VisitHistory 등
    │   └── Storage.ts                # StorageFile, StorageDir 등
    │
    ├── infrastructure/               # 외부 연동 레이어
    │   ├── api/
    │   │   ├── client.ts             # axios 인스턴스 + JWT 인터셉터 + 자동 재발급
    │   │   ├── authApi.ts            # 로그인·로그아웃·me·refresh
    │   │   ├── reportApi.ts          # 보고서 CRUD + 트리거 + SSE URL
    │   │   ├── partnerApi.ts         # 파트너 조직·이슈
    │   │   ├── searchApi.ts          # Jira 이슈 검색
    │   │   ├── siteApi.ts            # 사이트 CRUD + 노드/패치/방문 관리
    │   │   └── storageApi.ts         # 파일 목록·업로드·다운로드·삭제·미리보기
    │   └── hooks/
    │       ├── useAuth.ts            # useMe, useLogin, useLogout
    │       ├── useConfig.ts          # useAppConfig
    │       ├── useJobStream.ts       # SSE + Exp. Backoff 폴링 잡 모니터
    │       ├── useReport.ts          # useLatestReport, useReportById, useAllReports, useTriggerReport, useDeleteReport
    │       ├── useStorage.ts         # 스토리지 CRUD 훅 세트
    │       └── useTrigger.ts         # 트리거 상태 머신 (idle→pending→running→done)
    │
    ├── presentation/
    │   ├── styles/
    │   │   └── index.css             # Tailwind directives + 전역 스타일
    │   ├── components/
    │   │   ├── auth/
    │   │   │   └── ProtectedRoute.tsx          # 미인증 시 /login 리디렉션
    │   │   ├── layout/
    │   │   │   ├── Layout.tsx                  # Header + Sidebar + <Outlet/>
    │   │   │   ├── Header.tsx                  # 로고, 검색, 트리거, 유저 메뉴
    │   │   │   ├── Sidebar.tsx                 # 데스크톱 사이드 내비게이션
    │   │   │   └── MobileTabBar.tsx            # 모바일 하단 탭 바
    │   │   ├── common/
    │   │   │   ├── LoadingSpinner.tsx           # 전역 로딩 UI
    │   │   │   ├── ErrorBoundary.tsx            # 클래스형 에러 경계
    │   │   │   ├── LazyErrorBoundary.tsx        # lazy load용 에러 경계
    │   │   │   ├── StatusBadge.tsx              # 이슈 상태 뱃지 (common)
    │   │   │   ├── RefreshButton.tsx            # 수동 새로고침 버튼
    │   │   │   ├── TriggerButton.tsx            # 보고서 생성 트리거 버튼
    │   │   │   ├── GenerateReportModal.tsx      # 날짜 선택 + 생성 모달
    │   │   │   ├── LazyGenerateReportModal.tsx  # GenerateReportModal lazy wrapper
    │   │   │   ├── IssueModalShell.tsx          # 이슈 모달 공통 쉘
    │   │   │   └── SearchWidget.tsx             # Jira 이슈 검색 위젯
    │   │   ├── cards/
    │   │   │   ├── AiSummaryCard.tsx            # AI 분석 요약 카드
    │   │   │   ├── SlaRateCard.tsx              # SLA 달성률 도넛 카드
    │   │   │   └── SummaryCard.tsx              # 수치 요약 카드
    │   │   ├── charts/
    │   │   │   ├── MonthlyCountChart.tsx        # 월별 생성/해결 건수 바 차트
    │   │   │   ├── ReasonPieChart.tsx           # 지연 사유 파이 차트
    │   │   │   ├── ResolutionTimeChart.tsx      # 처리 시간 분포 차트
    │   │   │   ├── SlaDonutChart.tsx            # SLA 도넛 차트
    │   │   │   ├── SlaMonthlyLineChart.tsx      # SLA 월별 추이 라인 차트
    │   │   │   ├── TrendLineChart.tsx           # 이슈 트렌드 라인 차트
    │   │   │   └── TypeBarChart.tsx             # 이슈 유형별 바 차트
    │   │   ├── tables/
    │   │   │   ├── statusBadge.tsx              # 이슈 상태 뱃지 (tables 전용)
    │   │   │   ├── DataRequestModal.tsx         # 자료요청 이슈 모달
    │   │   │   ├── IncompleteIssueModal.tsx     # 미완료 이슈 모달
    │   │   │   ├── IssueReviewModal.tsx         # 이슈리뷰 모달
    │   │   │   ├── ResultPendingModal.tsx       # 결과대기 모달
    │   │   │   ├── SlaDelayModal.tsx            # SLA 지연 모달
    │   │   │   ├── SlaOverdueModal.tsx          # SLA 초과 모달
    │   │   │   ├── SlaViolationModal.tsx        # SLA 위반 모달
    │   │   │   ├── WeeklyCreatedModal.tsx       # 주간 생성 이슈 모달
    │   │   │   └── WeeklyResolvedModal.tsx      # 주간 해결 이슈 모달
    │   │   └── storage/
    │   │       └── FilePreviewModal.tsx         # 파일 미리보기 모달 (PDF/Word/Excel/Markdown/이미지/텍스트)
    │   └── pages/
    │       ├── LoginPage.tsx                    # 로그인 페이지
    │       ├── DashboardPage.tsx                # 메인 대시보드 (보고서 위젯)
    │       ├── HistoryPage.tsx                  # 보고서 히스토리 목록
    │       ├── PartnerManagementPage.tsx        # 파트너 관리 페이지
    │       ├── StoragePage.tsx                  # 파일 스토리지 페이지
    │       ├── StoragePreviewPage.tsx           # 스토리지 파일 미리보기 라우트
    │       ├── SiteManagementPage.tsx           # 사이트 목록 관리 페이지
    │       ├── SiteCreatePage.tsx               # 사이트 생성/편집 페이지
    │       └── SiteDetailPage.tsx               # 사이트 상세 페이지
    │
    └── shared/
        ├── constants.ts                         # 앱 전역 상수 (차트·SLA·테이블)
        ├── ui.ts                                # UI 클래스 토큰 (상태 스타일·모달 클래스)
        └── utils/
            └── formatters.ts                    # 날짜·숫자 포매터
```
