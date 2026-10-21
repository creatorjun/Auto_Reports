# 보안 뉴스

문서 기준: 2026-10-21.

`/security-news`는 로그인한 사용자가 CVE 취약점, 보안 권고, IT 보안 뉴스를 확인하는 메뉴입니다. 데스크톱 사이드바와 모바일 메뉴에서 열 수 있습니다. 공개 자료 수집은 API 키 없이 동작합니다. `GEMINI_API_KEY`가 설정되어 있으면 제목과 짧은 요약을 한국어로 번역합니다. 외부 AI에는 공개 뉴스의 제목·요약만 보내며 Jira 데이터나 사용자 검색어는 전송하지 않습니다.

## 화면

- 상단 위젯으로 전체 수집 항목·실제 악용 확인·치명적 또는 높은 위험도·보안 권고와 뉴스 목록을 선택합니다. 위젯을 선택하면 검색 조건과 페이지를 초기화하고 해당 집계 범위를 표시하며 정렬은 유지합니다.
- CVE 번호·제품·제목·요약 검색을 제공하며, 위젯 선택 후 검색 조건으로 결과를 더 좁힐 수 있습니다. 수집된 항목 위젯이나 필터 초기화로 전체 목록으로 돌아갑니다.
- 출처·위험도·실제 악용 확인·최근 7일/30일 필터와 최신순/위험도순 정렬을 조합합니다. 검색 결과는 20개씩 표시합니다.
- 상단 집계는 수집된 항목 기준입니다. 같은 CVE가 CISA와 NVD에 각각 포함될 수 있으므로 전 세계 취약점 총계나 고유 CVE 수를 뜻하지 않습니다.
- 실제 악용 확인은 CISA KEV 목록에 등재된 CVE 기준입니다. NVD·권고의 CVE 번호가 KEV와 일치하면 같은 표시를 적용합니다.
- CVSS는 NVD가 제공한 점수와 버전을 표시합니다. 값이 없는 항목은 미평가이며 낮은 위험으로 추정하지 않습니다.
- 기본 화면은 한국어 번역을 표시하고 **원문**으로 전환할 수 있습니다. 전환은 브라우저에서만 처리하며 번역 API를 호출하지 않습니다. 검색은 두 언어를 모두 대상으로 합니다.
- 번역 대기·실패 항목은 원문을 표시하며 저장된 번역은 계속 사용할 수 있습니다. KISA처럼 이미 한국어인 자료는 그대로 사용하고 요약이 없는 항목에는 원문 확인 안내를 표시합니다. 기사 전문은 수집하거나 번역하지 않습니다.
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

첫 목록 요청은 백그라운드 수집을 시작하고 즉시 반환합니다. 화면은 수집 중 2초, 번역 중 5초, 평상시 60초 간격으로 상태를 확인합니다. 서버는 마지막 수집 시작 후 15분이 지난 목록 요청에서 자동 수집을 시작합니다. 화면이 닫혀 있으면 새로운 주기 작업을 시작하지 않으며 이미 시작한 수집·번역은 완료합니다.

**최신 자료 확인**은 전체 사용자에게 공유되는 최소 60초 요청 간격을 적용합니다. 진행 중인 요청은 같은 작업을 공유합니다. NVD는 수동 요청을 포함해 마지막 시도부터 최소 2시간 동안 다시 요청하지 않으며 다른 출처만 갱신할 수 있습니다. 두 제한은 프로세스 메모리에 저장되므로 서버 재시작 시 초기화됩니다.

출처별 작업을 독립적으로 실행합니다. 실패한 출처는 마지막 정상 자료를 유지하고 `stale`로 표시하며, 성공 이력이 없으면 `error`입니다. `refreshed_at`은 전체 수집 시도의 종료 시각으로 모든 출처의 성공을 뜻하지 않습니다. 각 출처의 `last_success_at`을 확인해야 합니다.

