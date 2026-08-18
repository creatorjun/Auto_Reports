# Frontend Components

기준 경로는 `src/presentation/components`입니다.

| 폴더 | 책임 |
|------|------|
| `auth` | route 인증 가드 |
| `layout` | Header, Sidebar, MobileTabBar, Outlet layout |
| `common` | loading, error boundary, 검색, 보고서 생성, 공통 modal shell·table |
| `cards` | AI, SLA, 숫자 summary card와 업무 유형별 생성·완료 card |
| `charts` | 월별, SLA, 사유, 처리시간, 유형 Recharts 시각화 |
| `tables` | 이슈 종류별 modal과 history report table |
| `history` | 보고서 삭제 확인 |
| `partner` | 조직, 멤버, 이슈 panel과 row |
| `site` | 생성 form helper와 node·patch·visit section/form |
| `storage` | table, modal, icon, preview, link 복사와 표시 utility |

## 공통 설계

- 원격 동작은 props 또는 Presentation hook을 통해 수행합니다.
- component는 axios adapter를 import하지 않습니다.
- 이슈 표는 `IssueModalShell`과 `IssueTableModal`을 재사용합니다.
- query key와 표시 상수는 `presentation/config`, formatter는 `presentation/utils`를 사용합니다.
- 큰 파일 preview renderer는 lazy loading하고 보고서 생성 modal은 배포 안정성을 위해 메인 bundle에 포함합니다.

## File preview

`FilePreviewModal`은 PDF, Word, Excel, Markdown, 이미지와 텍스트를 표시합니다. Storage gateway를 주입받아 preview·download URL을 생성하며 token과 API base URL의 세부사항을 직접 구성하지 않습니다.
