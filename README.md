# SecuLayer · Auto Reports

Jira 데이터를 수집해 대시보드, 연간 보고서, SLA 위반, 재배포 현황과 전체 이슈를 제공하고, 공개 CVE·보안 뉴스를 모아 보여주는 사내 업무 포털입니다. React 프런트엔드, FastAPI 백엔드, PostgreSQL을 사용합니다.

문서 기준: 2026-10-28. 패키지와 API의 `1.0.0`은 고정 메타데이터이므로 기능 버전 확인에는 Git 커밋을 사용합니다. 문서는 현재 소스의 계약을 설명하며 특정 서버의 실시간 배포 상태를 보증하지 않습니다.

## 디렉터리 구조

```text
Auto_Reports/
├── README.md
├── .env.example
├── docker-compose.yml
├── Makefile
├── backend/
│   ├── src/
│   │   ├── domain/          업무 모델과 값
│   │   ├── application/     유스케이스, 집계 서비스, 포트
│   │   ├── infrastructure/  Jira, DB, 인증, 저장소, 스케줄러
│   │   ├── presentation/    API, 스키마, 매퍼, 메일 렌더러
│   │   ├── bootstrap/       의존성 조립
│   │   └── main.py          앱과 리소스 수명
│   ├── alembic/versions/    DB 마이그레이션
│   ├── scripts/             수집 진단·백필 도구
│   ├── tests/
│   ├── docs/
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── domain/          모델, 필터·정렬·요약 정책
    │   ├── application/     gateway 계약과 순수 서비스
    │   ├── infrastructure/  HTTP, PDF·Excel, 파일 파서
    │   ├── presentation/    화면, 훅, 상태, 테마
    │   ├── app/             앱과 라우터
    │   └── main.tsx         의존성 조립
    ├── tests/
    └── docs/
```

Domain/Application은 외부 프레임워크 구현을 모르며, 외부 동작은 Application 포트로 주입합니다. 구체 구현 조립은 백엔드 `bootstrap`·`main.py`, 프런트엔드 `main.tsx`에서 수행합니다.

## 화면과 보고서

| 메뉴 순서 | 기능 |
|---|---|
| 대시보드 | 최신 일반 보고서, 일·주·월·연 또는 시작일·종료일 지정 생성, 필터와 PDF·Excel |
| 전체 이슈 | 프로젝트 전체 이슈 동기화, 검색·필터, 전체 검색 결과 내보내기 |
| 집중 관리 항목 → SLA 현황 | 잔여율 30% 미만인 진행 SLA, 잔여 시간·목표·사용 시간, 상태별 체류시간 |
| 집중 관리 항목 → SLA 위반 | 전체·최초응답·해결·동시 위반 요약, 현재 상태 분포·생성 추이, 상세 티켓 |
| 집중 관리 항목 → 재배포 현황 | 2026-01-01 이후 완료 재배포와 현재 진행 중 재배포, 원인·월별 선택 |
| 연간 보고서 | 2024·2025·2026 전용 보고서, 연도 비교와 재배포 품질 지표 |
| 파트너 관리 | 조직·멤버별 이슈 |
| 사이트 관리 | 사이트, 장비, 접속 정보, 패치·방문 이력 |
| 장기 이슈 | 최신 일반 보고서의 최근 이슈 집합과 Jira 활동·댓글 |
| 파일 보관함 | 파일·폴더 관리, 미리보기, 업로드·다운로드 |
| CVE 취약점 대응 | 등록한 패키지의 모든 버전 CVE, OSV·Oracle Linux 수정 버전, 위험도 필터·기록 버전 영향·패키지 수집 상태 |
| 보안 뉴스 | 보안 권고·뉴스를 한 행씩 표시, 검색·위험도·출처 필터, 선택적 Gemini 한국어 한 줄 요약과 영구 캐시 |

`집중 관리 항목`과 `연간 보고서`는 해당 메뉴 버튼을 가리킬 때 펼쳐지고 메뉴 영역을 벗어나면 접힙니다. 모바일은 클릭으로 조작합니다. **보고서 히스토리** 이동 버튼은 모든 페이지에서 표시하지 않으며 `/history` 주소로 직접 접근할 수 있습니다. **감사로그**는 `SUPERADMIN`에게만 추가 표시됩니다.

사이드바의 로그아웃 위에는 로그인한 사용자 이름과 ID를 표시하며, Jira 로그인 사용자에게는 **Jira 알림** 버튼도 표시합니다. 본인의 Jira 권한으로 전체·직접·관심 알림을 조회하며, 읽음 상태는 조회 시점의 Jira 값을 표시합니다. 패널에서 알림을 열어도 읽음 상태를 변경하지 않습니다. 연결 만료 또는 서버 재시작 후에는 Jira 재로그인이 필요하며 앱 로그인은 유지됩니다. [Jira 알림 연동과 운영](backend/docs/15_jira_notifications.md)을 참고하세요.

