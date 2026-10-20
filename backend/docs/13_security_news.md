# 보안 뉴스

문서 기준: 2026-10-20.

`/security-news`는 로그인한 사용자가 CVE 취약점, 보안 권고, IT 보안 뉴스를 확인하는 메뉴입니다. 데스크톱 사이드바와 모바일 메뉴에서 열 수 있습니다. API 키·유료 계정·추가 환경 변수 없이 서버에서 공개 자료를 수집하며, Jira 데이터나 사용자 검색어를 외부 출처로 전송하지 않습니다.

## 화면

- 전체·CVE 취약점·보안 권고·보안 뉴스 탭, CVE 번호·제품·제목·요약 검색을 제공합니다.
- 출처·위험도·실제 악용 확인·최근 7일/30일 필터와 최신순/위험도순 정렬을 조합합니다. 검색 결과는 20개씩 표시합니다.
- 상단 집계는 수집된 항목 기준입니다. 같은 CVE가 CISA와 NVD에 각각 포함될 수 있으므로 전 세계 취약점 총계나 고유 CVE 수를 뜻하지 않습니다.
- 실제 악용 확인은 CISA KEV 목록에 등재된 CVE 기준입니다. NVD·권고의 CVE 번호가 KEV와 일치하면 같은 표시를 적용합니다.
- CVSS는 NVD가 제공한 점수와 버전을 표시합니다. 값이 없는 항목은 미평가이며 낮은 위험으로 추정하지 않습니다.
- 원문 제목·짧은 요약과 원문 링크를 제공합니다. 자동 번역이나 기사 전문 재배포는 하지 않으며 KISA처럼 요약이 없는 항목에는 원문 확인 안내를 표시합니다.
- 날짜는 KST로 표시합니다. CISA 날짜는 CVE 최초 공개일이 아닌 KEV 등록일이고, 조치 기한은 미국 연방기관 대상 기한입니다. 기간 필터는 게시/등록일, 없으면 수정일을 사용합니다.
- 수집 출처를 펼치면 출처별 정상·이전 자료 표시·수집 실패·수집 대기, 보관 건수, 마지막 성공 시각과 수집 범위를 확인합니다.

## 공개 소스와 범위

