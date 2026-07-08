# Auto Reports 문서 목차

> **Version 1.0** | 2026-07-09

이 폴더는 Auto Reports 프로젝트의 공식 기술 문서를 담고 있습니다.

| 문서 | 설명 |
|---|---|
| [architecture.md](./architecture.md) | 전체 시스템 아키텍처 및 레이어 구조 |
| [widgets.md](./widgets.md) | 위젯 목록, JQL 정의, 데이터 흐름 |
| [api.md](./api.md) | REST API 엔드포인트 레퍼런스 |
| [deployment.md](./deployment.md) | 환경 설정 및 Docker 배포 가이드 |

---

## 프로젝트 개요

Auto Reports는 Jira Service Management 데이터를 자동으로 수집·집계하여
실시간 대시보드로 시각화하는 내부 리포팅 시스템입니다.

- **백엔드**: FastAPI (Python 3.12) + APScheduler + PostgreSQL
- **프론트엔드**: React 18 + TypeScript + Vite + Tailwind CSS
- **배포**: Docker Compose (db / backend / frontend 3-컨테이너 구성)
- **AI 요약**: Google Gemini API (선택적 활성화)
