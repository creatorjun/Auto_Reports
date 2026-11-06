// frontend/src/presentation/config/cveVulnerabilities.ts
export const CVE_VULNERABILITIES_LABEL = 'CVE 취약점'

export const CVE_VULNERABILITY_LINKS = [
  { to: '/cve/os', label: 'OS' },
  { to: '/cve/java', label: 'JAVA' },
  { to: '/cve/db', label: 'DB' },
  { to: '/cve/eyecloudxoar', label: '솔루션' },
] as const
