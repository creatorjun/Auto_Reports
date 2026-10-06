# frontend/docs/README.md

# Frontend 문서 인덱스

| 문서 | 설명 |
|------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 레이어 아키텍처 전체 구조 |
| [DIRECTORY.md](./DIRECTORY.md) | 파일/폴더 트리 및 역할 |
| [DOMAIN.md](./DOMAIN.md) | 도메인 타입 정의 상세 |
| [INFRASTRUCTURE.md](./INFRASTRUCTURE.md) | HTTP·PDF adapter와 인증·오류 경계 |
| [PRESENTATION.md](./PRESENTATION.md) | 페이지·컴포넌트 상세 |
| [components.md](./components.md) | 컴포넌트 그룹과 공통 설계 |
| [data-flow.md](./data-flow.md) | query, 인증, 잡 데이터 흐름 |
| [STATE.md](./STATE.md) | 전역 상태(Zustand) 상세 |
| [ROUTING.md](./ROUTING.md) | 라우팅 구조 및 가드 |
| [SHARED.md](./SHARED.md) | Shared 제거 원칙과 공용 요소의 소유 위치 |
| [DEPENDENCIES.md](./DEPENDENCIES.md) | 외부 라이브러리 목록 |
| [REFACTORING_NOTES.md](./REFACTORING_NOTES.md) | 전수 검토 위반사항과 완료 결과 |

메인 대시보드·과거 보고서·연간 보고서에서 다운로드 형식을 PDF 또는 Excel (.xlsx)로 선택하고 내보내기 버튼을 누르면 현재 필터와 표 전체 행을 포함한 파일을 다운로드합니다. Excel은 적용 필터, 지표, 차트 수치와 이슈 목록을 시트별로 저장합니다. 연간 재배포 품질 지표는 연간 전체 기준을 유지합니다. 동작과 범위는 [components.md](./components.md#대시보드-다운로드)에 정리했습니다.

`frontend` 디렉터리에서 `pnpm test:pdf`를 실행하면 PDF 생성, 한글 글꼴 포함, 표 전체 행과 반복 머리글을 검증합니다.
