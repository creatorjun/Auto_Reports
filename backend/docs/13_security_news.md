# CVE 취약점 대응·보안 뉴스

문서 기준: 2026-10-22.

로그인한 사용자는 **CVE 취약점 대응**(`/cve-response`)에서 NVD와 CISA KEV 취약점을 함께 확인하고, **보안 뉴스**(`/security-news`)에서 보안 권고와 IT 보안 뉴스를 확인합니다. 데스크톱 사이드바와 모바일 메뉴 모두 CVE 취약점 대응이 보안 뉴스 바로 위에 있습니다. 공개 자료 수집은 API 키 없이 동작합니다. `GEMINI_API_KEY`가 설정되어 있으면 보안 권고·뉴스의 핵심을 한국어 한 문장으로 요약하며 CVE 항목은 AI 처리에서 제외합니다. 외부 AI에는 공개 뉴스의 제목·짧은 설명만 보내며 Jira 데이터나 사용자 검색어는 전송하지 않습니다.

## 화면

- CVE 취약점 대응은 `kind=cve`인 NVD·CISA KEV 자료를 제품·버전 대응마다 한 행으로 표시합니다. CVE, 위험도·CVSS, 소프트웨어, 영향 버전, 해결 버전, 판단 근거, 실제 악용, 출처, 등록·공개일, 원문을 별도 컬럼으로 제공하며 긴 설명이나 번역 전환은 표시하지 않습니다. 판단 근거를 선택하면 해당 출처를 열고, 좁은 화면에서는 CVE 컬럼을 고정하고 표 안에서 가로로 이동합니다.
- 보안 뉴스는 `kind=advisory|news`인 자료를 한 행씩 표시합니다. 유형, 한 줄 요약, 위험도, 관련 CVE, 실제 악용, 출처, 게시일, 원문을 별도 컬럼으로 제공합니다. 긴 문구는 한 줄로 줄여 표시하고 마우스를 올리면 전체 문구를 확인할 수 있습니다. 좁은 화면에서는 표를 가로로 이동합니다. CVE 번호를 언급한 보안 권고와 기사는 보안 뉴스에 남습니다.
- 상단 위젯은 현재 메뉴의 자료만 집계합니다. 위젯을 선택하면 검색 조건과 페이지를 초기화하고 해당 집계 범위를 표시하며 정렬은 유지합니다.
- CVE 번호·제품·버전·제목·요약과 수집된 NVD·KEV 원문 설명을 검색합니다. KEV 항목은 연결된 NVD 설명도 포함합니다. 링크된 외부 페이지 전체를 검색하는 기능은 아닙니다. 위젯 선택 후 검색 조건으로 결과를 더 좁힐 수 있으며 수집된 항목 위젯이나 필터 초기화로 현재 메뉴의 전체 목록으로 돌아갑니다.
- 출처·위험도·실제 악용 확인·최근 7일/30일 필터와 최신순/위험도순 정렬을 조합합니다. CVE 화면의 **제품 확인 필요 숨기기**는 제품을 확인할 수 없는 행만 제외합니다. 소프트웨어·영향 버전·해결 버전 컬럼이나 정렬 선택으로 오름차순/내림차순을 전환할 수 있으며 버전의 숫자를 비교합니다. 미확인 값은 양방향 모두 뒤에 표시합니다.
- CVE 검색 결과와 페이지는 제품·버전 행 기준으로 20행씩 표시하고 상단 위젯은 CVE 항목 수를 유지합니다. 보안 뉴스는 기사 기준으로 20개씩 표시합니다.
- 상단 집계는 수집된 항목 기준입니다. 같은 CVE가 CISA와 NVD에 각각 포함될 수 있으므로 전 세계 취약점 총계나 고유 CVE 수를 뜻하지 않습니다.
- 실제 악용 확인은 CISA KEV 목록에 등재된 CVE 기준입니다. NVD·권고의 CVE 번호가 KEV와 일치하면 같은 표시를 적용합니다.
- CVSS는 NVD가 제공한 점수와 버전을 표시합니다. 값이 없는 항목은 미평가이며 낮은 위험으로 추정하지 않습니다.
- 보안 뉴스는 기본으로 **한 줄 요약**을 표시하고 **원문 제목**으로 전환할 수 있습니다. 전환은 브라우저에서만 처리하며 AI를 호출하지 않습니다. 검색은 원문과 한국어 요약을 모두 대상으로 합니다.
- AI 요약은 최대 180자의 한국어 한 문장입니다. 요약 대기·실패 항목에는 원문 제목을 표시하며 저장된 새 요약은 계속 사용할 수 있습니다. KISA처럼 이미 한국어인 자료는 AI 처리 없이 원문 제목을 사용합니다. 기사 전문은 수집하거나 번역하지 않습니다.
- 날짜는 KST로 표시합니다. CISA 날짜는 CVE 최초 공개일이 아닌 KEV 등록일이고, 조치 기한은 미국 연방기관 대상 기한입니다. 기간 필터는 게시/등록일, 없으면 수정일을 사용합니다.
- 수집 출처를 펼치면 출처별 정상·이전 자료 표시·수집 실패·수집 대기, 보관 건수, 마지막 성공 시각과 수집 범위를 확인합니다.

