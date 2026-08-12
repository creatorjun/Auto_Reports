# Frontend Infrastructure

Infrastructure는 `src/infrastructure/api`의 HTTP adapter만 포함합니다. React hook, Zustand store, UI 타입은 이 레이어에 두지 않습니다.

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
| `storageApi.ts` | `StorageGateway` | 파일 목록, 업로드, 다운로드, 미리보기, 삭제 |

각 adapter는 HTTP 응답을 Domain 모델로 반환합니다. 사이트 하위 리소스 변경 API는 백엔드 계약대로 갱신된 `SiteDetail` aggregate를 반환합니다.

TanStack Query 기반 hook은 `src/presentation/hooks`에 있으며 `useApplicationServices()`로 위 gateway를 주입받습니다.
