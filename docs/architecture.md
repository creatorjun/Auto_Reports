# 시스템 아키텍처

> **Version 1.0** | 2026-07-09

## 전체 구성

```
┌─────────────────────────────────────────────────────┐
│  Browser                                            │
│  React 18 + TypeScript + Vite + Tailwind CSS        │
│  (tac_frontend · Nginx · port 80)                   │
└────────────────────┬────────────────────────────────┘
                     │ HTTP /api/*
┌────────────────────▼────────────────────────────────┐
│  Backend                                            │
│  FastAPI + APScheduler (tac_backend · port 8000)    │
└──────┬──────────────────────────┬───────────────────┘
       │ httpx async              │ asyncpg / SQLAlchemy
┌──────▼──────┐          ┌────────▼──────────┐
│  Jira API   │          │  PostgreSQL 16     │
│ (Atlassian) │          │  (tac_db)          │
└─────────────┘          └───────────────────┘
```

## 백엔드 레이어 구조

백엔드는 **클린 아키텍처** 원칙을 따릅니다.

```
backend/src/
├── domain/                  # 엔티티, 포트 인터페이스 (외부 의존성 없음)
│   ├── entities/
│   │   ├── widget.py        # WidgetResult 제네릭 컨테이너
│   │   └── widget_data.py   # 각 위젯별 데이터 클래스
│   └── ports/
│       └── jira_port.py     # JiraPort 추상 인터페이스
│
├── application/             # 비즈니스 로직
│   ├── services/
│   │   ├── query_builder.py # 위젯별 JQL 생성
│   │   ├── query_config.py  # 프로젝트/상태/SLA 설정값
│   │   └── report_service.py# 전체 수집 오케스트레이션
│   └── widgets/             # 위젯별 Collector (w1~w12)
│       ├── base.py
│       ├── count_collector.py
│       ├── created_vs_resolved_collector.py
│       ├── monthly_collector.py
│       ├── recent_collector.py
│       ├── resolution_collector.py
│       └── sla_delay_collector.py
│
├── infrastructure/          # 외부 어댑터
│   ├── external/
│   │   ├── jira_client.py   # JiraPort 구현체 (httpx)
│   │   └── gemini_client.py # Gemini AI 클라이언트
│   ├── persistence/         # DB 모델 및 레포지터리
│   ├── config/              # 설정 로딩
│   ├── container.py         # 의존성 주입 컨테이너
│   └── job_runner.py        # APScheduler 래퍼
│
└── presentation/            # FastAPI 라우터 및 스키마
    ├── api/v1/
    │   ├── reports.py       # GET /api/reports/latest
    │   ├── trigger.py       # POST /api/trigger
    │   └── config.py        # GET /api/config
    └── schemas/             # Pydantic 응답 스키마
```

## 프론트엔드 레이어 구조

```
frontend/src/
├── infrastructure/
│   └── hooks/               # React Query 훅 (useReport, useConfig 등)
└── presentation/
    └── components/
        ├── cards/           # SummaryCard 등 수치 카드 컴포넌트
        ├── charts/          # ResolutionTimeChart (w12 단계별 그래프)
        ├── tables/          # 모달 컴포넌트 (WeeklyCreatedModal 등)
        ├── common/          # 공통 UI (LoadingSpinner 등)
        └── layout/          # Header, Layout 래퍼
```

## 데이터 흐름

```
[APScheduler cron]          [수동 트리거 POST /api/trigger]
        │                              │
        └──────────┬───────────────────┘
                   ▼
          ReportService.run()
                   │
          ┌────────┴──────────────────┐
          │  w1~w12 Collector 병렬 실행 │  (asyncio.gather)
          └────────┬──────────────────┘
                   ▼
          결과 직렬화 → PostgreSQL 저장
                   │
          GET /api/reports/latest
                   ▼
          React 대시보드 렌더링
```