| 출처 | 주소 | 수집 범위 |
|---|---|---|
| CISA KEV | [공개 JSON](https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json) | 전체 KEV 번호로 악용 여부 확인, 화면에는 최근 등재 최대 300건 |
| NVD | [CVE API](https://services.nvd.nist.gov/rest/json/cves/2.0) | 최근 7일 공개 CVE 중 최신 최대 200건, 거부된 CVE 제외 |
| KISA 보호나라 | [보안공지 RSS](https://www.boho.or.kr/kr/rss.do?bbsId=B0000133) | RSS가 제공하는 최신 보안공지 |
| Cisco PSIRT | [보안 권고 RSS](https://sec.cloudapps.cisco.com/security/center/psirtrss20/CiscoSecurityAdvisory.xml) | RSS가 제공하는 최신 권고 |
| Google Security | [보안 뉴스 RSS](https://blog.google/security/rss/) | 공식 Security 블로그의 최신 뉴스 |

RSS는 출처별 최대 100건을 보관하며 실제 제공 개수는 출처에 따라 다릅니다. NVD는 기본 응답이 오래된 순이므로 먼저 동일한 7일 구간의 전체 건수를 조회하고 6초 이상 지난 뒤 마지막 200건을 조회합니다. 범위와 건수를 제한하는 초안으로, 전체 CVE 데이터베이스 검색이나 사내 장비의 취약점 진단 기능은 아닙니다.

출처 정책 참고: [NVD 개발자 안내](https://nvd.nist.gov/developers/start-here), [KISA RSS 안내](https://www.boho.or.kr/kr/subPage.do?menuNo=205121), [Cisco RSS 안내](https://sec.cloudapps.cisco.com/security/center/rss.x?i=44), [Google Security](https://blog.google/security/), [CISA KEV CC0 라이선스](https://github.com/cisagov/kev-data/blob/develop/LICENSE).

## 수집·캐시 계약

첫 목록 요청은 백그라운드 수집을 시작하고 즉시 반환합니다. 화면은 수집 중 2초, 평상시 60초 간격으로 상태를 확인합니다. 서버는 마지막 수집 시작 후 15분이 지난 목록 요청에서 자동 수집을 시작합니다. 화면이 닫혀 있으면 이 기능만을 위한 별도 예약 작업은 실행하지 않습니다.

**최신 자료 확인**은 전체 사용자에게 공유되는 최소 60초 요청 간격을 적용합니다. 진행 중인 요청은 같은 작업을 공유합니다. NVD는 수동 요청을 포함해 마지막 시도부터 최소 2시간 동안 다시 요청하지 않으며 다른 출처만 갱신할 수 있습니다. 두 제한은 프로세스 메모리에 저장되므로 서버 재시작 시 초기화됩니다.

출처별 작업을 독립적으로 실행합니다. 실패한 출처는 마지막 정상 자료를 유지하고 `stale`로 표시하며, 성공 이력이 없으면 `error`입니다. `refreshed_at`은 전체 수집 시도의 종료 시각으로 모든 출처의 성공을 뜻하지 않습니다. 각 출처의 `last_success_at`을 확인해야 합니다.

캐시는 서버 프로세스 메모리에 있고 DB 테이블·마이그레이션을 추가하지 않습니다. 재시작 후 첫 방문에서는 다시 수집합니다. 여러 backend worker로 확장하면 작업·제한이 공유되지 않으므로 현재 단일 프로세스 Compose 운영을 전제로 합니다.

## API

기본 경로는 `/api/v1`이며 기존 `require_auth`를 적용합니다. `LOGIN=false`인 개발 환경은 기존 정책에 따라 guest를 허용합니다.

| 요청 | 응답 |
|---|---|
| `GET /security-news` | 마지막 캐시와 출처 상태, 필요하면 수집 시작 |
| `POST /security-news/refresh` | 같은 응답 형식으로 수집 시작 또는 진행 중 작업 공유 |

성공 응답 필드:

| 필드 | 의미 |
|---|---|
| `items` | 출처별 보안 항목, 최신순 |
| `sources` | 출처 정보·상태·건수·마지막 성공·오류·범위 안내 |
| `initialized` | 최초 전체 수집 시도가 끝났는지 여부 |
| `refreshing` | 현재 수집 중인지 여부 |
| `refreshed_at` | 마지막 전체 수집 시도 종료 시각 또는 null |
| `next_refresh_at` | 다음 수동 갱신을 요청할 수 있는 가장 이른 시각 또는 null |
| `retry_after_seconds` | 응답 시점의 수동 갱신 대기 초, 0이면 요청 가능 |
| `refresh_interval_seconds` | 목록 요청에서 자동 수집을 시작하는 기준 간격, 900초 |

`items`는 `id`, `source_id`, `kind`, `title`, `summary`, `url`, `published_at`, `updated_at`, `cve_ids`, `severity`, `cvss_score`, `cvss_version`, `known_exploited`, `vendor`, `product`, `due_date`를 포함합니다. `kind`는 `cve|advisory|news`, `severity`는 `critical|high|medium|low|unknown`입니다. 자료에 없는 점수·날짜·제품은 null입니다.

`sources`는 `id`, `name`, `homepage`, `kind`, `status`, `count`, `last_success_at`, `error`, `warning`을 포함합니다. `status`는 `ok|stale|error|pending`입니다. 전체 출처 실패도 상태를 설명할 수 있도록 정상 snapshot 응답으로 반환합니다.

60초 이내의 완료된 작업에 다시 수동 요청하면 `429`와 `Retry-After`를 반환합니다. 화면의 대기 시간은 서버가 전달한 `retry_after_seconds`를 응답 수신 시각부터 계산하므로 PC와 서버의 시계 차이에 영향받지 않습니다. 서비스 미구성은 `503`, 인증 실패는 기존 인증 응답을 따릅니다. 정상 및 서비스 오류 응답은 `Cache-Control: no-store`입니다.

## 구현과 운영

```text
backend/src/
  domain/entities/security_news.py
  application/ports/security_news_port.py
  application/use_cases/security_news.py
  infrastructure/external/security_news_source.py
  presentation/api/v1/security_news.py
  presentation/schemas/security_news.py
frontend/src/
  domain/SecurityNews.ts
  application/services/securityNews.ts
  infrastructure/api/securityNewsApi.ts
  presentation/hooks/useSecurityNews.ts
  presentation/components/security/
  presentation/pages/SecurityNewsPage.tsx
```

Domain은 순수 자료형, Application은 캐시·상태·작업 수명을 관리하고 Infrastructure는 HTTP·JSON·RSS 파싱을 담당합니다. 기존 Container와 프런트엔드 ApplicationServices에서 조립합니다. 서버 종료 시 수집 작업을 취소하고 완료를 기다린 뒤 HTTP client를 닫습니다.

HTTP는 고정된 5개 주소만 호출하며 사용자 URL 입력을 받지 않습니다. TLS 인증을 검증하고 자동 리다이렉트를 따르지 않습니다. 응답은 최대 12MiB, 출처별 전체 수집 시간은 65초로 제한합니다. `defusedxml>=0.7.1`로 DTD·외부 엔터티를 차단하고, HTML 설명은 일반 텍스트로 변환합니다. UI에서 HTML을 직접 렌더링하지 않으며 원문 링크는 HTTP/HTTPS만 허용합니다.

운영 서버에서 위 5개 HTTPS 호스트로 나가는 연결이 필요합니다. 별도 API 키·SMTP·Jira 권한은 추가하지 않습니다. 공급자 장애나 차단은 출처별 상태에 표시되며, 백엔드 로그에는 출처 ID와 실패 예외 종류를 남깁니다.

검증은 `backend`에서 `../venv/Scripts/python.exe -m unittest tests.test_security_news tests.test_security_news_source tests.test_security_news_api tests.test_architecture tests.test_container_lifecycle`, `frontend`에서 `pnpm test:security-news`, `pnpm test:architecture`, `pnpm build`를 실행합니다. 실제 수집 검증은 운영 로그인 후 메뉴의 출처별 상태를 확인합니다. 단위 테스트 성공만으로 외부 피드 접근 성공을 보증하지 않습니다.
