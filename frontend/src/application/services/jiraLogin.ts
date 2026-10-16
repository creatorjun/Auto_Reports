// frontend/src/application/services/jiraLogin.ts
export function jiraLoginError(result: string | null): string | null {
  switch (result) {
    case 'denied':
      return 'Jira 로그인이 취소되었거나 이 서비스에 접근할 권한이 없습니다.'
    case 'unavailable':
      return 'Jira 로그인에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.'
    case 'error':
      return 'Jira 로그인 요청이 만료되었거나 올바르지 않습니다. 다시 로그인해 주세요.'
    default:
      return null
  }
}