버전 정보는 NVD의 CPE 영향 범위와 출처 설명에 명시된 제품·해결 버전에서 추출하며 AI를 호출하지 않습니다. 영향 버전의 포함·제외 조건을 유지하고 판단 근거를 구분합니다.

- **제조사 확인**: 제품과 연결된 명시적 수정 버전이며, NVD 등록 주체가 확인된 제조사이고 같은 주체가 제공한 제조사 도메인의 HTTPS `Vendor Advisory` 참조가 있습니다. 제조사가 NVD에 제공한 설명과 공지 출처를 확인하는 방식이며 공지 본문을 별도로 수집하지 않습니다. 현재 Apache·Cisco·Microsoft·Mozilla·Oracle·PHP·Red Hat의 등록 도메인과 제품 공급자 이름을 검증합니다.
- **NVD 영향 범위**: 같은 CVE 안에서 동일 CPE 제품 유형·공급자·제품의 모든 영향 범위를 비교합니다. 숫자 `major.minor` 계열의 다른 범위까지 벗어나는 제외 상한이 있을 때 `1.6.20 이상 (1.6 계열)`처럼 표시합니다. `< 1.6.20`과 `< 1.6.30`이 함께 있으면 1.6.30을 기준으로 삼으며, 1.6.30 이후에도 영향을 받는 상한 없는 범위가 있으면 제시하지 않습니다. 플랫폼 조건은 충돌을 놓치지 않도록 함께 비교합니다.
- **출처 수정 명시**: 원문에 수정 버전이 명시되어 있으나 위 제조사 출처 조건을 확인하지 못한 경우입니다. 이전 저장본에 근거가 없으면 **근거 확인 필요**로 표시합니다.

포함 상한(`<=`)에 패치 번호를 더하거나 두 자리 버전·사전 배포 버전·불완전한 조건에서 버전을 만들어내지 않습니다. NVD 기준은 해당 CVE와 제품·버전 계열에만 적용하며 다른 CVE, 다른 계열, 설치 환경이나 공급사의 백포트 적용 여부를 보증하지 않습니다. 제품과 버전을 연결할 수 없거나 영향 범위가 충돌하면 **버전 확인 필요** 또는 **해결 버전 미확인**으로 남깁니다.

CISA KEV도 CVE 번호로 NVD 상세 정보를 조회해 버전·판단 근거·CVSS를 보완합니다. KEV 등록일·조치 기한·실제 악용 여부는 유지하며, 같은 제품의 정보가 있으면 해당 제품의 버전을 우선 표시합니다. 명시적 영향·해결 버전 목록은 제품명과 숫자 major.minor 계열이 일치하는 경우에 연결합니다. 예를 들어 CVE-2026-34486은 `11.0.20 → 11.0.21`, `10.1.53 → 10.1.54`, `9.0.116 → 9.0.117`로 표시합니다. 목록 위치나 다른 제품의 버전으로 짝을 추정하지 않습니다.

## 공개 소스와 범위

