# Frontend Infrastructure

문서 기준: 2026-10-21.

Infrastructure는 `src/infrastructure/api`의 HTTP adapter와 `src/infrastructure/export`의 PDF·Excel 생성 adapter 및 `src/infrastructure/preview`의 파일 해석 adapter를 포함합니다. React hook과 Zustand store는 이 레이어에 두지 않습니다.

## HTTP client

`client.ts`는 다음 브라우저 I/O를 담당합니다.

- `VITE_API_BASE_URL` 또는 `/api/v1` base URL
- 30초 timeout과 refresh cookie 전송
- `AuthSessionPort`에서 받은 access token 주입
- 동시 401 요청의 단일 refresh Promise 공유
- refresh 실패 시 인증 제거와 로그인 이동
- axios 오류를 Application의 `RequestError`로 정규화

client는 Presentation store를 직접 import하지 않습니다. `main.tsx`가 store의 get/set 동작을 `AuthSessionPort` 형태로 주입합니다.

초기 복원과 동시 401은 같은 refresh Promise를 사용합니다. 로그인·로그아웃이 시작되면 이전 세대의 갱신 응답을 적용하지 않으며, 로그아웃은 진행 중인 갱신이 완료된 뒤 cookie를 제거해 응답 순서 경합을 방지합니다.

## Gateway adapter

| 파일 | 구현 계약 | 역할 |
|------|-----------|------|
| `authApi.ts` | `AuthGateway` | 관리자 로그인, Jira OAuth 시작·설정 조회, 갱신, 로그아웃, 사용자 조회 |
| `reportApi.ts` | `ReportGateway` | 보고서 조회·삭제, 생성 트리거와 잡 상태 |
| `siteApi.ts` | `SiteGateway` | 사이트 aggregate와 하위 이력 관리 |
| `partnerApi.ts` | `PartnerGateway` | 파트너 조직, 멤버, 이슈 조회 |
| `searchApi.ts` | `SearchGateway` | Jira 이슈 검색과 base URL 조회 |
| `slaDashboardApi.ts` | `SlaDashboardGateway` | 보고서 범위 내 티켓 본문·첨부 이미지, 최신 보고서 기반 이슈 활동과 offset에 따른 댓글 페이지 조회 |
| `slaStatusApi.ts` | `SlaStatusGateway` | SLA 현황의 현재 수집 스냅샷 조회와 강제 새로고침 |
| `slaViolationApi.ts` | `SlaViolationGateway` | SLA 위반 보고서 생성, 최신·ID·이력 조회 |
| `redeploymentApi.ts` | `RedeploymentGateway` | 최신 재배포 조회·갱신 |
| `issueManagementApi.ts` | `ApplicationServices.issueManagement` | 전체 이슈 동기화 스냅샷 조회 |
| `auditLogApi.ts` | `AuditLogGateway` | 관리자 감사로그 조건 조회 |
| `storageApi.ts` | `StorageGateway` | 파일 목록, 업로드, 다운로드, 미리보기, 삭제 |

위 HTTP adapter는 HTTP 응답을 Domain 모델로 반환합니다. 사이트 하위 리소스 변경 API는 백엔드 계약대로 갱신된 `SiteDetail` aggregate를 반환합니다.

TanStack Query 기반 hook은 `src/presentation/hooks`에 있으며 `useApplicationServices()`로 위 gateway를 주입받습니다.

일반 보고서의 `watchJob`은 SSE와 polling 전환을 소유합니다. SLA 위반·재배포 생성 요청은 최대 10분 HTTP timeout을 사용하며 별도 job stream이 없습니다. 취소 가능한 조회는 Application의 `CancellationSignal`을 받아 HTTP 취소로 연결합니다.

`SlaStatusGateway.getSnapshot(refresh, signal)`은 `slaStatusApi.ts`에서 `GET /sla-status`로 연결합니다. 일반 조회는 서버의 60초 캐시를 사용하며 수동 새로고침은 `refresh=true`를 보내 강제로 다시 수집합니다. adapter의 timeout은 120초이며 취소 신호를 그대로 전달합니다. 응답은 `domain/SLAStatus.ts`의 `SlaStatusSnapshot`입니다. 기간별 생성·DB 보고서 저장·히스토리 API와 별도 계약입니다.

`reportApi`는 연간 보고서와 차트 상세도 조회합니다. `slaDashboardApi`는 댓글 이미지 바이너리 조회를 지원합니다. 파일 변환 요청은 150초 timeout, 바이너리는 `BinaryContent`와 명시적 object URL 해제를 사용합니다.

Vite 개발 프록시의 기본 backend 주소는 `http://backend:8000`입니다. 호스트에서 `pnpm dev`를 실행하면 이 이름이 해석되지 않을 수 있으므로 개발 주소/프록시를 실제 API 주소에 맞춰야 합니다. 빌드된 앱 기본 base URL은 `/api/v1`이며 Compose nginx가 이를 전달합니다.

## PDF·Excel 생성 adapter

`DashboardExportGateway.renderPdf(document)`와 `renderExcel(document)`은 같은 `DashboardPdfDocument`를 받아 `BinaryContent`를 반환하는 Application 계약입니다. `main.tsx`가 `dashboardPdfExporter`와 `dashboardExcelExporter`를 조립하여 `ApplicationServices.dashboardExport`에 주입하며, Presentation은 pdfmake나 xlsx를 직접 import하지 않습니다.

`dashboardPdfExporter.ts`는 내보내기 요청 시 pdfmake와 `dashboardPdfDefinition.ts`를 지연 로드합니다. 문서는 A4 가로 방향으로 구성하고, 차트는 SVG 벡터와 2열 배치를 사용합니다. 표는 페이지가 넘어가면 제목과 열 머리글을 반복합니다.

NanumGothic Regular·Bold 글꼴은 `src/assets/fonts`에서 앱과 함께 배포하고 PDF에 포함합니다. PDF 생성은 브라우저에서 수행하며, 별도 백엔드 변환 API·CDN·외부 문서 앱을 호출하지 않습니다. 생성 결과는 기존 `BinaryContent` 경계를 통해 다운로드하고 object URL을 해제합니다.

`dashboardExcelExporter.ts`는 기존 xlsx 의존성과 `dashboardExcelWorkbook.ts`를 지연 로드합니다. 적용 필터를 정보 시트에, 각 지표·차트 수치·표를 별도 시트에 저장합니다. 차트의 숫자와 빈 값, 이슈 문자열과 링크를 보존하고 시트 이름의 길이·금지 문자·중복을 처리합니다. Excel 생성과 다운로드도 브라우저 안에서 완료하며 PDF와 같은 바이너리 수명 계약을 사용합니다.
