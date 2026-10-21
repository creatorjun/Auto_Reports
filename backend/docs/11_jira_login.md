# Jira 로그인과 JWT 자동 로그인

문서 기준: 2026-10-21.

## 사용자 흐름

일반 로그인 화면 `/login`은 **Jira 계정으로 로그인**만 표시하며 Atlassian OAuth 2.0 (3LO) 인증 화면으로 이동합니다. Jira 비밀번호나 개인 API 토큰은 이 서비스에 입력하지 않습니다. 기존 `ADMIN`과 `SUPERADMIN`의 아이디·비밀번호 로그인은 `/admin`에 직접 접속해 사용합니다. 일반 로그인 화면과 메뉴에는 `/admin` 링크를 표시하지 않습니다. 관리자 인증과 권한 검증은 기존 서버 로직을 유지합니다.

인증을 마치면 서버가 회사 Jira 사이트, 활성 사용자, 대상 프로젝트의 `BROWSE_PROJECTS` 권한을 확인하고 이 서비스의 JWT를 발급합니다. 로그인 대상은 `JIRA_BASE_URL`과 `PROJECT_KEY` 설정을 따릅니다. 다른 Jira 사이트, 비활성 계정, 앱·포털 고객 계정, 프로젝트 조회 권한이 없는 계정은 거부합니다. Jira 사용자는 일반 로그인 사용자 권한을 사용하며 감사로그는 기존 superadmin 전용입니다. Jira의 티켓별 접근 제어를 이 서비스의 저장 보고서에 적용하는 방식은 아닙니다.

access token과 표시 이름은 브라우저 메모리에만 저장하고 refresh token은 HttpOnly·SameSite=Lax cookie에 저장합니다. `/login`과 `/admin` 직접 접속, 새로고침, 브라우저 재접속 시 cookie로 access token을 복원합니다. 자동 로그인은 cookie가 남아 있고 유효한 동안만 작동합니다. 브라우저가 cookie를 지우면 재로그인이 필요합니다. 이전 버전의 `auth-storage` localStorage 항목은 시작 시 제거하며 테마와 표 설정은 유지합니다. Jira JWT에는 이름 대신 계정 식별자와 서버 프로필 버전만 넣고 이름은 서버 프로필에서 조회합니다.

access token 기본 수명은 30분입니다. Jira 세션은 최초 인증에서 `JWT_REFRESH_EXPIRE_DAYS`(기본 7일)까지만 유효하며 갱신으로 그 기한을 연장하지 않습니다. 만료 뒤에는 Jira에서 다시 인증해 권한을 확인합니다. 기존 로컬 계정의 갱신 방식은 유지합니다. Jira 권한 변경을 이미 발급된 JWT에 실시간 반영하지는 않으며, `JIRA_LOGIN_ENABLED=false`로 Jira 로그인을 끄면 해당 JWT도 거부합니다.

로그아웃은 브라우저 cookie와 메모리 세션을 지웁니다. 진행 중인 갱신 응답이 세션을 되살리지 않도록 갱신 완료 후 로그아웃 요청을 보냅니다. 일반 로그아웃은 별도 복사된 토큰의 즉시 폐기나 전체 기기 로그아웃 기능을 제공하지 않습니다. 개인정보 갱신·삭제 이벤트는 Jira 서버 프로필 버전을 변경하므로 해당 계정의 기존 access/refresh token을 모두 거부합니다. 이름을 포함하던 이전 버전 Jira JWT도 재로그인이 필요합니다.

## Atlassian 앱 등록

