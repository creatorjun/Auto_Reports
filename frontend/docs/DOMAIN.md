# frontend/docs/DOMAIN.md

# Domain 타입 정의

`src/domain/` 에는 순수 TypeScript 인터페이스만 존재합니다. 외부 라이브러리 의존이 없습니다.

---

## Config.ts

```ts
interface AppConfig {
  jira_base_url: string   // 예: 'https://seculayer.atlassian.net'
}
```

---

## Issue.ts

```ts
interface RecentIssue {
  key:          string   // Jira 이슈 키 (예: TAC-1234)
  summary:      string
  type:         string
  status:       string
  stage_index:  number   // 0~6, STAGE_MAP 참조
  created:      string   // ISO 8601
  elapsed_days: number
  reporter:     string
  tac_team:     string
}
```

---

## Job.ts

```ts
interface TriggerAccepted {
  job_id:  string
  message: string
}

interface JobStatus {
  job_id:    string
  status:    'pending' | 'running' | 'done' | 'error'
  report_id: number | null
  error:     string | null
}

interface TriggerParams {
  start_date?: string   // YYYY-MM-DD
  end_date?:   string   // YYYY-MM-DD
}
```

---

## Partner.ts

```ts
interface PartnerOrg {
  id:   string
  name: string
}

interface PartnerMember {
  account_id:   string
  display_name: string
  email:        string
}

interface PartnerIssue {
  key:          string
  summary:      string
  type:         string
  status:       string
  stage_index:  number
  created:      string
  elapsed_days: number
  reporter:     string
  tac_team:     string
}
```

> `PartnerIssue`와 `RecentIssue`는 현재 동일한 형태입니다.  
> 리팩토링 시 공통 `BaseIssue`로 추상화를 고려하세요. ([REFACTORING_NOTES.md](./REFACTORING_NOTES.md) 참조)

---

## Report.ts

```ts
type Sentiment = 'good' | 'warning' | 'critical'

interface AiAnalysis {
  summary:         string
  risks:           string[]
  recommendations: string[]
  sentiment:       Sentiment
}

interface WidgetResult {
  name:  string
  total: number
  jql:   string
  data:  Record<string, unknown> | null
}

interface ReportSummary {
  id:          number
  week_start:  string   // YYYY-MM-DD
  week_end:    string
  report_date: string
  created_at:  string
  sentiment:   Sentiment | null
}

interface ReportDetail extends ReportSummary {
  widgets:     Record<string, WidgetResult>
  ai_analysis: AiAnalysis | null
}
```

---

## Site.ts

```ts
type SiteStatus    = 'installing' | 'active' | 'inactive' | 'expired' | 'maintenance'
type ContractType  = '정식라이센스' | '임시라이센스'
type NodeRole      = 'AllInOne' | 'Analyzer' | 'Collector' | 'Proxy'
type PatchType     = '정기패치' | '긴급패치' | '핫픽스'
type PatchResultStatus = '성공' | '실패' | '롤백'
```

주요 인터페이스:

| 인터페이스 | 용도 |
|---|---|
| `ContactInfo` | 고객/유지보수 담당 연락처 |
| `Credential` | username/password/ip/port |
| `AccessCredentials` | cli/web/db/vpn 자격증명 묶음 |
| `DeploymentNode` | 서버 노드 정보 (HW 스펙·IP·디스크) |
| `DeploymentNodePayload` | 노드 생성/수정 요청 DTO |
| `PatchHistory` | 패치 이력 |
| `PatchHistoryPayload` | 패치 이력 생성 요청 DTO |
| `VisitHistory` | 방문 이력 |
| `VisitHistoryPayload` | 방문 이력 생성 요청 DTO |
| `SiteSummary` | 목록용 요약 (id·site_name·status·contract_end_date) |
| `SiteDetail` | 상세 (nodes·patch_histories·visit_histories 포함) |
| `SiteCreatePayload` | 사이트 생성 요청 DTO |
| `SiteUpdatePayload` | 사이트 수정 요청 DTO |

---

## Storage.ts

파일 스토리지 관련 타입 (StorageFile, StorageDir 등).
