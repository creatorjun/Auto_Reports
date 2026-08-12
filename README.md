# Auto Reports Workspace

Jira 데이터를 수집해 주간 보고서, 파트너 현황, 고객사 사이트 정보와 파일 저장소를 제공하는 사내 통합 워크스페이스입니다. FastAPI 백엔드와 React 대시보드를 하나의 Docker Compose 스택으로 운영합니다.

## 프로젝트 구조

```text
Auto_Reports/
├── backend/
│   ├── src/
│   │   ├── domain/          핵심 엔티티와 값 객체
│   │   ├── application/     유스케이스와 포트
│   │   ├── infrastructure/  DB, Jira, 메일, 파일, 스케줄러 어댑터
│   │   ├── presentation/    FastAPI 라우터, 스키마, 매퍼
│   │   ├── bootstrap/       의존성 조립
│   │   └── main.py          프로세스 Composition Root
│   ├── tests/               아키텍처와 핵심 동시성 회귀 테스트
│   └── docs/
├── frontend/
│   ├── src/
│   │   ├── domain/          프레임워크 독립 모델
│   │   ├── application/     게이트웨이 계약과 애플리케이션 오류
│   │   ├── infrastructure/  axios API 어댑터
│   │   ├── presentation/    React UI, 훅, 상태, 컨텍스트
│   │   ├── app/             라우터와 앱 셸
│   │   └── main.tsx         브라우저 Composition Root
│   ├── tests/               의존 방향 아키텍처 테스트
│   └── docs/
├── docker-compose.yml
└── Makefile
```

의존성은 안쪽을 향합니다. Domain은 어떤 프레임워크도 알지 못하고, Application은 Domain과 자체 포트만 사용합니다. Infrastructure와 Presentation은 Application 포트에 의존하며, 실제 구현 연결은 각 실행 진입점에서만 수행합니다.

## 실행

루트에 `.env`를 준비한 뒤 전체 스택을 실행합니다.

```bash
docker compose up -d --build
docker compose logs -f backend
```

기본 접속 주소는 `http://localhost`이고 백엔드 상태 확인은 `GET /api/health`입니다. 환경 변수는 [backend/docs/04_environment_and_config.md](backend/docs/04_environment_and_config.md)를 참고하세요.

## 로컬 검증

```bash
cd backend
python -m unittest discover -s tests -v
python -m compileall -q src tests

cd ../frontend
pnpm install --frozen-lockfile
pnpm test:architecture
pnpm build
```

백엔드 문서는 [backend/docs/README.md](backend/docs/README.md), 프런트엔드 문서는 [frontend/docs/README.md](frontend/docs/README.md)에서 시작합니다.