원문 수집 캐시는 서버 프로세스 메모리에 있습니다. 재시작 후 첫 방문에서는 원문을 다시 수집하지만 아래 영구 저장소에 있는 번역은 재사용합니다. PostgreSQL 테이블·마이그레이션을 추가하지 않습니다. 현재 단일 backend 프로세스 Compose 운영을 전제로 하며 여러 worker로 확장할 때는 수집 작업과 번역 실행의 조정이 필요합니다.

## 한국어 번역과 API 사용 제한

번역은 수집과 별도의 백그라운드 작업으로 진행되어 뉴스 조회를 막지 않습니다. 제목과 요약을 함께 묶어 자연스러운 한국어로 번역하고 CVE 번호·수치·버전은 보존하도록 요청·검증합니다. CVSS, 출처 URL, 날짜, 제품 등 메타데이터는 AI가 수정하지 않습니다. 반환된 ID와 텍스트 형식이 유효한 결과만 저장하며 실패 항목은 원문을 유지합니다.

성공한 번역은 `reports/security-news-translations.sqlite3`에 영구 보관합니다. Docker에서는 기존 `reports_data` 볼륨의 `/app/reports` 경로이므로 컨테이너 재생성·배포 후에도 남습니다. 캐시 키는 한국어 대상 언어와 원문 제목·요약의 SHA-256입니다.

- 원문 제목·요약이 같으면 출처·기사 ID가 달라도 같은 번역을 사용합니다.
- 새로고침, 페이지 재방문, 서버 재시작, 모델 변경은 기존 번역의 재호출 사유가 아닙니다.
- 원문이 바뀐 항목만 새로 번역합니다. 성공한 번역에는 자동 만료나 개수 제한에 따른 삭제를 적용하지 않습니다.
- 캐시 저장소에 접근할 수 없으면 새 번역 요청을 중단합니다. 저장에 실패한 상태에서 API를 계속 호출하지 않습니다.

기본값은 **한 번에 최대 10개 기사, 요청 간 최소 10초, UTC 날짜별 최대 60회 요청**입니다. 호출 예산을 API 요청 전에 저장하므로 재시작으로 일일 한도를 초기화할 수 없습니다. SDK의 자동 재시도를 끄고 애플리케이션에서 재시도·대기 시간을 관리합니다. 개별 원문의 잘못된 번역·일시적인 서비스 오류는 최대 3회까지만 시도하며 이미 성공한 항목은 이 대상에서 제외됩니다. 할당량 제한은 최소 1시간부터 대기를 늘리고, 인증·크레딧 오류는 24시간 동안 전체 번역 요청을 중지합니다. 이 대기 상태도 저장하고 화면에 안내하며, 계정 오류 때문에 개별 기사의 재시도 횟수를 소진하지 않습니다.

키가 없거나 `SECURITY_NEWS_TRANSLATION_ENABLED=false`이면 AI를 호출하지 않습니다. 이 설정은 보고서의 `AI_ENABLED`와 독립적입니다. [환경 설정](04_environment_and_config.md)의 `SECURITY_NEWS_TRANSLATION_*` 값으로 모델·경로·한도를 조정할 수 있습니다. 설정 변경 후 backend 컨테이너를 재생성해야 합니다. Gemini 계정의 실제 접근 권한과 할당량·크레딧도 필요합니다. 기본 모델은 [Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)입니다.

백업할 때 번역 저장소도 포함해야 합니다. 실행 중인 SQLite 파일은 단순 복사 대신 SQLite backup API로 일관된 사본을 만드세요. 파일이나 `reports_data` 볼륨을 삭제하면 기번역 이력이 사라져 원문을 다시 번역할 수 있습니다. 외부 API 응답 직후 프로세스가 강제로 종료되어 저장하지 못한 요청까지 정확히 한 번 실행되는 것은 보장하지 않습니다.

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
| `translation` | 번역 활성화·진행 여부, 번역 완료·대기 건수와 상태 안내 |