| 보고서 | 생성·갱신 | 저장 계약 |
|---|---|---|
| 일반 대시보드 | 기간·기준일로 수동 생성, `SCHEDULE_CRON` 정기 생성; 최신 일반 보고서는 기본 5분 주기 갱신 | `reports`, `scope=standard`; 생성 시 새 ID, 갱신은 같은 ID |
| 연간 전용 | 연도별 생성; 백엔드는 현재 연도 저장본을 기본 5분 주기 갱신 | `reports`, `scope=annual`; 최신 일반 보고서와 분리 |
| SLA 현황 | 현재 미완료 티켓 조회·새로고침 | 60초 메모리 캐시; 기간별 이력 저장 없음 |
| SLA 위반 | 주·월·연 및 기준일로 수동 생성 | `sla_violation_reports`; 성공할 때 새 불변 스냅샷, 히스토리 자동 저장 |
| 재배포 현황 | 매일 08:00 KST, 시작 시 누락 보충, 지금 갱신 | `redeployment_reports`; KST 날짜별 한 건, 당일 갱신은 대체 |

대시보드의 일간은 선택 날짜 하루이며, 대시보드와 SLA 위반의 주간은 선택 날짜가 속한 주의 월요일~일요일 전체, 월간·연간은 해당 달·연도 전체입니다. 예를 들어 기준일이 2026-10-14이면 주간은 10월 12일~18일, 월간은 10월 1일~31일, 연간은 1월 1일~12월 31일이며 KST 기준 종료일 전체를 포함합니다. 기존 저장 보고서는 유지하며 새로 생성할 때 변경된 기간 기준을 적용합니다. 대시보드의 선택 기간 생성·완료 위젯은 저장된 범위에 따라 `일간 생성·완료`, `주간 생성·완료`, `10월 생성·완료`, `연간 생성·완료`로 표시하고, 한 주·한 달·한 해 전체가 아닌 기존 보고서는 일수 표시를 유지합니다. 대시보드에서 연간을 선택해도 일반 보고서이며 별도 연간 메뉴의 보고서와 구분합니다. 날짜 선택만으로 현재 표시 중인 보고서는 바뀌지 않습니다. `기간 지정`에서는 시작일·종료일을 직접 선택하며, KST 기준 시작일 00:00 이상부터 종료일 다음 날 00:00 미만까지 집계합니다. 같은 날도 선택할 수 있고 종료일은 오늘까지 허용하며, 새로고침은 마지막 저장 보고서의 지정 기간을 유지합니다.

대시보드의 **보고서 최신화**, Windows **Ctrl+R**, Mac **Cmd+R**은 마지막에 생성된 일반 보고서의 저장된 조회 기간으로 전체 데이터를 다시 수집합니다. Jira 캐시를 우회하고 완료된 결과를 새 보고서로 저장해 표시합니다. 생성 폼의 미실행 조건이나 열어 둔 과거 보고서의 기간은 사용하지 않습니다. **Ctrl+Shift+R / Cmd+Shift+R**은 브라우저 새로고침으로 유지합니다.

SLA 위반은 **티켓 생성일**로 기간을 선택하고 위반·상태·시간은 보고서 생성 시점에 저장합니다. 상태별 시간과 막대는 Jira의 **해결시간 SLA clock**을 기준으로 하며, 닫힘·결과 대기 중·자료 요청 중·보류 중은 표시와 비율 계산에서 제외합니다. 실제 경과시간으로 저장된 이전 보고서는 다시 생성해야 SLA 기준 시간이 표시됩니다. 기본 상태 필터는 닫힘·반려됨·보류 중을 제외합니다. **SLA 위반 티켓** 목록에서는 티켓을 한 번만 표시하고 `위반 항목` 컬럼의 배지로 최초응답·해결시간 위반을 구분합니다. 두 SLA를 모두 위반하면 같은 행에 두 배지를 표시하며, 상단 요약 카드로 위반 범위를 선택합니다. 재배포 현황의 월별 완료는 Jira의 **배포 완료 월** 필드 기준입니다.

화면의 팔레트와 3단계 글자 크기(약 16.67·18.67·26.67px), 굵기(400·500·600)는 `frontend/src/presentation/config/designTokens.json`에서 관리합니다. 기존 세 크기에 각각 2pt(약 2.67px)를 더했으며 차트 글자와 Markdown 미리보기 본문에도 적용합니다. PDF의 별도 인쇄 조판과 업로드 원본 서식은 유지하고, 내보내는 차트의 글자는 중앙 토큰을 따릅니다. 헤더 로고는 테마별 투명 PNG만 사용하고 전체 뷰포트의 가운데에 배치합니다. SLA 월별 차트는 `1월`, `2월` 형식으로 표시합니다.

C-Level 기능과 관련 테이블은 제거했습니다. SLA 매일 08시 자동 생성과 Rovo A2A 직접 호출은 현재 구현에 포함하지 않습니다. 보고서 AI는 Gemini 또는 Rovo Automation을 선택할 수 있습니다.

## 보고서 AI 분석

`AI_ENABLED=true`일 때 새 보고서의 저장 대상 집계를 분석합니다. `AI_PROVIDER=gemini`가 기본값이며, `AI_PROVIDER=rovo_automation`은 관리자 설정한 Incoming webhook → Use Rovo → 전용 Jira 이슈의 임시 결과 → 서버 조회 방식으로 연동합니다. 사내 서버는 외부 HTTPS 요청만 보내므로 공개 콜백 주소가 필요하지 않습니다. 보안 뉴스의 Gemini 번역 설정과는 독립적입니다.

