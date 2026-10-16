# SecuLayer · Auto Reports

Jira 데이터를 수집해 대시보드, 연간 보고서, SLA 현황, 재배포 현황과 전체 이슈를 제공하는 사내 업무 포털입니다. React 프런트엔드, FastAPI 백엔드, PostgreSQL을 사용합니다.

문서 기준: 2026-10-16. 패키지와 API의 `1.0.0`은 고정 메타데이터이므로 기능 버전 확인에는 Git 커밋을 사용합니다. 문서는 현재 소스의 계약을 설명하며 특정 서버의 실시간 배포 상태를 보증하지 않습니다.

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
| 대시보드 | 최신 일반 보고서, 주·월·연 및 기준일 선택 생성, 필터와 PDF·Excel |
| 전체 이슈 | 프로젝트 전체 이슈 동기화, 검색·필터, 전체 검색 결과 내보내기 |
| 집중 관리 항목 → SLA 현황 | 전체·최초응답·해결·동시 위반 요약, 현재 상태 분포·생성 추이, 상세 티켓 |
| 집중 관리 항목 → 재배포 현황 | 2026-01-01 이후 완료 재배포와 현재 진행 중 재배포, 원인·월별 선택 |
| 연간 보고서 | 2024·2025·2026 전용 보고서, 연도 비교와 재배포 품질 지표 |
| 파트너 관리 | 조직·멤버별 이슈 |
| 사이트 관리 | 사이트, 장비, 접속 정보, 패치·방문 이력 |
| 장기 이슈 | 최신 일반 보고서의 최근 이슈 집합과 Jira 활동·댓글 |
| 파일 보관함 | 파일·폴더 관리, 미리보기, 업로드·다운로드 |

`집중 관리 항목`과 `연간 보고서`는 해당 메뉴 버튼을 가리킬 때 펼쳐지고 메뉴 영역을 벗어나면 접힙니다. 모바일은 클릭으로 조작합니다. **보고서 히스토리**는 대메뉴가 아닌 대시보드와 SLA 현황의 버튼으로 엽니다. **감사로그**는 `SUPERADMIN`에게만 추가 표시됩니다.

| 보고서 | 생성·갱신 | 저장 계약 |
|---|---|---|
| 일반 대시보드 | 기간·기준일로 수동 생성, `SCHEDULE_CRON` 정기 생성; 최신 일반 보고서는 기본 5분 주기 갱신 | `reports`, `scope=standard`; 생성 시 새 ID, 갱신은 같은 ID |
| 연간 전용 | 연도별 생성; 백엔드는 현재 연도 저장본을 기본 5분 주기 갱신 | `reports`, `scope=annual`; 최신 일반 보고서와 분리 |
| SLA 현황 | 주·월·연 및 기준일로 수동 생성 | `sla_violation_reports`; 성공할 때 새 불변 스냅샷, 히스토리 자동 저장 |
| 재배포 현황 | 매일 08:00 KST, 시작 시 누락 보충, 지금 갱신 | `redeployment_reports`; KST 날짜별 한 건, 당일 갱신은 대체 |

대시보드 주간은 선택 날짜가 속한 주의 월요일~선택 날짜, 월간·연간은 해당 달·연도 전체입니다. 예를 들어 기준일이 2026-10-09이면 주간은 10월 5일~9일, 월간은 10월 1일~31일, 연간은 1월 1일~12월 31일이며 KST 기준 종료일 전체를 포함합니다. SLA 현황의 주간은 기존 월요일~일요일을 유지합니다. 대시보드에서 연간을 선택해도 일반 보고서이며 별도 연간 메뉴의 보고서와 구분합니다. 날짜 선택만으로 현재 표시 중인 보고서는 바뀌지 않습니다.

SLA 현황은 **티켓 생성일**로 기간을 선택하고 위반·상태·체류시간은 보고서 생성 시점에 저장합니다. 기본 상태 필터는 닫힘·반려됨·보류 중을 제외합니다. **SLA 위반 티켓** 목록에서는 티켓을 한 번만 표시하고 `위반 항목` 컬럼의 배지로 최초응답·해결시간 위반을 구분합니다. 두 SLA를 모두 위반하면 같은 행에 두 배지를 표시하며, 상단 요약 카드로 위반 범위를 선택합니다. 재배포 현황의 월별 완료는 Jira의 **배포 완료 월** 필드 기준입니다.

화면의 팔레트와 3단계 글자 크기(약 16.67·18.67·26.67px), 굵기(400·500·600)는 `frontend/src/presentation/config/designTokens.json`에서 관리합니다. 기존 세 크기에 각각 2pt(약 2.67px)를 더했으며 차트 글자와 Markdown 미리보기 본문에도 적용합니다. PDF의 별도 인쇄 조판과 업로드 원본 서식은 유지하고, 내보내는 차트의 글자는 중앙 토큰을 따릅니다. 헤더 로고는 테마별 투명 PNG만 사용하고 전체 뷰포트의 가운데에 배치합니다. SLA 월별 차트는 `1월`, `2월` 형식으로 표시합니다.

C-Level 기능과 관련 테이블은 제거했습니다. Rovo/A2A 분석과 SLA 매일 08시 자동 생성은 현재 구현에 포함하지 않습니다. 일반 보고서의 선택적 Gemini 분석은 별도 기능입니다.

## 실행

Docker Engine/Desktop과 Compose v2가 필요합니다. Compose는 PostgreSQL 16, Python 3.11, Node 22 빌드 환경을 사용합니다.

1. `.env.example`을 루트 `.env`로 복사하고 Jira·DB·로그인 설정을 입력합니다. 실제 비밀번호와 토큰은 Git에 저장하지 않습니다.
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

- [화면 사용 가이드](frontend/docs/USER_GUIDE.md)
- [백엔드 문서 인덱스](backend/docs/README.md): API, DB, 설정, SLA·재배포 수집, 운영
- [프런트엔드 문서 인덱스](frontend/docs/README.md): 구조, 상태, 라우팅, 디자인, 내보내기

`_tmp_presentation/`의 날짜가 포함된 자료는 과거 발표 작업 기록이고 현재 제품 사용 설명서가 아닙니다. 글꼴 라이선스와 의존성 manifest는 해당 원본 계약을 유지합니다.
