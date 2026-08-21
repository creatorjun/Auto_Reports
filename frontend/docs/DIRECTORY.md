# Frontend Directory

```text
frontend/
├── package.json
├── pnpm-lock.yaml
├── pnpm-workspace.yaml
├── tests/
│   └── architecture.test.mjs
└── src/
    ├── main.tsx
    ├── app/
    │   ├── App.tsx
    │   └── router.tsx
    ├── domain/
    │   ├── Auth.ts
    │   ├── Config.ts
    │   ├── Dashboard.ts
    │   ├── Issue.ts
    │   ├── Job.ts
    │   ├── Partner.ts
    │   ├── Report.ts
    │   ├── Search.ts
    │   ├── Site.ts
    │   ├── SlaDashboard.ts
    │   ├── Storage.ts
    │   └── WidgetId.ts
    ├── application/
    │   ├── errors/RequestError.ts
    │   └── ports/
    │       ├── ApplicationServices.ts
    │       └── AuthSessionPort.ts
    ├── infrastructure/
    │   └── api/
    │       ├── client.ts
    │       ├── authApi.ts
    │       ├── reportApi.ts
    │       ├── partnerApi.ts
    │       ├── searchApi.ts
    │       ├── siteApi.ts
    │       ├── slaDashboardApi.ts
    │       └── storageApi.ts
    └── presentation/
        ├── components/
        ├── pages/
        ├── hooks/
        ├── state/
        ├── context/
        ├── config/
        ├── utils/
        └── styles/
```

새 외부 연동은 Application gateway 계약을 먼저 정의한 뒤 Infrastructure adapter로 구현합니다. React hook과 컴포넌트는 `presentation`에 두며 API adapter를 직접 import하지 않습니다. UI 상수와 query key는 `presentation/config`, 표시용 formatter는 `presentation/utils`에 둡니다.
