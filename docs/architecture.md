# 아키텍처 v1.0

## 개요

TAC Auto Reports 는 백엔드(FastAPI)와 프론트엔드(React)를 독립적인 Docker 컨테이너로 운영하며, 양쪽 모두 **클린 아키텍처** 원칙을 따릅니다. 의존성은 항상 외부(Infrastructure) → 내부(Domain) 방향으로만 흐릅니다.

```
┌──────────────────────────────────────────────────────────────┐
│                        Browser                               │
│              React + TanStack Query + Zustand                │
└─────────────────────────┬────────────────────────────────────┘
                          │ HTTP / REST
┌─────────────────────────▼────────────────────────────────────┐
│                  Nginx (port 80)                             │
│   /api/*  →  proxy → backend:8000                           │
│   /*       →  React SPA static files                        │
└──────────┬───────────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────┐
│               FastAPI Backend (port 8000)                    │
│                                                              │
│  Presentation  →  Application  →  Domain  ←  Infrastructure │
│  (API Routers)    (Use Cases)   (Entities)   (Jira/DB/AI)   │
└──────────┬──────────────────────────────────────────────────┘
           │
┌──────────▼──────────┐    ┌─────────────┐    ┌────────────────┐
│  PostgreSQL 16       │    │ Jira Cloud  │    │ Google Gemini  │
│  (reports, jobs)     │    │  REST API   │    │     API        │
└─────────────────────┘    └─────────────┘    └────────────────┘
```

---

## 백엔드 레이어 구조

```
backend/src/
├── main.py                          # FastAPI 앱 생성, 미들웨어, 라이프사이클
├── domain/                          # 순수 비즈니스 규칙 (외부 의존성 없음)
│   ├── entities/
│   │   ├── report.py                # Report 엔티티
│   │   ├── widget.py                # Widget 엔티티
│   │   ├── widget_data.py           # 14개 위젯 데이터 타입 정의
│   │   └── job.py                   # Job 엔티티 (pending/running/done/error)
│   ├── repositories/                # Repository 인터페이스 (ABC)
│   ├── ports/                       # 외부 서비스 포트 인터페이스
│   └── value_objects/               # 값 객체
├── application/                     # 유스케이스 & 애플리케이션 서비스
│   ├── use_cases/                   # 단일 책임 유스케이스
│   ├── services/                    # 복합 비즈니스 로직
│   ├── widgets/                     # 위젯별 수집기 (14개)
│   │   ├── base.py                  # BaseWidgetCollector ABC
│   │   ├── count_collector.py       # w1~w6 이슈 카운트
│   │   ├── monthly_collector.py     # w7~w8 SLA 월별 추이
│   │   ├── monthly_count_collector.py  # w13~w14 월별 등록/해결
│   │   ├── created_vs_resolved_collector.py  # w3 주간 생성/해결
│   │   ├── sla_delay_collector.py   # w10 SLA 지연 현황
│   │   ├── resolution_collector.py  # w11 유형별 해결시간
│   │   └── recent_collector.py      # w12 미완료 이슈
│   ├── mappers/                     # Entity ↔ Schema 매핑
│   ├── ports/                       # 애플리케이션 레벨 포트
│   └── scheduler/                   # APScheduler 설정
├── infrastructure/                  # 외부 어댑터 구현체
│   ├── container.py                 # 의존성 주입 컨테이너
│   ├── job_runner.py                # 비동기 Job 실행 엔진
│   ├── external/
│   │   ├── jira_client.py           # Jira Cloud REST API v3 클라이언트
│   │   └── gemini_client.py         # Google Gemini AI 클라이언트
│   ├── persistence/
│   │   ├── database.py              # SQLAlchemy async 엔진 & 세션
│   │   ├── models.py                # ORM 모델 (Report, Widget, Job)
│   │   ├── report_repository_impl.py
│   │   ├── job_repository_impl.py
│   │   └── widget_serializer.py     # Widget 데이터 JSON 직렬화
│   ├── security/                    # JWT 인증 로직
│   ├── config/                      # pydantic-settings 환경변수
│   └── storage/                     # 파일 스토리지 (로컬 볼륨)
├── presentation/                    # HTTP 어댑터
│   ├── api/
│   │   ├── v1/
│   │   │   ├── router.py            # APIRouter 집계
│   │   │   ├── reports.py           # GET /reports 엔드포인트
│   │   │   ├── trigger.py           # POST /trigger, GET /jobs/{id}
│   │   │   ├── auth.py              # POST /auth/login
│   │   │   ├── search.py            # GET /search
│   │   │   ├── storage.py           # 파일 스토리지 CRUD
│   │   │   └── config.py            # GET /config (LOGIN 플래그 노출)
│   │   └── deps.py                  # FastAPI Depends 공통 의존성
│   └── schemas/                     # Pydantic 요청/응답 스키마
└── shared/                          # 공통 유틸리티
```

---

## 프론트엔드 레이어 구조