`items`는 `id`, `source_id`, `kind`, `title`, `summary`, `title_ko`, `summary_ko`, `url`, `published_at`, `updated_at`, `cve_ids`, `severity`, `cvss_score`, `cvss_version`, `known_exploited`, `vendor`, `product`, `due_date`를 포함합니다. `title`·`summary`는 원문이고 아직 번역되지 않은 `title_ko`·`summary_ko`는 null입니다. `kind`는 `cve|advisory|news`, `severity`는 `critical|high|medium|low|unknown`입니다. 자료에 없는 점수·날짜·제품은 null입니다.

`translation`은 `enabled`, `translating`, `translated_count`, `pending_count`, `message`를 포함합니다. 원문 수집의 `refreshing`과 번역의 `translating`은 별개이며 번역 중에도 수집 제한이 지난 경우 최신 자료를 확인할 수 있습니다.

`sources`는 `id`, `name`, `homepage`, `kind`, `status`, `count`, `last_success_at`, `error`, `warning`을 포함합니다. `status`는 `ok|stale|error|pending`입니다. 전체 출처 실패도 상태를 설명할 수 있도록 정상 snapshot 응답으로 반환합니다.

60초 이내의 완료된 작업에 다시 수동 요청하면 `429`와 `Retry-After`를 반환합니다. 화면의 대기 시간은 서버가 전달한 `retry_after_seconds`를 응답 수신 시각부터 계산하므로 PC와 서버의 시계 차이에 영향받지 않습니다. 서비스 미구성은 `503`, 인증 실패는 기존 인증 응답을 따릅니다. 정상 및 서비스 오류 응답은 `Cache-Control: no-store`입니다.

## 구현과 운영

```text
backend/src/
  domain/entities/security_news.py
  domain/entities/security_news_translation.py
  application/ports/security_news_port.py
  application/ports/security_news_translation_port.py
  application/services/security_news_translation.py
  application/use_cases/security_news.py
  infrastructure/external/security_news_source.py
  infrastructure/external/gemini_news_translator.py
  infrastructure/persistence/security_news_translation_cache.py
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

Domain은 순수 자료형, Application은 캐시·상태·작업 수명을 관리하고 Infrastructure는 HTTP·JSON·RSS 파싱, Gemini 호출과 SQLite 저장을 담당합니다. 기존 Container와 프런트엔드 ApplicationServices에서 조립합니다. 서버 종료 시 수집·번역 작업을 취소하고 진행 중인 저장을 마친 뒤 HTTP client와 저장소를 닫습니다.

HTTP는 고정된 5개 주소만 호출하며 사용자 URL 입력을 받지 않습니다. TLS 인증을 검증하고 자동 리다이렉트를 따르지 않습니다. 응답은 최대 12MiB, 출처별 전체 수집 시간은 65초로 제한합니다. `defusedxml>=0.7.1`로 DTD·외부 엔터티를 차단하고, HTML 설명은 일반 텍스트로 변환합니다. UI에서 HTML을 직접 렌더링하지 않으며 원문 링크는 HTTP/HTTPS만 허용합니다.

운영 서버에서 위 5개 HTTPS 호스트로 나가는 연결이 필요합니다. 선택적 번역에는 Google Gemini API 연결과 키가 필요하며 SMTP·Jira 권한은 추가하지 않습니다. 공급자 장애나 차단은 출처별 상태에 표시되며, 백엔드 로그에는 출처 ID와 실패 예외 종류를 남깁니다. 번역 오류의 원문 응답이나 API 키는 로그·브라우저 응답에 포함하지 않습니다.

검증은 `backend`에서 `../venv/Scripts/python.exe -m unittest tests.test_security_news tests.test_security_news_source tests.test_security_news_api tests.test_security_news_translation tests.test_gemini_news_translator tests.test_architecture tests.test_container_lifecycle`, `frontend`에서 `pnpm test:security-news`, `pnpm test:architecture`, `pnpm build`를 실행합니다. 번역 테스트는 외부 API 없이 영구 캐시 재사용, 중복 제거, 내용 변경, 일일 한도, 공급자 오류, 종료 처리를 검증합니다. 실제 수집·번역 상태는 운영 로그인 후 메뉴에서 별도로 확인해야 하며 단위 테스트 성공만으로 외부 서비스의 접근 권한이나 크레딧을 보증하지 않습니다.
