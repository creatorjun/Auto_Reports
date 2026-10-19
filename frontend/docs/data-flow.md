# Frontend Data Flow

문서 기준: 2026-10-16.

## 공통 요청

```text
Page/Component → Presentation hook → Application gateway
              → Infrastructure HTTP adapter → FastAPI
              → Domain 응답 모델 → TanStack Query → UI
```

`main.tsx`가 인증·일반 보고서·SLA·재배포·전체 이슈·감사로그·사이트·파일·파트너·검색 gateway와 export/preview 구현을 Provider에 주입합니다. 컴포넌트는 구체 adapter를 import하지 않습니다.

## 생성과 갱신

| 화면 | 요청부터 표시까지 |
|---|---|
| 일반 대시보드 | DashboardGenerateForm → period/date → ReportGateway.trigger → job_id → SSE 또는 polling → report_id → 최신 일반 query 갱신 |
| 연간 전용 | 연도 생성 버튼 → start_date/end_date → 같은 job 흐름 → annual query 갱신 |
| SLA 현황 | period/date → SlaViolationGateway.generate → 수집·DB 저장이 완료된 응답 → 최신·ID 캐시 설정 및 이력 무효화 |
| 재배포 현황 | 서버 08시 작업 또는 generate → 당일 DB upsert → 최신 응답; 화면은 60초마다 최신 저장본 조회 |
| 전체 이슈 | 서버 시작 시 DB 마지막 목록 복원 → getIssues로 즉시 반환 및 필요 시 백그라운드 갱신 → 기존 목록을 유지하며 화면 2초/30초 polling; 페이지 이탈 후 메모리 캐시는 1시간 유지 |

일반 job 구독은 Layout이 소유합니다. SSE 연결 실패 시 adapter가 backoff polling으로 전환하고 종료 시 연결·타이머를 회수합니다. SLA·재배포는 SSE가 아닌 장기 HTTP 요청이며 최신 조회만으로 Jira 수집을 시작하지 않습니다.

## SLA 화면 계산

```text
저장 보고서 tickets
  → 공통 유형·현재 상태·반기 필터
  → 전체/최초응답/해결/동시 위반 카드
  → 선택 SLA 범위
  → 현재 상태 분포 + KST 생성월/일 추이
  → 상태·날짜 선택 AND 검색
  → SLA 위반 티켓 통합 목록 → 저장된 정렬·너비 → 위반 항목 배지가 있는 접힌 행/상세
```

위 흐름은 저장본만 사용합니다. 동시 위반 티켓도 한 행에 최초응답 위반·해결시간 위반 배지를 함께 표시하며, 카드 선택은 행의 범위를 바꿉니다. 현재 Jira 차트 상세를 별도 조회하는 연간 보고서와 구분합니다. 화면의 조건은 DB 스냅샷·히스토리 수치를 바꾸지 않습니다.

## 내보내기

내보내기 클릭 → 보고서/이슈·필터·검색 조건 복사 → 별도 라이트 테마 고정 폭 렌더링 → 전체 행·차트 원본 수치 캡처 → DashboardExportGateway → PDF 또는 Excel BinaryContent → 다운로드 → object URL 해제 순서입니다. 다운로드 시작 후 화면 조건 변화와 페이지 번호는 결과를 바꾸지 않습니다.

## 인증과 파일

로그인 → auth store access token → interceptor Authorization → 401 시 공유 refresh Promise → 재시도 또는 세션 제거 흐름입니다. refresh cookie와 access token은 다른 저장 수명입니다. HTTP 오류는 `RequestError`로 정규화합니다.

Jira 링크는 `/config`의 base URL과 `JiraContext`로 생성합니다. 파일 I/O는 StorageGateway, 형식 해석은 PreviewParserPort를 사용합니다. 댓글 이미지와 파일 바이너리의 object URL은 화면에서 더 이상 쓰지 않으면 해제합니다. 취소된 이전 검색/미리보기 응답은 새 선택 화면에 반영하지 않습니다.
