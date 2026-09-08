# Frontend Infrastructure

Infrastructure는 `src/infrastructure/api`의 HTTP adapter와 `src/infrastructure/export`의 PDF 생성 adapter를 포함합니다. React hook과 Zustand store는 이 레이어에 두지 않습니다.

## HTTP client

`client.ts`는 다음 브라우저 I/O를 담당합니다.

- `VITE_API_BASE_URL` 또는 `/api/v1` base URL
- 30초 timeout과 refresh cookie 전송
- `AuthSessionPort`에서 받은 access token 주입
- 동시 401 요청의 단일 refresh Promise 공유
- refresh 실패 시 인증 제거와 로그인 이동
- axios 오류를 Application의 `RequestError`로 정규화

client는 Presentation store를 직접 import하지 않습니다. `main.tsx`가 store의 get/set 동작을 `AuthSessionPort` 형태로 주입합니다.

## Gateway adapter

| 파일 | 구현 계약 | 역할 |
|------|-----------|------|
| `authApi.ts` | `AuthGateway` | 로그인, 갱신, 로그아웃, 사용자 조회 |
| `reportApi.ts` | `ReportGateway` | 보고서 조회·삭제, 생성 트리거와 잡 상태 |
| `siteApi.ts` | `SiteGateway` | 사이트 aggregate와 하위 이력 관리 |
| `partnerApi.ts` | `PartnerGateway` | 파트너 조직, 멤버, 이슈 조회 |
| `searchApi.ts` | `SearchGateway` | Jira 이슈 검색과 base URL 조회 |
| `slaDashboardApi.ts` | `SlaDashboardGateway` | 최신 보고서 기반 이슈 활동과 offset에 따른 티켓별 댓글 페이지 조회 |
| `storageApi.ts` | `StorageGateway` | 파일 목록, 업로드, 다운로드, 미리보기, 삭제 |

위 HTTP adapter는 HTTP 응답을 Domain 모델로 반환합니다. 사이트 하위 리소스 변경 API는 백엔드 계약대로 갱신된 `SiteDetail` aggregate를 반환합니다.

TanStack Query 기반 hook은 `src/presentation/hooks`에 있으며 `useApplicationServices()`로 위 gateway를 주입받습니다.

## PDF 생성 adapter

`DashboardExportGateway.renderPdf(document)`는 `DashboardPdfDocument`를 받아 `BinaryContent`를 반환하는 Application 계약입니다. `main.tsx`가 `dashboardPdfExporter`를 `ApplicationServices.dashboardExport`에 주입하며, Presentation은 pdfmake를 직접 import하지 않습니다.

`dashboardPdfExporter.ts`는 내보내기 요청 시 pdfmake와 `dashboardPdfDefinition.ts`를 지연 로드합니다. 문서는 A4 가로 방향으로 구성하고, 차트는 SVG 벡터와 2열 배치를 사용합니다. 표는 페이지가 넘어가면 제목과 열 머리글을 반복합니다.

NanumGothic Regular·Bold 글꼴은 `src/assets/fonts`에서 앱과 함께 배포하고 PDF에 포함합니다. PDF 생성은 브라우저에서 수행하며, 별도 백엔드 변환 API·CDN·외부 문서 앱을 호출하지 않습니다. 생성 결과는 기존 `BinaryContent` 경계를 통해 다운로드하고 object URL을 해제합니다.