```
frontend/src/
├── main.tsx                         # React 앱 진입점
├── domain/                          # 순수 TypeScript 타입
│   ├── Report.ts                    # ReportDetail, ReportSummary
│   ├── Issue.ts                     # RecentIssue
│   ├── Job.ts                       # JobStatus, TriggerParams
│   ├── Storage.ts                   # StorageItem
│   └── Config.ts                    # AppConfig
├── app/                             # 앱 수준 설정
│   ├── App.tsx                      # QueryClientProvider, RouterProvider 마운트
│   ├── router.tsx                   # React Router v6 라우트 정의
│   ├── store/
│   │   ├── reportStore.ts           # Zustand: currentReport, selectedReportId
│   │   ├── uiStore.ts               # Zustand: isTriggerLoading, triggerMessage
│   │   └── authStore.ts             # Zustand: token, isAuthenticated
│   └── context/                     # React Context (필요 시)
├── infrastructure/
│   ├── api/
│   │   ├── client.ts                # Axios 인스턴스 (토큰 인터셉터)
│   │   ├── reportApi.ts             # 보고서 CRUD + trigger + jobStatus
│   │   ├── authApi.ts               # 로그인 API
│   │   ├── searchApi.ts             # 전체 검색 API
│   │   └── storageApi.ts            # 파일 스토리지 API
│   └── hooks/
│       ├── useReport.ts             # useLatestReport, useReportById,
│       │                            # useAllReports, useDeleteReport,
│       │                            # useRefreshReport (폴링 포함)
│       ├── useAuth.ts               # useLogin, useLogout
│       ├── useConfig.ts             # useAppConfig
│       └── useStorage.ts            # useStorageList, useUploadFile, ...
├── presentation/
│   ├── pages/
│   │   ├── DashboardPage.tsx        # 최신/특정 보고서 대시보드
│   │   ├── HistoryPage.tsx          # 보고서 이력 목록
│   │   ├── StoragePage.tsx          # 파일 스토리지 관리
│   │   ├── StoragePreviewPage.tsx   # 파일 미리보기
│   │   └── LoginPage.tsx            # 로그인
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Layout.tsx           # 전체 레이아웃 래퍼
│   │   │   ├── Header.tsx           # 헤더 (RefreshButton 포함)
│   │   │   ├── Sidebar.tsx          # 사이드바 내비게이션
│   │   │   └── MobileTabBar.tsx     # 모바일 하단 탭
│   │   ├── common/
│   │   │   ├── RefreshButton.tsx    # 현재 보고서 재조회 버튼
│   │   │   ├── TriggerButton.tsx    # 신규 보고서 생성 버튼
│   │   │   ├── GenerateReportModal.tsx
│   │   │   ├── SearchWidget.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── StatusBadge.tsx
│   │   │   └── IssueModalShell.tsx
│   │   ├── cards/
│   │   │   ├── SummaryCard.tsx      # 숫자 요약 카드
│   │   │   └── AiSummaryCard.tsx    # AI 분석 요약 카드
│   │   ├── charts/
│   │   │   ├── SlaDonutChart.tsx    # w9 SLA 위반 도넛
│   │   │   ├── ReasonPieChart.tsx   # w10 SLA 지연 파이
│   │   │   ├── TypeBarChart.tsx     # w11 유형별 바
│   │   │   ├── TrendLineChart.tsx   # w3 생성/해결 트렌드
│   │   │   ├── SlaMonthlyLineChart.tsx  # w7~w8 월별 SLA 라인
│   │   │   ├── MonthlyCountChart.tsx    # w13~w14 월별 건수
│   │   │   └── ResolutionTimeChart.tsx  # w12 미완료 이슈 산점도
│   │   ├── tables/                  # 모달 형태의 이슈 상세 테이블
│   │   └── storage/                 # 스토리지 UI 컴포넌트
│   └── styles/
└── shared/
    └── constants.ts                 # 차트 색상, 공통 상수
```

---

## 보고서 생성 흐름

```
[클라이언트]
  │  POST /api/v1/trigger  { start_date, end_date }
  │
[trigger.py]
  │  Job 생성 (status=pending) → job_id 반환
  │
[job_runner.py]  ← asyncio.create_task 로 백그라운드 실행
  │  status = running
  │
  ├── JiraClient.fetch_issues()       ← Jira Cloud REST API v3
  │     (JQL: project=TAC AND created >= start_date ...)
  │
  ├── WidgetCollector × 14            ← 각 위젯 데이터 독립 계산
  │
  ├── GeminiClient.generate_summary() ← AI_ENABLED=true 인 경우
  │
  ├── ReportRepositoryImpl.save()     ← PostgreSQL upsert
  │
  └── status = done  (report_id 기록)

[클라이언트]
  │  GET /api/v1/jobs/{job_id}  (2초 폴링, 최대 3분)
  │  status=done → queryClient.invalidateQueries(['reports'])
  │  → DashboardPage 자동 갱신
```

---

## 데이터 모델

### Report

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL PK | |
| `week_start` | DATE | 집계 시작일 |
| `week_end` | DATE | 집계 종료일 |
| `report_date` | DATE | 보고서 생성일 |
| `ai_analysis` | TEXT | Gemini 생성 요약 |
| `created_at` | TIMESTAMPTZ | |

### Widget

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL PK | |
| `report_id` | FK → Report | |
| `widget_key` | VARCHAR | w1~w14 |
| `total` | INTEGER | 집계 합계 |
| `data` | JSONB | 위젯별 상세 데이터 |

### Job

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | UUID PK | |
| `status` | ENUM | pending/running/done/error |
| `report_id` | FK → Report (nullable) | |
| `error` | TEXT | 에러 메시지 |
| `created_at` | TIMESTAMPTZ | |

---

## 인증 구조

`LOGIN=true` 환경변수로 활성화합니다. `POST /api/v1/auth/login` 에서 JWT Access Token 을 발급하며, 이후 모든 보호된 엔드포인트는 `Authorization: Bearer <token>` 헤더를 요구합니다. `LOGIN=false` 시 인증 미들웨어가 bypass 됩니다.
