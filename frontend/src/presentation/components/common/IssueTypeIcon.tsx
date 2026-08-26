// frontend/src/presentation/components/common/IssueTypeIcon.tsx
import { Tag } from 'lucide-react'
import cveIcon from '@/presentation/assets/issue-types/cve.svg'
import hardwareReplacementIcon from '@/presentation/assets/issue-types/hardware-replacement.svg'
import improvementIcon from '@/presentation/assets/issue-types/improvement.svg'
import incidentIcon from '@/presentation/assets/issue-types/incident.png'
import licenseRequestIcon from '@/presentation/assets/issue-types/license-request.png'
import serviceRequestIcon from '@/presentation/assets/issue-types/service-request.png'

interface IssueTypeVisual {
  src: string | null
  label: string
}

function getVisual(type: string): IssueTypeVisual {
  if (type.includes('승인된 서비스 요청')) {
    return { src: serviceRequestIcon, label: '승인된 서비스 요청' }
  }
  if (type.includes('서비스 요청')) {
    return { src: serviceRequestIcon, label: '서비스 요청' }
  }
  if (type.includes('개선')) {
    return { src: improvementIcon, label: '개선 요청' }
  }
  if (type.includes('인시던트')) {
    return { src: incidentIcon, label: '인시던트' }
  }
  if (type.toUpperCase().includes('CVE')) {
    return { src: cveIcon, label: 'CVE' }
  }
  if (type.includes('라이선스') || type.includes('라이센스')) {
    return { src: licenseRequestIcon, label: '라이선스 요청' }
  }
  if (type.includes('H/W') || type.toUpperCase().includes('HW') || type.includes('하드웨어')) {
    return { src: hardwareReplacementIcon, label: 'H/W 요청' }
  }
  return { src: null, label: type || '기타 요청' }
}

export function IssueTypeIcon({ type }: { type: string }) {
  const visual = getVisual(type)
  return (
    <span
      role="img"
      aria-label={`${visual.label} 유형`}
      title={visual.label}
      className={`inline-flex h-6 w-6 flex-shrink-0 items-center justify-center ${visual.src ? '' : 'rounded-md bg-gray-50 text-gray-600 ring-1 ring-inset ring-gray-200'}`}
    >
      {visual.src
        ? <img src={visual.src} alt="" aria-hidden="true" draggable={false} className="h-4 w-4 object-contain" />
        : <Tag size={13} aria-hidden="true" />}
    </span>
  )
}
