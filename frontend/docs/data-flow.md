# Frontend Data Flow

문서 기준: 2026-10-21.

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
| SLA 현황 | useSlaStatus → SlaStatusGateway.getSnapshot → GET /sla-status → 현재 스냅샷 → query 캐시와 화면 표시; 수동 새로고침은 refresh=true |
| SLA 위반 | period/date → SlaViolationGateway.generate → 수집·DB 저장이 완료된 응답 → 최신·ID 캐시 설정 및 이력 무효화 |
| 재배포 현황 | 서버 08시 작업 또는 generate → 당일 DB upsert → 최신 응답; 화면은 60초마다 최신 저장본 조회 |
| 전체 이슈 | 서버 시작 시 DB 마지막 목록 복원 → getIssues로 즉시 반환 및 필요 시 백그라운드 갱신 → 기존 목록을 유지하며 화면 2초/30초 polling; 페이지 이탈 후 메모리 캐시는 1시간 유지 |

일반 job 구독은 Layout이 소유합니다. SSE 연결 실패 시 adapter가 backoff polling으로 전환하고 종료 시 연결·타이머를 회수합니다. SLA 위반·재배포 생성은 SSE가 아닌 장기 HTTP 요청이며 최신 저장본 조회만으로 Jira 수집을 시작하지 않습니다. SLA 현황의 일반 조회는 60초 캐시가 없거나 만료되면 현재 값을 수집하며 `refresh=true`는 캐시를 우회합니다. 성공 결과에는 수집 시각을 표시하고 실패하면 마지막 성공 데이터를 유지합니다.

## SLA 현황 계산

```text
SlaStatusPage → useSlaStatus → SlaStatusGateway → slaStatusApi
  → GET /sla-status → SLAStatus.ts 현재 수집 스냅샷
  → 잔여율 0% 이상 30% 미만인 미위반 고유 티켓
  → 전체/잔여 10% 미만/진행 중 SLA 포함/일시정지 SLA 포함 위젯
  → 위젯 범위 AND 검색 AND 현재 상태 AND SLA 단계
  → 잔여율 낮은 순 정렬 → 티켓당 한 행
  → 잔여율·시간·상태·담당자·최대 체류 단계
  → 펼침: 해결시간 SLA 기준 표시 대상 전체 상태별 체류시간 + 목표·사용·잔여
```

표시 계산은 `application/services/slaStatus.ts`가 담당합니다. 위젯 건수는 전체 수집 결과를 기준으로 유지하고 필터는 목록에 적용합니다. 하나의 티켓에 진행 중·일시정지 SLA가 함께 있으면 두 위젯에 모두 포함될 수 있으므로 범위별 건수의 합을 전체로 사용하지 않습니다. 최대 체류 단계·상태별 시간은 기존 SLA 표시 정책대로 닫힘·결과 대기 중·자료 요청 중·보류 중을 제외합니다. SLA 현황에는 생성 기간·보고서 ID·저장 이력이 없습니다.

## SLA 위반 화면 계산

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
