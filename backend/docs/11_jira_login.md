# Jira 로그인과 JWT 자동 로그인

문서 기준: 2026-10-16.

## 사용자 흐름

일반 로그인 화면 `/login`은 **Jira 계정으로 로그인**만 표시하며 Atlassian OAuth 2.0 (3LO) 인증 화면으로 이동합니다. Jira 비밀번호나 개인 API 토큰은 이 서비스에 입력하지 않습니다. 기존 `ADMIN`과 `SUPERADMIN`의 아이디·비밀번호 로그인은 `/admin`에 직접 접속해 사용합니다. 일반 로그인 화면과 메뉴에는 `/admin` 링크를 표시하지 않습니다. 관리자 인증과 권한 검증은 기존 서버 로직을 유지합니다.

인증을 마치면 서버가 회사 Jira 사이트, 활성 사용자, 대상 프로젝트의 `BROWSE_PROJECTS` 권한을 확인하고 이 서비스의 JWT를 발급합니다. 로그인 대상은 `JIRA_BASE_URL`과 `PROJECT_KEY` 설정을 따릅니다. 다른 Jira 사이트, 비활성 계정, 앱·포털 고객 계정, 프로젝트 조회 권한이 없는 계정은 거부합니다. Jira 사용자는 일반 로그인 사용자 권한을 사용하며 감사로그는 기존 superadmin 전용입니다. Jira의 티켓별 접근 제어를 이 서비스의 저장 보고서에 적용하는 방식은 아닙니다.

access token은 브라우저 메모리에만 저장하고 refresh token은 HttpOnly·SameSite=Lax cookie에 저장합니다. `/login`과 `/admin` 직접 접속, 새로고침, 브라우저 재접속 시 cookie로 access token을 복원합니다. 자동 로그인은 cookie가 남아 있고 유효한 동안만 작동합니다. 브라우저가 cookie를 지우면 재로그인이 필요합니다. localStorage에는 표시 이름만 남고 토큰·비밀번호는 저장하지 않습니다.

access token 기본 수명은 30분입니다. Jira 세션은 최초 인증에서 `JWT_REFRESH_EXPIRE_DAYS`(기본 7일)까지만 유효하며 갱신으로 그 기한을 연장하지 않습니다. 만료 뒤에는 Jira에서 다시 인증해 권한을 확인합니다. 기존 로컬 계정의 갱신 방식은 유지합니다. Jira 권한 변경을 이미 발급된 JWT에 실시간 반영하지는 않으며, `JIRA_LOGIN_ENABLED=false`로 Jira 로그인을 끄면 해당 JWT도 거부합니다.

로그아웃은 브라우저 cookie와 메모리 세션을 지웁니다. 진행 중인 갱신 응답이 세션을 되살리지 않도록 갱신 완료 후 로그아웃 요청을 보냅니다. 현재 JWT는 서버 세션 DB를 사용하지 않으므로 별도 복사된 토큰의 즉시 폐기나 전체 기기 로그아웃 기능을 제공하지 않습니다.

## Atlassian 앱 등록

1. [개발자 콘솔](https://developer.atlassian.com/console/myapps/)에서 OAuth 2.0 integration을 만듭니다. 앱 이름 예시는 `SecuLayer Auto Reports Login`, 접근 범위는 Resource-level입니다.
2. Jira API의 Classic scope `read:jira-user`, `read:jira-work`를 추가합니다. 사용자 확인과 대상 프로젝트 조회 권한 검사에 사용하며 쓰기 권한과 `offline_access`는 요청하지 않습니다.
3. Authorization의 OAuth 2.0 callback URL을 `https://10.1.43.100/api/v1/auth/jira/callback`으로 등록합니다. 서버의 `JIRA_OAUTH_REDIRECT_URI`도 정확히 같은 HTTPS 주소로 설정하고 `COOKIE_SECURE=true`를 적용합니다.
4. Settings의 Client ID와 Secret을 서버 `.env`에 저장합니다. Git·브라우저 코드·문서에 실제 Secret을 넣지 않습니다.
5. 여러 직원이 사용하는 경우 Distribution에 공급자명, 실제 개인정보처리방침·이용약관 URL, 지원 연락처를 등록하고 조직의 앱 접근 정책을 확인합니다. 정책 페이지는 로그인 전에도 대상 직원이 열 수 있어야 합니다. 미공유 앱은 소유자에게만 인증이 허용될 수 있습니다.

Distribution에서 개인정보 저장을 `Yes`로 선언하면 Personal Data Reporting API 구현 확인이 필요합니다. 현재 버전은 Jira 표시 이름을 JWT와 브라우저 표시 정보에 보관하지만 해당 보고 API는 구현하지 않았습니다. 공유 설정을 완료하기 전에 [Atlassian 개인정보 보고 요구사항](https://developer.atlassian.com/cloud/jira/platform/user-privacy-developer-guide/)에 맞춰 보고·정정·삭제 처리를 구현해야 하며, 구현 확인란을 미리 선택하면 안 됩니다. 콜백 URL 등록 성공과 직원 대상 공유 활성화는 별도 단계입니다.

```dotenv
LOGIN=true
JIRA_LOGIN_ENABLED=true
JIRA_OAUTH_CLIENT_ID=replace-with-client-id
JIRA_OAUTH_CLIENT_SECRET=replace-with-client-secret
JIRA_OAUTH_REDIRECT_URI=https://10.1.43.100/api/v1/auth/jira/callback
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

Domain `AuthIdentity`, Application `JiraOAuthPort`와 `AuthService`, Infrastructure `JiraOAuthClient`와 `JwtService`, Presentation 인증 API로 분리합니다. 외부 HTTP client는 인증 요청 범위에서 닫으며 전체 인증 시간 제한을 적용합니다. Atlassian 토큰은 계정 검증 동안만 사용하고 저장하지 않습니다.

state는 예측 불가능한 nonce, HttpOnly cookie, 서버의 10분 단일 사용 기록을 함께 검증합니다. 서버 재시작은 진행 중인 OAuth 요청을 무효화하므로 다시 로그인합니다. 현재 단일 worker 구성에서 동작하며 여러 worker·인스턴스로 확장하면 state 저장소를 공유하도록 변경해야 합니다.

nginx와 Uvicorn access log는 OAuth callback의 code/state query를 기록하지 않습니다. 성공·실패 감사 이벤트에는 인증 결과와 계정 식별자만 남깁니다. callback 응답은 `no-store`와 `no-referrer`를 설정하며 JWT와 client secret을 redirect URL에 넣지 않습니다.

회귀 검증은 로컬 관리자 로그인, superadmin 제한, 정상 OAuth와 state 변조·재사용·만료, 잘못된 사이트·계정·권한, 외부 API 실패, JWT 만료와 Jira 세션 최대 수명, 동시 갱신 및 로그아웃 경합을 포함합니다. 모의 API 테스트는 실제 Atlassian 앱 승인이나 조직 정책 통과를 증명하지 않습니다.

공식 사양: [Atlassian OAuth 2.0](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/), [현재 사용자](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-myself/), [사용자 권한](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-permissions/).
