// frontend/src/presentation/pages/PrivacyPage.tsx
import PolicyLayout, { PolicySection, PolicySupportLink } from '@/presentation/components/auth/PolicyLayout'

export default function PrivacyPage() {
  return (
    <PolicyLayout title="개인정보처리방침">
      <p className="text-body leading-relaxed text-apple-mid">SecuLayer는 사내 기술지원 업무의 이슈 현황, SLA, 재배포 및 보고서 관리 서비스를 운영합니다. 이 방침은 본 서비스가 로그인과 업무자료 처리 과정에서 사용하는 개인정보, 보관 방식 및 문의 방법을 설명합니다.</p>

      <PolicySection id="privacy-purpose" title="1. 처리 목적과 정보의 출처">
        <p>정보는 사용자 인증과 접근 권한 확인, Jira 업무 현황 집계, 보고서 이력 관리, 업무자료 조회 및 서비스 운영·보안을 위해 처리합니다. Jira 정보는 회사가 연결한 Jira 사이트와 프로젝트에서 API로 조회하며, 사이트 관리와 파일 보관함의 자료는 권한 있는 사용자가 직접 등록합니다.</p>
      </PolicySection>

      <PolicySection id="privacy-data" title="2. 처리하는 정보">
        <dl className="divide-y divide-apple-divider rounded-xl border border-apple-divider px-4">
          <div className="grid gap-2 py-4 sm:grid-cols-[140px_minmax(0,1fr)]">
            <dt className="font-medium text-apple-dark">로그인 정보</dt>
            <dd className="min-w-0">Atlassian 계정 식별자, Jira 사이트 식별자, 표시 이름, 계정 활성 여부, 대상 프로젝트 조회 권한을 확인합니다. Jira 로그인 표시 이름과 프로필 상태·버전은 서버에 저장합니다. Jira 로그인용 JWT에는 사용자 식별자, 로그인 방식, 프로필 버전, 만료 정보와 알림 연결용 임의 식별자가 포함되며 표시 이름이나 원문 Atlassian 토큰은 포함하지 않습니다.</dd>
          </div>
          <div className="grid gap-2 py-4 sm:grid-cols-[140px_minmax(0,1fr)]">
            <dt className="font-medium text-apple-dark">티켓·보고서</dt>
            <dd className="min-w-0">티켓 번호·제목·유형·상태·생성일, 고객사·파트너사, 보고자·담당자·TAC 담당자, SLA와 상태별 시간, 재배포 현황·사유 등 업무 정보를 조회하고 보고서 이력에 저장합니다. 일부 화면은 Jira의 댓글·첨부정보 등 최신 업무자료를 조회합니다.</dd>
          </div>
          <div className="grid gap-2 py-4 sm:grid-cols-[140px_minmax(0,1fr)]">
            <dt className="font-medium text-apple-dark">등록 업무자료</dt>
            <dd className="min-w-0">사용자가 등록한 고객사·사이트·담당자 연락처, 장비·작업 이력, 접속 정보 및 업로드 파일에 포함된 정보를 저장합니다. 업무에 필요하지 않은 개인정보는 등록하지 않아야 합니다.</dd>
          </div>
          <div className="grid gap-2 py-4 sm:grid-cols-[140px_minmax(0,1fr)]">
            <dt className="font-medium text-apple-dark">접속·작업 기록</dt>
            <dd className="min-w-0">로그인 결과, 사용자 식별자, 발생 시각, 일부 이벤트의 IP 주소, 보고서 생성·삭제 및 파일 작업 등의 감사 기록을 저장합니다. 모든 화면 이동이나 클릭을 기록하는 방식은 아닙니다.</dd>
          </div>
        </dl>
      </PolicySection>

      <PolicySection id="privacy-auth" title="3. Jira 인증과 자동 로그인">
        <p>Jira 로그인은 Atlassian의 OAuth 인증·승인 화면에서 진행합니다. 본 서비스는 Jira 비밀번호나 사용자의 개인 API 토큰을 입력받지 않습니다. 로그인 연동은 사용자와 업무 조회 범위를 요청하며 Jira 쓰기 권한을 요청하지 않습니다.</p>
        <p>일반 사용자의 Atlassian access token은 로그인 검증과 본인의 Jira 알림 조회에 사용하며 실제 만료 시각까지만 서버 메모리에 보관합니다. 원문 토큰을 DB나 브라우저에 저장하지 않으며 로그아웃·개인정보 갱신 또는 삭제 처리·서버 종료 시 해당 메모리 연결을 제거합니다. 일반 로그인은 offline_access 권한을 요청하지 않으며 Atlassian refresh token을 저장하지 않습니다. 자동 로그인에는 본 서비스가 발급한 JWT를 사용하고, 서버에 저장된 프로필 상태와 버전을 함께 확인합니다. 앱 로그인과 별개로 Jira 알림 연결이 만료되면 다시 Jira로 로그인해야 합니다.</p>
        <p>개인정보 정기 보고를 위해서는 최고 관리자가 별도 연결 화면에서 앱 소유자의 승인을 진행합니다. 이때 사용자·업무 조회 및 offline_access 권한을 요청하고, 앱 소유자의 refresh token을 서버에서 암호화해 보관합니다. 이 자격 증명은 Atlassian 개인정보 보고용 access token을 발급받는 데 사용하며, 직원의 로그인 승인 범위를 변경하지 않습니다.</p>
        <p>서비스 access token은 브라우저 메모리에 보관하며 기본 유효기간은 30분입니다. refresh token은 HTTPS에서 전달되는 HttpOnly·Secure 쿠키에 보관합니다. Jira 로그인 세션은 기본 7일 뒤 다시 인증하며, 갱신으로 최초 인증의 최대 유효기간을 연장하지 않습니다. 실제 기간은 운영 설정에 따릅니다.</p>
        <p>표시 이름과 access token은 브라우저 메모리에서만 관리하며, 표시 이름·토큰·비밀번호를 localStorage에 저장하지 않습니다. 이전 버전의 로그인 표시 정보가 저장되어 있으면 서비스 시작 시 해당 저장 항목을 제거합니다. 테마와 표 표시 설정은 별도로 저장하며 유지합니다. 로그아웃하면 이 브라우저의 로그인 쿠키와 메모리 세션을 제거합니다. 브라우저의 사이트 데이터를 삭제해 저장된 설정을 지울 수 있으며, 쿠키를 차단하거나 삭제하면 자동 로그인이 제한됩니다.</p>
      </PolicySection>

      <PolicySection id="privacy-access" title="4. 정보 접근과 연동 서비스">
        <p>Jira 알림은 Jira로 로그인한 사용자 본인의 권한으로 조회합니다. 알림의 제목·본문·작성자·시각·읽음 상태는 화면 표시에만 사용하며 서버에 목록을 저장하지 않습니다. 패널을 닫거나 로그인 세션이 변경되면 브라우저 알림 캐시를 제거합니다. 앱에서 알림을 조회해도 Jira의 읽음 상태는 변경하지 않습니다.</p>
        <p>저장 보고서와 업무자료는 본 서비스 접근 권한이 있는 내부 사용자가 조회합니다. Jira에서 현재 사용자에게 보이는 티켓만으로 저장 보고서를 다시 제한하는 구조는 아니므로 회사의 업무 권한과 내부 자료 취급 기준에 따라 이용해야 합니다. 감사로그 조회는 별도의 관리자 권한으로 제한합니다.</p>
        <p>Atlassian은 Jira 로그인과 원본 업무자료 조회를 제공하는 연동 서비스입니다. Atlassian 인증·승인 화면과 Jira에 저장된 원본 정보의 처리는 해당 서비스의 정책도 적용됩니다. 본 서비스에서 로그아웃해도 Jira 원본이나 Atlassian 계정이 삭제되지는 않습니다.</p>
        <p>앱 소유자의 개인정보 보고 연결이 설정되면, 서버는 보관 중인 개인정보에 연결된 Atlassian 계정 식별자(accountId)와 해당 계정 정보의 가장 오래된 수집 시점을 Atlassian에 정기 보고합니다. 보고 요청에는 이름·이메일·티켓 본문을 포함하지 않으며, 다음 보고 주기는 Atlassian 응답을 따릅니다. 연결과 처리 상태는 최고 관리자 전용 화면에서 확인합니다.</p>
        <p>이 방침의 시행일 기준으로 AI 분석 기능은 비활성화되어 있습니다. 운영자가 기능을 활성화하면 보고서의 운영 집계·지연 사유·일부 이슈 상세를 Google Gemini API로 전달해 분석할 수 있습니다. 업무 이메일 알림 기능을 활성화한 경우에는 지정된 수신자에게 알림을 발송합니다. 선택 기능의 사용 여부와 처리 범위는 문의 창구에서 확인할 수 있습니다.</p>
      </PolicySection>

      <PolicySection id="privacy-retention" title="5. 보관과 삭제">
        <p>로그인용 JWT는 정해진 유효기간까지 사용할 수 있습니다. 보고서 이력, 등록 업무자료 및 감사로그는 운영 서버에 보관하며, 자료 종류별 보관 설정과 관리자 관리 절차를 따릅니다. 로그인 세션 만료, 로그아웃 또는 Atlassian 연결 해제만으로 저장된 업무자료가 자동 삭제되지는 않습니다.</p>
        <p>Atlassian 정기 보고에서 정보 변경(updated) 응답을 받으면 Jira에서 최신 표시 이름을 자동 조회하여 서버 프로필과 계정 식별자가 연결된 저장 보고서의 보고자·담당자·TAC 담당자 이름을 갱신합니다. 과거 정보 변경 처리로 삭제 표시가 된 이름도 같은 계정 식별자로 확인해 복구합니다. 조회나 저장에 실패하면 갱신 중 표시를 유지하고 다시 시도합니다.</p>
        <p>계정 폐쇄(closed) 응답을 받은 경우에만 해당 프로필 이름과 계정 식별자가 연결된 저장 보고서의 구조화된 사용자 이름을 삭제 표시로 바꾸고 로그인을 허용하지 않습니다. 정보 변경과 계정 폐쇄 모두 기존 로그인 세션을 무효화하므로 이후 이용 시 Jira에서 다시 인증해야 합니다. 이슈 건수·SLA 시간 등 업무 집계와 보고서 이력은 유지합니다.</p>
        <p>티켓 제목·본문·댓글·첨부파일, 직접 등록한 업무자료와 자유 입력 내용에 포함된 개인정보는 계정 식별자만으로 일괄 삭제할 수 없습니다. 계정 연결을 확인할 수 없는 과거 정보와 이미 내려받은 파일도 별도 확인이 필요합니다. 이런 자료의 정정·삭제는 문의를 통해 대상과 범위를 확인하여 처리합니다.</p>
        <p>개인정보의 열람·정정·삭제·처리정지를 요청하려면 아래 문의 창구로 연락해 주세요. 요청자와 대상 자료를 확인한 뒤 처리 가능 범위와 결과를 안내합니다. Jira 원본의 정정과 이미 저장된 보고서의 정정·삭제는 별도로 확인해야 하며, 업무 기록의 보존 필요가 있는 경우 해당 사유를 함께 안내합니다.</p>
      </PolicySection>

      <PolicySection id="privacy-security" title="6. 보호 조치">
        <p>서비스는 HTTPS 통신, 서명된 JWT 검증, 로그인 사용자와 감사로그 관리자 권한의 구분을 적용합니다. 인증 과정의 비밀번호·client secret·토큰을 감사로그에 남기지 않도록 처리하며 OAuth 인증 토큰을 브라우저 주소에 포함해 반환하지 않습니다. 사용자는 공유 기기에서 이용을 마친 뒤 로그아웃하고 계정과 업무자료를 안전하게 관리해야 합니다.</p>
      </PolicySection>

      <PolicySection id="privacy-contact" title="7. 문의와 방침 변경">
        <p>운영 주체는 SecuLayer이며 개인정보 관련 문의 및 요청은 <PolicySupportLink />로 접수합니다. 비밀번호나 인증 토큰을 이메일에 포함하지 마세요.</p>
        <p>처리 범위나 서비스 운영 방식이 변경되면 이 페이지에 변경 내용과 시행일을 안내합니다. 본 방침은 2026년 10월 16일부터 적용하며, 2026년 10월 21일 Jira 알림 조회·임시 인증 보관과 변경된 이름의 자동 갱신·복구, 폐쇄 계정의 삭제 처리에 관한 내용을 반영했습니다.</p>
      </PolicySection>
    </PolicyLayout>
  )
}