| 출처 | 주소 | 수집 범위 |
|---|---|---|
| CISA KEV | [공개 JSON](https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json) | 전체 KEV 번호로 악용 여부 확인, 최근 등재 최대 300건을 NVD 상세 정보로 보완 |
| NVD | [CVE API](https://services.nvd.nist.gov/rest/json/cves/2.0) | 최근 7일 공개 CVE 중 최신 최대 200건, 거부된 CVE 제외 |
| KISA 보호나라 | [보안공지 RSS](https://www.boho.or.kr/kr/rss.do?bbsId=B0000133) | RSS가 제공하는 최신 보안공지 |
| Cisco PSIRT | [보안 권고 RSS](https://sec.cloudapps.cisco.com/security/center/psirtrss20/CiscoSecurityAdvisory.xml) | RSS가 제공하는 최신 권고 |

RSS는 출처별 최대 100건을 보관하며 실제 제공 개수는 출처에 따라 다릅니다. NVD는 기본 응답이 오래된 순이므로 먼저 동일한 7일 구간의 전체 건수를 조회하고 6초 이상 지난 뒤 마지막 200건을 조회합니다. KEV 상세 조회는 공개일 제한 없이 `cveIds`에 최대 100개씩 묶어 최대 3회 요청합니다. 최근 NVD 수집과 KEV 보완 조회는 하나의 요청 간격 제어를 공유하며 각 NVD 응답 종료 후 최소 6초 뒤 다음 요청을 보냅니다. 각각 최대 180초 안에 완료하지 못하면 해당 출처의 이전 정상 저장본을 유지합니다. 범위와 건수를 제한하므로, 전체 CVE 데이터베이스 검색이나 사내 장비의 취약점 진단 기능은 아닙니다.

Google Security는 수집 대상에서 제거했습니다. 이전 저장본에 남은 해당 출처·항목도 목록·집계·번역 대상에서 제외합니다. 한국어로 제공된 원문은 번역 대상에서 제외합니다.

출처 정책 참고: [NVD 개발자 안내](https://nvd.nist.gov/developers/start-here), [KISA RSS 안내](https://www.boho.or.kr/kr/subPage.do?menuNo=205121), [Cisco RSS 안내](https://sec.cloudapps.cisco.com/security/center/rss.x?i=44), [CISA KEV CC0 라이선스](https://github.com/cisagov/kev-data/blob/develop/LICENSE).

## 수집·캐시 계약

자동 수집은 서버 스케줄러가 매일 **08:00 KST**에 한 번 실행합니다. 페이지 방문·주기 조회·서버 시작은 수집을 시작하지 않습니다. 서버가 꺼져 있던 시간의 수집을 부팅 때 소급 실행하지 않습니다. 저장본이 전혀 없으면 빈 목록을 표시하고 **최신 자료 확인** 또는 다음 정기 수집으로 첫 자료를 가져옵니다.

화면은 수집 중 2초, AI 요약 중 5초, 평상시 60초 간격으로 저장 결과와 상태만 조회합니다. 목록 GET은 외부 뉴스 수집이나 새 AI 작업을 시작하지 않습니다. 페이지가 닫혀 있어도 정기 수집은 실행되고 이미 시작한 수집·요약은 완료합니다.

두 메뉴의 **최신 자료 확인**은 같은 수집 작업을 요청하며 전체 사용자에게 공유되는 최소 60초 요청 간격을 적용합니다. 진행 중인 요청은 같은 작업을 공유합니다. NVD와 CISA KEV는 수동 요청을 포함해 각각 마지막 시도부터 최소 2시간 동안 다시 요청하지 않으며 다른 출처만 갱신할 수 있습니다. 시도 시각과 당일 자동 수집 기록은 저장해 재시작 후에도 중복 실행을 방지합니다.

출처별 작업을 독립적으로 실행합니다. 실패한 출처는 마지막 정상 자료를 유지하고 `stale`로 표시하며, 성공 이력이 없으면 `error`입니다. `refreshed_at`은 전체 수집 시도의 종료 시각으로 모든 출처의 성공을 뜻하지 않습니다. 각 출처의 `last_success_at`을 확인해야 합니다.

원문과 출처 상태를 `reports/security-news-snapshot.sqlite3`에 저장하며 재시작 후 마지막 결과를 복원합니다. `SECURITY_NEWS_SNAPSHOT_PATH`로 경로를 변경할 수 있고 Compose에서는 기존 `/app/reports` 볼륨에 저장합니다. 아래 번역 저장소도 계속 재사용합니다. PostgreSQL 테이블·마이그레이션을 추가하지 않습니다. 현재 단일 backend 프로세스 Compose 운영을 전제로 하며 여러 worker로 확장할 때는 수집 작업과 번역 실행의 조정이 필요합니다.

구조화된 버전 정보가 없는 이전 저장본도 복원합니다. KEV 보완 정보나 전체 원문 설명이 없는 이전 저장본은 다음 정상 수동·예약 수집에서 한 번 보완할 수 있도록 출처 수집 버전을 비교합니다. 페이지 GET·서버 시작은 여전히 수집을 시작하지 않으며 60초 수동 제한도 유지합니다. 보완 시도 버전을 요청 전에 저장하므로 실패·취소 후 재시작해도 2시간 제한이 유지됩니다. NVD 상세 응답의 CVE 번호·건수·페이지 완전성을 검증하며, 요청 실패 시 부분 결과로 정상 저장본을 덮어쓰지 않습니다. NVD가 정상 응답했으나 해당 CVE를 제공하지 않으면 KEV 원문을 유지하고 출처 안내에 누락 건수를 표시합니다.

## 한국어 한 줄 요약과 API 사용 제한

AI 요약은 보안 권고·뉴스(`kind=advisory|news`)에만 적용하며 수집과 별도의 백그라운드 작업으로 진행되어 뉴스 조회를 막지 않습니다. CVE·Google Security·이미 한국어인 자료는 AI 요청에서 제외합니다. 원문 제목과 짧은 설명을 함께 입력해 제품·취약점·영향·조치 중 핵심을 최대 180자의 한국어 한 문장으로 압축합니다. 세부 정보는 생략할 수 있지만 새 CVE 번호·수치·버전을 만들어서는 안 됩니다. 반환된 ID, 한 줄 형식, 길이, 한국어 포함 여부와 원문에 없는 CVE·숫자 토큰을 검증하고 유효한 결과만 저장합니다. CVSS, 출처 URL, 날짜, 제품과 버전 대응 정보 등 메타데이터는 AI가 수정하지 않습니다. 실패 항목은 원문 제목을 유지합니다.

성공한 요약은 기존 `reports/security-news-translations.sqlite3`에 영구 보관합니다. Docker에서는 기존 `reports_data` 볼륨의 `/app/reports` 경로이므로 컨테이너 재생성·배포 후에도 남습니다. 캐시 키는 작업 버전 `ko-brief-v1`과 원문 제목·설명의 SHA-256입니다. 이전 전체 번역은 삭제하지 않으며 새 요약으로 재사용하지 않습니다. 기존 기사도 다음 정상 수동·정기 수집에서 새 요약을 생성할 수 있으며 기존 일일 요청 예산과 전체 대기 상태는 유지합니다. SQLite 테이블 변경이나 PostgreSQL 마이그레이션은 없습니다.

- 같은 작업 버전에서 원문 제목·설명이 같으면 출처·기사 ID가 달라도 같은 요약을 사용합니다.
- 새로고침, 페이지 재방문, 서버 재시작, 모델 변경은 저장된 요약의 재호출 사유가 아닙니다.
- 새 요약이 없는 원문만 처리합니다. 성공한 요약에는 자동 만료나 개수 제한에 따른 삭제를 적용하지 않습니다.
- 캐시 저장소에 접근할 수 없으면 새 요약 요청을 중단합니다. 저장에 실패한 상태에서 API를 계속 호출하지 않습니다.

기본값은 **한 번에 최대 10개 기사, 요청 간 최소 10초, UTC 날짜별 최대 60회 요청**입니다. 호출 예산을 API 요청 전에 저장하므로 재시작으로 일일 한도를 초기화할 수 없습니다. SDK의 자동 재시도를 끄고 애플리케이션에서 재시도·대기 시간을 관리합니다. 개별 원문의 잘못된 요약·일시적인 서비스 오류는 최대 3회까지만 시도하며 이미 성공한 항목은 이 대상에서 제외됩니다. 할당량 제한은 최소 1시간부터 대기를 늘리고, 인증·크레딧 오류는 24시간 동안 전체 요약 요청을 중지합니다. 이 대기 상태도 저장하고 화면에 안내하며, 계정 오류 때문에 개별 기사의 재시도 횟수를 소진하지 않습니다.

키가 없거나 `SECURITY_NEWS_TRANSLATION_ENABLED=false`이면 AI를 호출하지 않습니다. 이 설정은 보고서의 `AI_ENABLED`와 독립적입니다. [환경 설정](04_environment_and_config.md)의 `SECURITY_NEWS_TRANSLATION_*` 값으로 모델·경로·한도를 조정할 수 있습니다. 설정 변경 후 backend 컨테이너를 재생성해야 합니다. 무료 티어를 지원하는 `gemini-3.5-flash-lite`(기본)와 `gemini-3.1-flash-lite`만 허용하며 유료 전용 모델·미등록 모델·자동 별칭은 클라이언트 생성 전에 거부합니다. 오류나 할당량 소진 시 다른 모델로 전환하지 않습니다. [공식 가격표](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite)를 기준으로 제한하며 실제 무료 사용에는 Free Tier 프로젝트의 키와 사용 가능한 할당량이 필요합니다. 유료 프로젝트는 잔액 소진 시 자동으로 무료 전환되지 않습니다. [결제 안내](https://ai.google.dev/gemini-api/docs/billing)

백업할 때 번역 저장소도 포함해야 합니다. 실행 중인 SQLite 파일은 단순 복사 대신 SQLite backup API로 일관된 사본을 만드세요. 파일이나 `reports_data` 볼륨을 삭제하면 기번역 이력이 사라져 원문을 다시 번역할 수 있습니다. 외부 API 응답 직후 프로세스가 강제로 종료되어 저장하지 못한 요청까지 정확히 한 번 실행되는 것은 보장하지 않습니다.

## API

기본 경로는 `/api/v1`이며 기존 `require_auth`를 적용합니다. `LOGIN=false`인 개발 환경은 기존 정책에 따라 guest를 허용합니다.

두 화면은 기존 보안 뉴스 API와 캐시를 공유하며 `kind`로 표시 자료를 분리합니다. 별도의 CVE 수집 API나 중복 스케줄은 추가하지 않습니다.

| 요청 | 응답 |
|---|---|
| `GET /security-news` | 마지막 저장 결과와 출처 상태 조회, 외부 수집·번역 시작 없음 |
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
| `refresh_interval_seconds` | 정기 수집 주기, 86400초. 실제 실행 시각은 매일 08:00 KST |
| `translation` | 번역 활성화·진행 여부, 번역 완료·대기 건수와 상태 안내 |

`items`는 `id`, `source_id`, `kind`, `title`, `summary`, `original_description`, `title_ko`, `summary_ko`, `url`, `published_at`, `updated_at`, `cve_ids`, `severity`, `cvss_score`, `cvss_version`, `known_exploited`, `vendor`, `product`, `due_date`, `remediations`를 포함합니다. `title`·`summary`는 원문이고 `summary_ko`는 한국어 한 줄 요약 또는 null입니다. 별도 제목 번역을 생성하지 않으므로 호환용 `title_ko`는 null입니다. `original_description`은 요약으로 자르기 전의 NVD·KEV 일반 텍스트 설명이며, 설명당 최대 100,000자를 보존하고 KEV에는 연결된 NVD 설명도 합칩니다. 해당 설명이 없는 이전 저장본·일반 뉴스는 null입니다. CVE에는 AI 요약을 적용하지 않습니다. `kind`는 `cve|advisory|news`, `severity`는 `critical|high|medium|low|unknown`입니다. 자료에 없는 점수·날짜·제품은 null입니다.

`remediations`는 제품별 `vendor`, `product`, `affected_versions`, `fixed_version`, `reference_url`, `fixed_version_basis`, `fixed_version_branch` 배열이며 정보가 없으면 빈 배열입니다. `product`·`affected_versions`는 문자열, 나머지는 문자열 또는 null입니다. `fixed_version_basis`는 `vendor|nvd_range|description` 또는 null, `fixed_version_branch`는 숫자 `major.minor` 계열 또는 null입니다. `fixed_version`은 숫자 정렬을 위해 버전 문자열만 유지하며 NVD 기준의 '이상'·계열 문구는 화면에서 표시합니다. 새 필드가 없는 이전 저장본은 null로 복원하고 다음 정상 수집에서 보완합니다. 같은 취약점이 여러 제품·버전 범위에 영향을 주면 각각 표시합니다.

`translation`은 호환을 위해 기존 필드명을 유지하며 `enabled`, `translating`, `translated_count`, `pending_count`, `message`로 AI 요약 활성화·진행·완료·대기 상태를 반환합니다. 건수는 AI 대상 보안 권고·뉴스만 포함하며 이미 한국어인 자료와 CVE는 제외합니다. 원문 수집의 `refreshing`과 요약의 `translating`은 별개이며 요약 중에도 수집 제한이 지난 경우 최신 자료를 확인할 수 있습니다.

`sources`는 `id`, `name`, `homepage`, `kind`, `status`, `count`, `last_success_at`, `error`, `warning`을 포함합니다. `status`는 `ok|stale|error|pending`입니다. 전체 출처 실패도 상태를 설명할 수 있도록 정상 snapshot 응답으로 반환합니다.

60초 이내의 완료된 작업에 다시 수동 요청하면 `429`와 `Retry-After`를 반환합니다. 화면의 대기 시간은 서버가 전달한 `retry_after_seconds`를 응답 수신 시각부터 계산하므로 PC와 서버의 시계 차이에 영향받지 않습니다. 서비스 미구성은 `503`, 인증 실패는 기존 인증 응답을 따릅니다. 정상 및 서비스 오류 응답은 `Cache-Control: no-store`입니다.

## 구현과 운영

```text
backend/src/
  domain/entities/security_news.py
  domain/entities/security_news_translation.py
  application/ports/security_news_port.py
  application/ports/security_news_snapshot_port.py
  application/ports/security_news_translation_port.py
  application/services/security_news_translation.py
  application/use_cases/security_news.py
  infrastructure/external/security_news_source.py
  infrastructure/external/security_cve_remediation.py
  infrastructure/external/gemini_news_translator.py
  infrastructure/persistence/security_news_translation_cache.py
  infrastructure/persistence/security_news_snapshot_store.py
  infrastructure/config/gemini_translation_models.py
  presentation/api/v1/security_news.py
  presentation/schemas/security_news.py
frontend/src/
  domain/SecurityNews.ts
  application/services/securityNews.ts
  infrastructure/api/securityNewsApi.ts
  presentation/hooks/useSecurityNews.ts
  presentation/components/security/
  presentation/pages/CveResponsePage.tsx
  presentation/pages/SecurityNewsPage.tsx
```

Domain은 순수 자료형, Application은 캐시·상태·작업 수명을 관리하고 Infrastructure는 HTTP·JSON·RSS 파싱, Gemini 호출과 SQLite 저장을 담당합니다. 기존 Container와 프런트엔드 ApplicationServices에서 조립합니다. 서버 종료 시 수집·번역 작업을 취소하고 진행 중인 저장을 마친 뒤 HTTP client와 저장소를 닫습니다.

HTTP는 고정된 4개 주소만 호출하며 사용자 URL 입력을 받지 않습니다. TLS 인증을 검증하고 자동 리다이렉트를 따르지 않습니다. 응답은 최대 12MiB, 출처별 전체 수집 시간은 65초로 제한합니다. `defusedxml>=0.7.1`로 DTD·외부 엔터티를 차단하고, HTML 설명은 일반 텍스트로 변환합니다. UI에서 HTML을 직접 렌더링하지 않으며 원문 링크는 HTTP/HTTPS만 허용합니다.

운영 서버에서 위 4개 HTTPS 호스트로 나가는 연결이 필요합니다. 선택적 번역에는 Google Gemini API 연결과 키가 필요하며 SMTP·Jira 권한은 추가하지 않습니다. 공급자 장애나 차단은 출처별 상태에 표시되며, 백엔드 로그에는 출처 ID와 실패 예외 종류를 남깁니다. 번역 오류의 원문 응답이나 API 키는 로그·브라우저 응답에 포함하지 않습니다.

검증은 `backend`에서 `../venv/Scripts/python.exe -m unittest tests.test_security_news tests.test_security_news_schedule tests.test_security_news_snapshot_store tests.test_security_news_source tests.test_security_cve_remediation tests.test_security_cve_ranges tests.test_security_cve_provenance tests.test_security_kev_enrichment tests.test_security_news_api tests.test_security_news_translation tests.test_gemini_news_translator tests.test_architecture tests.test_container_lifecycle`, `frontend`에서 `pnpm test:security-news`, `pnpm test:architecture`, `pnpm build`를 실행합니다. 외부 API 없이 08시 KST 예약, GET의 외부 호출 차단, 당일 중복 방지, 재시작 복원, 취소 중 시도 시각 보존, CVE 버전 추출·영향 범위 충돌·계열·제조사 출처 검증·AI 제외, 번역 캐시·호출 제한·모델 제한을 검증합니다. 실제 수집·번역 상태는 운영 로그인 후 메뉴에서 별도로 확인해야 하며 단위 테스트 성공만으로 외부 서비스의 접근 권한이나 할당량을 보증하지 않습니다.