1. [개발자 콘솔](https://developer.atlassian.com/console/myapps/)에서 OAuth 2.0 integration을 만듭니다. 앱 이름 예시는 `SecuLayer Auto Reports Login`, 접근 범위는 Resource-level입니다.
2. Jira API의 Classic scope `read:jira-user`, `read:jira-work`를 추가합니다. 사용자 확인과 대상 프로젝트 조회 권한 검사에 사용하며 쓰기 권한은 요청하지 않습니다. 직원 로그인은 이 두 권한만 사용하며 앱 소유자의 개인정보 정기 보고 연결에만 `offline_access`를 추가합니다.
3. Authorization의 OAuth 2.0 callback URL을 `https://10.1.43.100/api/v1/auth/jira/callback`으로 등록합니다. 서버의 `JIRA_OAUTH_REDIRECT_URI`도 정확히 같은 HTTPS 주소로 설정하고 `COOKIE_SECURE=true`를 적용합니다.
4. Settings의 Client ID와 Secret을 서버 `.env`에 저장합니다. Git·브라우저 코드·문서에 실제 Secret을 넣지 않습니다.
5. 여러 직원이 사용하는 경우 Distribution에 공급자명, 실제 개인정보처리방침·이용약관 URL, 지원 연락처를 등록하고 조직의 앱 접근 정책을 확인합니다. 정책 페이지는 로그인 전에도 대상 직원이 열 수 있어야 합니다. 미공유 앱은 소유자에게만 인증이 허용될 수 있습니다.

Distribution에서 개인정보 저장을 `Yes`로 선언하면 Personal Data Reporting API 구현 확인이 필요합니다. 이 버전에는 계정별 보유 데이터 보고와 정정·삭제 처리 기능을 포함합니다. 실제 소유자 연결, 과거 이력의 계정 식별자 연결, API 보고 성공을 확인한 뒤 구현 확인란을 선택합니다. 콜백 URL 등록 성공과 직원 대상 공유 활성화는 별도 단계입니다.

현재 운영 서비스의 `/privacy`와 `/terms`는 로그인 없이 열리는 실제 정책 페이지이며 지원 연락처는 `jh.han@seculayer.com`입니다. 2026-10-16 운영 HTTPS, 앱 소유자의 Jira 로그인·자동 로그인·로그아웃·root 감사로그 조회를 확인했고, Atlassian Distribution의 `Sharing` 저장도 확인했습니다. 공급자명은 `SecuLayer`, 개인정보 저장 선언은 `Yes`이며 두 정책 URL과 지원 이메일이 실제 등록되었습니다. 직원용 Atlassian 동의 화면에서 회사 정책 링크와 두 읽기 권한 표시를 확인했습니다. 다른 직원 계정으로의 최종 로그인은 해당 직원의 직접 승인과 회사 Jira 프로젝트 접근 권한이 필요합니다.

직원 공유 전 기존 보고서 29개(대시보드 9개, SLA 17개, 재배포 3개)의 사용자 필드 7,848개를 Jira 변경 이력에 근거해 계정 ID와 연결했습니다. 이력 행 삭제 없이 실제 개인정보 보고 API에 62개 계정을 보고했고 미보고·미연결·처리 대기와 오류가 없는 상태를 확인했습니다. 당시 구현은 응답에서 확인된 폐쇄 1개·갱신 7개 계정에 대해 관련 보고서 16개의 사용자 이름을 삭제 표시로 정리했습니다. 티켓 번호·집계·보고서 행은 유지했습니다. 현재 구현에서는 `updated` 계정의 최신 Jira 이름을 자동 조회하여 계정 ID가 연결된 과거 보고서도 복구하고 `closed`만 삭제 표시로 유지합니다. 위 수치는 최초 검증 결과이며 현재 처리·복구 상태는 `/admin/jira-privacy`에서 확인합니다.

```dotenv
LOGIN=true
JIRA_LOGIN_ENABLED=true
JIRA_OAUTH_CLIENT_ID=replace-with-client-id
JIRA_OAUTH_CLIENT_SECRET=replace-with-client-secret
JIRA_OAUTH_REDIRECT_URI=https://10.1.43.100/api/v1/auth/jira/callback
JIRA_PRIVACY_OWNER_ACCOUNT_ID=replace-with-verified-app-owner-account-id
COOKIE_SECURE=true
```

등록·조직 허용이 완료되지 않은 동안 `JIRA_LOGIN_ENABLED=false`로 둡니다. 버튼은 설정 필요 상태로 표시하며 `/admin`의 기존 관리자 로그인을 계속 사용할 수 있습니다. 설정 후 backend를 재생성하고 `/api/v1/auth/providers`의 `jira.enabled`와 실제 승인·복귀·새로고침·로그아웃을 확인합니다. OAuth 앱 등록이나 권한 승인 완료 여부는 코드 배포 성공과 별도로 검증해야 합니다.

## 운영 HTTPS와 인증서

운영 접속 주소는 `https://10.1.43.100`을 사용합니다. 내부용 자체 서명 서버 인증서의 Subject Alternative Name에는 `IP Address:10.1.43.100`을 넣고 Basic Constraints는 `CA:false`로 설정합니다. 이 인증서는 서버 연결용 leaf 인증서이며 다른 인증서를 발급하는 CA 용도가 아닙니다.

자체 서명 인증서는 공개 인증기관이 보증하는 인증서가 아니므로 일반 브라우저에서 기본적으로 신뢰하지 않습니다. 사용자가 접속하는 각 클라이언트에 서버의 공개 인증서만 배포해 신뢰 설정을 적용해야 합니다. 인증서의 개인 키는 운영 서버에만 보관하며 클라이언트, Git, 프런트엔드 번들에 배포하지 않습니다.

클라이언트에서 인증서 경고 없이 HTTPS 접속이 되는지 확인한 다음 Jira 로그인과 callback 복귀를 검증합니다. 인증서 검증을 생략한 연결 성공만으로 클라이언트의 신뢰 설정 완료를 판단하지 않습니다. `Secure` cookie를 사용하므로 운영 로그인은 HTTPS에서 진행하며, callback 등록 주소와 서버 환경값을 함께 유지합니다.

## 감사로그

Jira 사용자도 로그인·로그아웃, 보고서 생성·삭제, 파일 업로드·이동·삭제 등 기존 감사 이벤트의 기록 대상입니다. `SUPERADMIN`으로 설정한 root 계정이 조회하며 Jira 사용자와 일반 admin에게는 조회 권한을 부여하지 않습니다. 사용자 열에는 실제 이름 대신 `jira:<cloudId>:<accountId>` 식별자가 저장됩니다. 모든 화면 클릭, 조회, 검색, 필터 변경을 수집하는 방식은 아닙니다.

## 구현과 검증 경계

Domain `AuthIdentity`, Application `JiraOAuthPort`와 `AuthService`, Infrastructure `JiraOAuthClient`와 `JwtService`, Presentation 인증 API로 분리합니다. 외부 HTTP client는 인증 요청 범위에서 닫으며 전체 인증 시간 제한을 적용합니다. 직원 로그인의 Atlassian access token은 계정 검증과 본인 Jira 알림 조회에 사용하고 실제 만료 시각까지만 서버 메모리에 보관합니다. 로그아웃·개인정보 갱신 또는 삭제·서버 종료 시 연결을 제거하며 DB나 브라우저에 원문 토큰을 저장하지 않습니다. 직원 로그인에는 `offline_access`를 요청하지 않으며, 별도로 승인한 앱 소유자의 정기 보고용 refresh token만 서버에서 암호화해 보관합니다.

## 개인정보 보고 연결과 운영

`/admin`에서 최고 관리자 계정으로 로그인한 뒤 `/admin/jira-privacy`에 직접 접속합니다. 일반 admin과 Jira 직원은 접근할 수 없습니다. 연결 버튼은 기존 관리자 세션을 유지하면서 `JIRA_PRIVACY_OWNER_ACCOUNT_ID`로 지정한 앱 소유자의 Atlassian 승인을 요청합니다. 다른 계정 또는 시작 당시와 다른 관리자 세션은 callback에서 거부합니다.

개인정보 보고용 refresh token은 `JWT_SECRET`에서 용도를 구분해 파생한 키로 암호화하며 Git·브라우저·상태 API에 반환하지 않습니다. 최소 32바이트 서버 비밀값이 필요하고, 이 키가 변경되어 복호화가 불가능하면 소유자가 다시 연결해야 합니다. 토큰 교체는 API 보고 전에 DB에 저장하며 네트워크 오류와 비밀값을 사용자 화면이나 로그에 노출하지 않습니다.

마이그레이션 `0019`는 `personal_data_accounts`와 `personal_data_reporting_grants` 테이블을 추가합니다. 계정별 가장 오래된 보유 데이터 조회 시각, 프로필 버전, 다음 보고 시각, 처리 중 삭제·갱신 상태 및 재시도 시각을 보관합니다. 스케줄러는 시작 시와 약 5분마다 처리할 작업을 확인하지만 Atlassian으로 보내는 주기는 계정별 `Cycle-Period`(기본 7일)를 따릅니다. 요청당 최대 90계정을 보고하고 `Retry-After`를 준수합니다.

Atlassian에 전달하는 항목은 계정 ID와 가장 오래된 조회 시각입니다. `closed` 응답만 프로필 이름과 해당 계정 ID로 확인되는 보고서의 보고자·담당자·TAC 담당자 이름을 삭제 표시로 바꿉니다. 폐쇄된 계정은 최신 프로필을 조회하거나 이름을 복구하지 않으며 로그인을 허용하지 않습니다.

`updated` 응답은 해당 사용자 이름을 갱신 중 상태로 전환한 뒤 Jira에서 계정 ID로 최신 표시 이름을 자동 조회합니다. 조회에 성공하면 서버 프로필과 계정 ID가 연결된 저장 보고서의 구조화된 사용자 이름을 함께 갱신하고 계정을 활성 상태로 전환합니다. 과거 `updated` 처리에서 삭제 표시가 된 이름도 같은 방법으로 복구합니다. 조회·저장 실패 시 갱신 중 표시와 처리 상태를 유지하여 재시도하며 이전 이름이나 삭제 표시로 확정하지 않습니다. 갱신 조회가 실패하더라도 함께 대기 중인 `closed` 계정 삭제를 먼저 처리합니다.

갱신·삭제 이벤트는 기존 로그인 세션을 무효화하고 관련 캐시를 비웁니다. 이름 갱신은 사용자의 재로그인을 기다리지 않고 수행하지만 이후 로그인에는 새 인증이 필요합니다. 보고서 행, 티켓 번호, 집계값과 시간 정보는 유지합니다. 중간 실패는 DB에 남은 상태를 기준으로 재개하며 삭제·갱신 중인 이름이 신규 저장에서 다시 들어오지 않도록 검사합니다.

과거 보고서는 Jira 티켓 변경 이력과 보고서 생성 시각을 대조해 계정 ID를 보완합니다. 표시 이름만으로 다른 계정을 추정해서 연결하지 않습니다. 연결되지 않은 사용자 필드가 있으면 관리자 화면의 준비 상태는 미완료로 표시합니다. 티켓 제목·설명·AI 문구·업로드 파일의 자유 입력 개인정보와 별도 내려받은 파일은 구조화된 사용자 필드와 다르므로 지원 연락처를 통한 별도 확인·처리 대상입니다. 백업을 복원하면 삭제 상태도 함께 복원하고 개인정보 보고 처리 후 서비스를 개방해야 합니다.

관리자 API는 `GET /auth/jira/privacy/status`, `POST /auth/jira/privacy/start`, `POST /auth/jira/privacy/run`입니다. 공개 직원 로그인 API와 분리하며 상태 응답에는 소유자 토큰을 포함하지 않습니다. 실제 보고 성공, 미보고·처리 대기 계정, 미연결 필드가 없는 상태를 확인한 후 앱 공유를 완료합니다.

state는 예측 불가능한 nonce, HttpOnly cookie, 서버의 10분 단일 사용 기록을 함께 검증합니다. 서버 재시작은 진행 중인 OAuth 요청을 무효화하므로 다시 로그인합니다. 현재 단일 worker 구성에서 동작하며 여러 worker·인스턴스로 확장하면 state 저장소를 공유하도록 변경해야 합니다.

nginx와 Uvicorn access log는 `/api` 및 그 하위 경로의 query를 기록하지 않습니다. OAuth callback의 code/state, 파일 미리보기의 `_t`, SSE의 `token`이 접근 로그에 남지 않으며 메서드·경로·상태는 유지합니다. 성공·실패 감사 이벤트에는 인증 결과와 계정 식별자만 남깁니다. callback 응답은 `no-store`와 `no-referrer`를 설정하며 JWT와 client secret을 redirect URL에 넣지 않습니다.

회귀 검증은 로컬 관리자 로그인, superadmin 제한, 정상 OAuth와 state 변조·재사용·만료, 잘못된 사이트·계정·권한, 외부 API 실패, JWT 만료와 Jira 세션 최대 수명, 동시 갱신 및 로그아웃 경합을 포함합니다. 모의 API 테스트는 실제 Atlassian 앱 승인이나 조직 정책 통과를 증명하지 않습니다.

공식 사양: [Atlassian OAuth 2.0](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/), [현재 사용자](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-myself/), [사용자 권한](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-permissions/).
