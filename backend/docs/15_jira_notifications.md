# Jira 알림 연동

사이드바 로그아웃 위의 Jira 알림은 Jira로 로그인한 사용자만 이용할 수 있습니다. 로그인 사용자 이름과 ID는 같은 위치에 표시합니다. Jira의 ID는 Atlassian 계정 식별자이며 이메일 주소를 추정하지 않습니다. 로컬 관리자·일반 로컬 로그인·로그인 비활성화 상태에는 알림 버튼을 표시하지 않으며 서버도 접근을 거부합니다. 현재 로그인한 Jira 사이트의 알림을 전체·직접·관심으로 조회하고 한 번에 최대 30개씩 더 불러옵니다.

## 구조와 인증

`JiraNotificationsUseCase`가 로그인한 사용자의 `JiraUserGrantStorePort`와 `JiraNotificationSourcePort`를 조합합니다. `JiraNotificationClient`는 Atlassian 공식 GraphQL의 `notifications.notificationFeed`를 호출하며, API·화면은 공급자 응답 대신 내부 모델을 사용합니다. 보고서 수집 계정이나 개인정보 보고용 소유자 인증은 사용하지 않습니다.

기존 직원 로그인 권한인 `read:jira-user`, `read:jira-work`를 사용합니다. `offline_access`나 쓰기 권한을 추가하지 않습니다. OAuth access token은 실제 만료 시각까지만 서버 프로세스 메모리에 보관하며 최대 1,024개로 제한합니다. JWT에는 임의의 연결 ID만 들어가며 원문 Jira token은 브라우저·DB·로그에 저장하지 않습니다.

로그아웃은 해당 연결을 제거하고 개인정보 삭제 시 메모리 연결을 비웁니다. 요청이 진행 중이어도 연결이 제거되면 도착한 알림을 반환하지 않습니다. 알림 목록은 서버에 저장하지 않으며 브라우저는 패널을 닫거나 세션이 바뀌면 요청과 캐시를 정리합니다. 응답에는 `Cache-Control: no-store`를 적용합니다.

## 화면과 API

`GET /api/v1/jira/notifications?category=all|direct|watching&cursor=...`를 앱 Bearer 세션으로 호출합니다. 사용자 ID·다른 사용자 token을 파라미터로 받지 않습니다.

- `connected`: 알림 목록과 다음 페이지 cursor를 반환합니다. 빈 목록은 정상 조회 결과입니다.
- `reconnect_required`: Jira 연결이 만료되었거나 서버 재시작 등으로 연결이 없습니다. 앱 세션을 종료하지 않고 Jira 재로그인을 안내합니다.
- HTTP 401/403: 앱 세션이 유효하지 않거나 Jira 로그인이 아닙니다.
- HTTP 503: Jira 응답 오류·제한·시간 초과 등으로 조회하지 못했습니다. 이전 목록이나 빈 목록을 정상 결과로 표시하지 않습니다.

알림 묶음은 최신 알림과 묶음 건수로 표시하며, 안 읽은 항목에 점을 표시합니다. 전체 미확인 건수는 조회한 페이지의 건수와 다르므로 벨에 임의의 숫자를 표시하지 않습니다. 읽음 처리·모두 읽음·미확인 수 초기화 요청은 보내지 않습니다. 알림 링크는 설정된 Jira 사이트의 HTTPS 주소만 허용하고 본문은 일반 텍스트로 표시합니다.

## 운영

현재 단일 backend 프로세스 배포 구조에서 동작합니다. 기존 배포 이전의 Jira 로그인이나 서버 재시작 후 첫 조회에는 재로그인이 필요합니다. OAuth의 실제 access token 만료 후에도 재로그인이 필요하며, 앱 세션 갱신은 Jira 연결의 만료를 연장하지 않습니다. 여러 backend 프로세스로 확장할 때는 사용자 연결 저장소의 수명·보호·삭제 정책을 유지하는 공유 구현이 필요합니다.

DB 마이그레이션이나 새 환경변수는 없습니다. 네트워크에서 `https://api.atlassian.com/graphql`로 나가는 HTTPS 접근이 필요합니다. 기존 보고서·메일·Rovo 설정은 변경하지 않습니다.

## 공급자 근거

- [Atlassian GraphQL API](https://developer.atlassian.com/platform/atlassian-graphql-api/graphql/): OAuth endpoint, schema 탐색과 필드별 scope.
- 공식 endpoint의 introspection에서 `notifications`의 `read:jira-work` 지원과 `notificationFeed` 및 `collabContextRoutingAri` 인자를 확인했습니다. 스키마 계약 검증과 실제 로그인 계정의 데이터 검증은 구분합니다.
- [Atlassian 인앱 알림 안내](https://support.atlassian.com/atlassian-cloud/kb/overview-of-in-app-notifications-in-atlassian-cloud-products/): 직접·관심 알림과 읽음·미확인 상태의 차이.
