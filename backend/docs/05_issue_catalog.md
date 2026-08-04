# backend/docs/05_issue_catalog.md

# Issue Catalog — 코드 검수 결과

검수 기준일: 2026-08-05  
검수 범위: `backend/src/` 전체

---

## 🔴 HIGH — 즉시 수정 권고

### [ISS-001] `sites.py` 라우터의 변환 함수 중복

**위치**: `backend/src/presentation/api/v1/sites.py`  
**설명**: `_creds_from_schema`, `_creds_to_schema`, `_contact_from_schema`, `_contact_to_schema`, `_node_to_schema` 등의 변환 함수들이 라우터 파일에 직접 정의되어 있습니다. 이 로직은 Presentation Layer에 속하지 않으며 Application Layer의 Mapper 또는 별도 `site_mapper.py`로 분리해야 합니다.  
**영향**: 테스트 불가, 코드 재사용 불가, 관심사 미분리  
**수정 방향**: `src/application/mappers/site_mapper.py` 생성 및 이전

---

### [ISS-002] `sites.py` `add_node` 엔드포인트의 취약한 응답

**위치**: `backend/src/presentation/api/v1/sites.py` — `add_node()`  
**설명**: `site.nodes[-1]`로 마지막 노드를 반환합니다. 동시 요청 시 잘못된 노드가 반환될 수 있으며, 데이터베이스 순서 보장이 없습니다.  
**수정 방향**: `SiteUseCase.add_node()`가 추가된 노드 객체(id 포함)를 직접 반환하도록 수정

---

### [ISS-003] `access_credentials` 평문 저장

**위치**: `backend/src/infrastructure/persistence/site_models.py`  
**설명**: CLI/Web/DB/VPN 패스워드가 JSONB에 평문으로 저장됩니다.  
**영향**: DB 접근 권한이 있는 누구든 자격증명 열람 가능  
**수정 방향**: 저장 시 AES-256 또는 Fernet 암호화 적용, 또는 HashiCorp Vault 연동 고려

---

## 🟡 MEDIUM — 다음 리팩토링 사이클에서 수정

### [ISS-004] `update_node`, `update_patch_history`, `update_visit_history` 패턴 중복

**위치**: `backend/src/presentation/api/v1/sites.py`  
**설명**: 3개의 서브리소스 업데이트 핸들러가 동일한 패턴(site 조회 → 서브리소스 탐색 → setattr 루프 → site 전체 저장)을 반복합니다.  
**수정 방향**: `SiteUseCase`에 `update_node(site_id, node_id, updates)` 등 전용 메서드 추가

---

### [ISS-005] `JobRunner._notify_events` 메모리 누수 가능성

**위치**: `backend/src/infrastructure/job_runner.py`  
**설명**: `_notify_events` 딕셔너리는 `finally` 블록에서 정리되지만, `save_pending` 이후 `execute_in_background`가 호출되지 않는 비정상 경로에서는 이벤트가 영구적으로 남을 수 있습니다.  
**수정 방향**: TTL 기반 정리 또는 WeakValueDictionary 사용 검토

---

### [ISS-006] `Container.is_valid_credentials` 비교 로직 취약

**위치**: `backend/src/infrastructure/container.py`  
**설명**: 패스워드 비교가 `==` 단순 문자열 비교입니다. `admin_password`가 빈 문자열(`""`)일 때 의도치 않게 로그인이 허용될 수 있습니다.  
**수정 방향**: `admin_password`가 빈 문자열인 경우 로그인 실패 처리 추가

```python
if not password:
    return False
```

---

### [ISS-007] `auth.py`의 `secure=False` 쿠키 설정

**위치**: `backend/src/presentation/api/v1/auth.py` — `_set_refresh_cookie()`  
**설명**: `secure=False`로 설정되어 있어 HTTP 환경에서도 쿠키가 전송됩니다. 운영 환경에서는 HTTPS가 보장되어야 합니다.  
**수정 방향**: `secure=settings.cookie_secure` 형태로 환경변수화

---

### [ISS-008] `trigger.py` SSE `elapsed` 계산 오차

**위치**: `backend/src/presentation/api/v1/trigger.py` — `event_generator()`  
**설명**: `elapsed += _SSE_WAIT_TIMEOUT`으로 누적하는 방식은 실제 대기 시간과 차이가 생깁니다 (잡이 빨리 완료되어 `wait_for_update`가 조기 반환 시). 타임아웃이 의도보다 짧게 작동할 수 있습니다.  
**수정 방향**: `asyncio.get_event_loop().time()` 또는 `time.monotonic()`으로 실제 경과 시간 측정

---

## 🟢 LOW — 품질 개선 사항

### [ISS-009] `Settings.year_start` 프로퍼티 타임존 미고려

**위치**: `backend/src/infrastructure/config/settings.py`  
**설명**: `datetime.date.today()`는 서버 로컬 타임존 기준입니다. KST 서버가 아닌 환경에서 연도가 다를 수 있습니다.  
**수정 방향**: `datetime.datetime.now(ZoneInfo("Asia/Seoul")).year` 사용

---

### [ISS-010] 위젯 컬렉터 `site.nodes[-1]` 패턴 일관성

**위치**: 여러 위젯 컬렉터 파일  
**설명**: 위젯 컬렉터들이 각각 독립적으로 Jira API를 호출합니다. `report_assembler.py`가 병렬 실행하지만, 동일한 JQL을 여러 컬렉터가 중복 호출할 가능성이 있습니다.  
**수정 방향**: 필요 시 공통 이슈 목록 사전 패치 후 컬렉터에 주입하는 방식으로 최적화 가능

---

### [ISS-011] `partner_use_case.py` Jira 클라이언트 직접 접근

**위치**: `backend/src/application/use_cases/partner_use_case.py`  
**설명**: `PartnerUseCase`가 `jira_base_url`, `jira_email`, `jira_api_token`을 직접 받아 내부에서 HTTP 클라이언트를 생성합니다. 이는 `JiraPort` 추상화를 우회하는 패턴입니다.  
**수정 방향**: `JiraPort`에 파트너 조회 메서드 추가 또는 전용 포트 분리

---

## 검수 총평

전체적으로 Clean Architecture 원칙이 잘 지켜지고 있습니다. 레이어 간 의존성 방향이 올바르며, 포트/어댑터 패턴이 일관성 있게 적용되어 있습니다. 위의 이슈들은 기능 결함이 아닌 보안 강화 및 코드 품질 개선 항목이 중심입니다.  

**우선 처리 권고 순서**: ISS-003 (보안) → ISS-001 (아키텍처) → ISS-002 (버그) → ISS-006 (보안)
