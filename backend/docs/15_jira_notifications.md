# Jira 알림 연동

사이드바 로그아웃 위의 Jira 알림은 Jira로 로그인한 사용자만 이용할 수 있습니다. 로그인 사용자 이름과 Jira에서 확인한 이메일은 같은 위치에 표시하며 내부 계정 ID는 표시하지 않습니다. 이메일을 제공하지 않으면 별도 안내를 표시하고 주소를 추정하지 않습니다. 로컬 로그인은 기존 ID를 표시합니다. 로컬 관리자·일반 로컬 로그인·로그인 비활성화 상태에는 알림 버튼을 표시하지 않으며 서버도 접근을 거부합니다. 현재 로그인한 Jira 사이트의 알림을 전체·직접·관심으로 조회하고 한 번에 최대 30개씩 더 불러옵니다.

## 구조와 인증

`JiraNotificationsUseCase`가 로그인한 사용자의 `JiraUserGrantStorePort`와 `JiraNotificationSourcePort`를 조합합니다. `JiraNotificationClient`는 Atlassian 공식 GraphQL의 `notifications.notificationFeed`와 선택한 알림의 읽음 처리를 호출하며, API·화면은 공급자 응답 대신 내부 모델을 사용합니다. 보고서 수집 계정이나 개인정보 보고용 소유자 인증은 사용하지 않습니다.

기존 직원 로그인 권한인 `read:jira-user`, `read:jira-work`를 사용합니다. 공식 스키마는 읽음 mutation에도 `read:jira-work`와 외부 OAuth를 허용하므로 추가 scope나 `offline_access`를 요청하지 않습니다. OAuth access token은 실제 만료 시각까지만 서버 프로세스 메모리에 보관하며 최대 1,024개로 제한합니다. JWT에는 임의의 연결 ID만 들어가며 원문 Jira token은 브라우저·DB·로그에 저장하지 않습니다.

로그아웃은 해당 연결을 제거하고 개인정보 삭제 시 메모리 연결을 비웁니다. 요청이 진행 중이어도 연결이 제거되면 도착한 알림을 반환하지 않습니다. 알림 목록은 서버에 저장하지 않으며 브라우저는 패널을 닫거나 세션이 바뀌면 요청과 캐시를 정리합니다. 응답에는 `Cache-Control: no-store`를 적용합니다.

## 화면과 API

`GET /api/v1/jira/notifications?category=all|direct|watching&cursor=...`를 앱 Bearer 세션으로 호출합니다. 사용자 ID·다른 사용자 token을 파라미터로 받지 않습니다.

- `connected`: 알림 목록과 다음 페이지 cursor를 반환합니다. 빈 목록은 정상 조회 결과입니다.
- `reconnect_required`: Jira 연결이 만료되었거나 서버 재시작 등으로 연결이 없습니다. 앱 세션을 종료하지 않고 Jira 재로그인을 안내합니다.
- HTTP 401/403: 앱 세션이 유효하지 않거나 Jira 로그인이 아닙니다.
- HTTP 503: Jira 응답 오류·제한·시간 초과 등으로 조회하지 못했습니다. 이전 목록이나 빈 목록을 정상 결과로 표시하지 않습니다.

알림 묶음은 최신 알림과 묶음 건수로 표시하며, 안 읽은 항목에 점과 `읽음 처리` 버튼을 표시합니다. 버튼이나 알림 링크를 클릭하면 해당 묶음을 Jira에서도 읽음으로 변경합니다. 링크는 기존처럼 새 탭으로 열리며, 실패한 읽음 요청은 별도로 재시도할 수 있습니다. 목록을 여는 것만으로 읽음 처리하지 않습니다. 전체 미확인 건수는 조회한 페이지의 건수와 다르므로 벨에 임의의 숫자를 표시하지 않습니다. 알림 링크는 설정된 Jira 사이트의 HTTPS 주소만 허용하고 본문은 일반 텍스트로 표시합니다.

`POST /api/v1/jira/notifications/read`에 `notification_id`, `group_id`, `category`를 전달합니다. 서버는 현재 사용자의 연결로 `notificationGroup`에서 해당 알림의 그룹·사이트·분류를 확인한 뒤 `markNotificationsByGroupIdAsRead`를 호출합니다. `beforeInclusive`를 선택한 알림 ID로 고정해 그보다 새로운 알림은 읽음 처리하지 않습니다. 반환 문자열의 의미를 추정하지 않고 같은 그룹을 다시 조회해 선택한 알림의 `readState`가 `read`임을 확인합니다. 이어 선택 시각 이전의 미읽음 알림이 남아 있지 않은지도 확인해야 성공 응답을 반환합니다. 시각 경계에서 선택한 알림을 빠뜨리지 않도록 조회 상한에 1ms를 더하며, 같은 시각의 새 알림 때문에 확인에 실패할 수 있어도 이를 임의로 읽음 처리하지 않습니다. 각 조회는 30개로 제한하며 알림이 이동하거나 확인되지 않으면 실패로 처리합니다. 실패 시 새로고침 후 다시 시도할 수 있습니다.

성공 응답은 `connection_status: connected`, 대상 ID·그룹과 `is_read: true`입니다. 연결 만료는 `reconnect_required`와 `is_read: false`, 확인 실패는 HTTP 503입니다. 프런트는 확인된 ID·그룹 쌍만 갱신하고 같은 그룹에 새로 도착한 알림에는 읽음 상태를 전파하지 않습니다. 중복 클릭, 세션 변경과 늦은 응답도 분리합니다. 전체 읽음·미확인 수 초기화 요청은 보내지 않습니다.

## 운영

현재 단일 backend 프로세스 배포 구조에서 동작합니다. 기존 배포 이전의 Jira 로그인이나 서버 재시작 후 첫 조회에는 재로그인이 필요합니다. OAuth의 실제 access token 만료 후에도 재로그인이 필요하며, 앱 세션 갱신은 Jira 연결의 만료를 연장하지 않습니다. 여러 backend 프로세스로 확장할 때는 사용자 연결 저장소의 수명·보호·삭제 정책을 유지하는 공유 구현이 필요합니다.

알림 조회 자체는 DB 마이그레이션이나 새 환경변수가 없습니다. 로그인 이메일 표시는 마이그레이션 `0023`의 서버 프로필 필드를 사용합니다. 네트워크에서 `https://api.atlassian.com/graphql`로 나가는 HTTPS 접근이 필요합니다. 기존 보고서·메일·Rovo 설정은 변경하지 않습니다.

## 공급자 근거

- [Atlassian GraphQL API](https://developer.atlassian.com/platform/atlassian-graphql-api/graphql/): OAuth endpoint, schema 탐색과 필드별 scope.
- 공식 endpoint의 introspection에서 조회·mutation의 `notifications`가 `read:jira-work`를 지원함을 확인했습니다. `notificationGroup`, `markNotificationsByGroupIdAsRead`, `beforeInclusive`, `collabContextRoutingAri`와 외부 OAuth 지원도 확인했습니다. 스키마 계약 검증과 실제 로그인 계정의 데이터 검증은 구분합니다.
- [Atlassian 인앱 알림 안내](https://support.atlassian.com/atlassian-cloud/kb/overview-of-in-app-notifications-in-atlassian-cloud-products/): 직접·관심 알림과 읽음·미확인 상태의 차이.