분석 입력은 보고 기간·집계 범위·지표·제한된 근거 티켓 키·저장된 JQL을 허용 목록으로 구성하며, 고객명·담당자·이슈 제목·본문은 포함하지 않습니다. Rovo에는 추가 Jira 조회를 맡기지 않고 애플리케이션이 수집·집계한 값을 전달합니다. 결과는 요약·문제점·병목·개선 제안이며 현재 화면 필터가 아닌 보고서 전체 기준입니다. 자동 갱신은 AI를 다시 호출하지 않으며 이전 총평에는 분석 시점 안내를 표시합니다. 분석에 실패해도 수집한 보고서는 저장합니다.

Rovo Automation의 코드 배포와 실제 분석 활성화는 별도입니다. 현재 작업 계정에는 TACEA Automation 생성 권한이 없어 관리자가 규칙과 연결 권한을 설정해야 합니다. 관리자 설정과 합성 데이터 왕복 검증 전에는 `AI_PROVIDER=rovo_automation`, `AI_ENABLED=false`로 운영합니다. [Rovo Automation 관리자 설정](backend/docs/14_rovo_automation.md)에 검증, 활성화 및 임시 결과 정리 절차를 정리했습니다.

## 실행

Docker Engine/Desktop과 Compose v2가 필요합니다. Compose는 PostgreSQL 16, Python 3.11, Node 22 빌드 환경을 사용합니다.

1. `.env.example`을 루트 `.env`로 복사하고 Jira·DB·로그인 설정을 입력합니다. 실제 비밀번호와 토큰은 Git에 저장하지 않습니다.

   기존 관리자 로그인과 함께 Jira OAuth 로그인을 사용할 수 있습니다. 앱 등록과 환경 설정은 [Jira 로그인과 JWT 자동 로그인](backend/docs/11_jira_login.md)을 참고하세요. Jira 세션은 기본 7일 동안 새로고침·재접속 시 복원되며, 앱 등록 전에는 기존 관리자 로그인을 사용합니다.
2. 최초 실행 전 [환경 설정](backend/docs/04_environment_and_config.md)과 기존 DB의 [마이그레이션](backend/docs/03_data_model.md)을 확인합니다.
3. 저장소 루트에서 실행합니다.

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 backend
curl -f http://localhost/api/health
```

기본 접속 주소는 `http://localhost`, `APP_PORT`로 포트를 바꿀 수 있습니다. 백엔드 컨테이너 시작 시 `alembic upgrade head`가 실행됩니다. 현재 migration head는 `0018`입니다. `0016`은 과거 C-Level 데이터를 삭제하므로 기존 DB는 백업 후 업그레이드합니다.

`SCHEDULE_CRON=0 23 * * 5`의 숫자 요일은 APScheduler 기준으로 **토요일**입니다. 금요일 23시를 원하면 `0 23 * * fri`를 설정합니다. [운영 가이드](backend/docs/10_operations.md)에 갱신 종류, 백업, 배포 및 확인 명령을 정리했습니다.

## 검증

백엔드는 Python 3.11과 `backend/requirements.txt` 설치 환경에서 실행합니다. 테스트는 backend 디렉터리를 기준으로 import합니다.

```bash
cd backend
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

프런트엔드는 Node 22와 `package.json`에 지정한 pnpm을 사용합니다.

```bash
cd frontend
pnpm install --frozen-lockfile
node --test tests/*.test.mjs
pnpm build
```

테스트·빌드는 실제 Jira 수집이나 운영 배포 확인을 대신하지 않습니다. 문서만 변경할 때는 링크·경로·명령과 `git diff --check`를 확인합니다. 상세 검증 구분은 [운영 가이드](backend/docs/10_operations.md#검증과-점검)를 참고하세요.

## 문서

- [SLA 현황](backend/docs/15_sla_status.md): SLA 위반 임박 티켓, 잔여 시간·잔여율·상태별 체류시간

- [CVE 취약점 대응·보안 뉴스](backend/docs/13_security_news.md): 취약 버전·해결 버전 표시, 뉴스 한 줄 요약 목록·캐시·호출 제한
- [패키지 인벤토리 CVE 대응](backend/docs/18_cve_inventory.md): 모든 버전 CVE 조회, 위험도 필터, 패키지 식별·수집 상태와 운영 인벤토리 배치

- [화면 사용 가이드](frontend/docs/USER_GUIDE.md)
- [백엔드 문서 인덱스](backend/docs/README.md): API, DB, 설정, SLA·재배포 수집, 운영
- [프런트엔드 문서 인덱스](frontend/docs/README.md): 구조, 상태, 라우팅, 디자인, 내보내기

`_tmp_presentation/`의 날짜가 포함된 자료는 과거 발표 작업 기록이고 현재 제품 사용 설명서가 아닙니다. 글꼴 라이선스와 의존성 manifest는 해당 원본 계약을 유지합니다.
