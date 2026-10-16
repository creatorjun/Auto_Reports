// frontend/src/presentation/pages/TermsPage.tsx
import { Link } from 'react-router-dom'
import PolicyLayout, { PolicySection, PolicySupportLink } from '@/presentation/components/auth/PolicyLayout'

export default function TermsPage() {
  return (
    <PolicyLayout title="이용약관">
      <p className="text-body leading-relaxed text-apple-mid">이 약관은 SecuLayer가 운영하는 사내 기술지원 보고서 서비스의 이용 범위와 사용자·운영자의 기본 준수사항을 정합니다. 서비스는 회사의 기술지원 업무를 위한 내부 업무 도구입니다.</p>

      <PolicySection id="terms-access" title="1. 이용 대상과 인증">
        <p>서비스는 회사가 이용을 허용한 내부 사용자를 대상으로 합니다. Jira 로그인은 연결된 회사 Jira 사이트의 활성 계정과 TACEA 프로젝트 조회 권한을 확인합니다. 관리자 계정은 운영자가 별도로 관리하며, Jira 로그인으로 관리자 권한을 취득하지 않습니다.</p>
        <p>이용자는 본인에게 허용된 계정과 권한으로 접속해야 합니다. Jira 인증에 동의하지 않거나 필요한 권한이 없으면 Jira 로그인을 사용할 수 없습니다. 계정 사용 권한이 변경되었거나 인증 정보가 유출된 경우 즉시 운영자에게 알려야 합니다.</p>
      </PolicySection>

      <PolicySection id="terms-service" title="2. 제공 기능과 정보의 기준">
        <p>서비스는 Jira 이슈와 SLA·재배포 현황의 조회·집계, 보고서 생성·이력 조회·내보내기, 고객사·사이트 및 파일 관리를 제공합니다. 제공 범위는 운영 설정과 사용자의 서비스 권한에 따라 달라질 수 있습니다.</p>
        <p>저장 보고서는 생성·수집 시점의 정보를 담은 기록입니다. Jira의 현재 상태나 이후 정정 사항과 차이가 있을 수 있고, 외부 API의 응답·권한·데이터 누락으로 일부 항목을 확인하지 못할 수 있습니다. 업무 판단, 고객 전달 또는 책임 소재 확인이 필요한 경우 Jira 원본과 관련 담당자의 확인을 거쳐야 합니다.</p>
        <p>보고서에 표시된 SLA와 체류시간은 해당 보고서의 계산 기준 및 Jira 설정을 따릅니다. 자동 집계나 선택적 AI 분석만으로 계약상 책임 또는 개인의 업무 책임이 확정되는 것은 아닙니다.</p>
      </PolicySection>

      <PolicySection id="terms-confidentiality" title="3. 업무자료와 비밀 유지">
        <p>서비스의 보고서, 티켓, 고객사 정보, 파일 및 기타 업무자료는 허용된 업무 목적과 범위에서 사용해야 합니다. 회사의 사전 허용 없이 외부에 배포하거나 공개하지 않아야 하며, 다운로드·내보내기한 자료에도 동일한 관리 기준을 적용합니다.</p>
        <p>사용자는 등록하거나 업로드하는 자료를 취급할 권한이 있어야 하고, 업무에 불필요한 개인정보나 제3자의 권리를 침해하는 자료를 등록하지 않아야 합니다. 잘못 등록된 정보나 자료의 노출을 발견하면 운영자에게 알려 주세요.</p>
      </PolicySection>

      <PolicySection id="terms-prohibited" title="4. 금지되는 이용">
        <ul className="list-disc space-y-2 pl-6">
          <li>계정·비밀번호·인증 토큰을 공유하거나 다른 사람의 계정으로 이용하는 행위</li>
          <li>권한을 우회하거나 허용받지 않은 자료를 조회·수집·변경·삭제하는 행위</li>
          <li>서비스 운영을 방해하는 요청, 악성 파일 업로드 또는 보안 통제의 무력화</li>
          <li>업무자료를 승인되지 않은 외부 서비스로 전송하거나 목적 외로 이용하는 행위</li>
        </ul>
      </PolicySection>

      <PolicySection id="terms-operation" title="5. 운영과 이용 제한">
        <p>운영자는 유지보수, 장애 대응, 보안 조치, 외부 API 정책 또는 조직의 접근 정책에 따라 기능을 변경하거나 이용을 일시 제한할 수 있습니다. 권한 상실, 계정 유출, 금지행위 또는 보안상 위험이 확인되면 해당 사용자의 접근을 제한할 수 있습니다.</p>
        <p>서비스 중단이나 데이터 오류를 발견한 경우 문의 창구로 알려 주세요. 업무자료의 보관·삭제와 이력 정정은 운영자가 대상과 처리 범위를 확인해 안내합니다. 로그아웃이나 연동 해제가 보고서·업무자료의 삭제를 의미하지는 않습니다.</p>
      </PolicySection>

      <PolicySection id="terms-privacy" title="6. 개인정보와 작업 기록">
        <p>사용자 인증, 업무자료 및 감사로그의 개인정보 처리는 <Link to="/privacy" className="text-brand-600 underline underline-offset-4">개인정보처리방침</Link>에 따릅니다. 로그인 결과와 일부 주요 작업은 운영·보안을 위한 감사로그에 기록되며 권한 있는 관리자가 확인할 수 있습니다.</p>
      </PolicySection>

      <PolicySection id="terms-contact" title="7. 문의와 적용일">
        <p>서비스 이용과 이 약관에 관한 문의는 SecuLayer의 <PolicySupportLink />로 연락해 주세요. 이용 조건이 변경되면 이 페이지에 변경 내용과 시행일을 안내합니다.</p>
        <p>이 약관은 2026년 10월 16일부터 적용합니다.</p>
      </PolicySection>
    </PolicyLayout>
  )
}
