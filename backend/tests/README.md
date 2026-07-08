# 테스트 실행 가이드

## 의존성 설치

```bash
cd backend
pip install -r tests/requirements-test.txt
```

## 단위 테스트 (외부 I/O 없음)

```bash
pytest tests/unit/ -v
```

## 통합 테스트 (Docker 필요)

```bash
# testcontainers가 PostgreSQL 컨테이너를 자동 실행합니다
pytest tests/integration/ -v -m integration
```

## 전체 + 커버리지

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

## 테스트 구조

```
tests/
├── conftest.py                              # 공통 픽스체
├── unit/
│   ├── domain/
│   │   ├── test_report_entity.py           # NewReport/Report 불변성
│   │   └── test_widget_serializer.py       # 직렬화/역직렬화 화람테스트
│   └── application/
│       ├── test_generate_report_uc.py      # UseCase Mock 루트
│       └── test_ai_analyzer.py             # 프롬프트 생성 로직
└── integration/
    └── test_report_repository.py           # 실DB 라운드트립
```
