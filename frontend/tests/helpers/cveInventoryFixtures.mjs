// frontend/tests/helpers/cveInventoryFixtures.mjs
export function finding(overrides = {}) {
  return {
    id: 'maven:example:library:CVE-2020-12345', package_id: 'maven:example:library', package_name: 'example:library', ecosystem: 'Maven',
    inventory_versions: ['3.0.0'], product_names: ['Example Library'], categories: ['Java 라이브러리'], cve_id: 'CVE-2020-12345',
    title: 'Example package vulnerability', affected_versions: ['1.0.0', '1.1.0', '2.0.0'], fixed_versions: ['1.2.0', '2.1.0'],
    ranges: [{ affected: '>= 1.0.0, < 1.2.0', fixed: '1.2.0', type: 'ECOSYSTEM' }, { affected: '>= 2.0.0, < 2.1.0', fixed: '2.1.0', type: 'ECOSYSTEM' }],
    severity: 'high', cvss_score: 8.1, cvss_version: '3.1', references: ['https://example.com/security'], source_ids: ['GHSA-aaaa-bbbb-cccc'], source: 'osv',
    published_at: '2020-01-01T00:00:00Z', modified_at: '2026-10-28T00:00:00Z', inventory_impact: 'not_affected', affected_inventory_versions: [],
    first_seen_at: '2026-10-28T00:00:00Z', known_exploited: false, severity_source: 'GHSA', collection_status: 'ok', ...overrides,
  }
}

export function snapshot(overrides = {}) {
  return {
    items: [finding(), finding({ id: 'second', package_id: 'second', package_name: 'jinja2', ecosystem: 'PyPI', cve_id: 'CVE-2024-56201', inventory_versions: ['3.1.4'], severity: 'critical', cvss_score: 9.1, inventory_impact: 'affected', affected_inventory_versions: ['3.1.4'], known_exploited: true, ranges: [{ affected: '>= 3.0.0, < 3.1.5', fixed: '3.1.5', type: 'ECOSYSTEM' }], fixed_versions: ['3.1.5'] }), finding({ id: 'third', package_id: 'third', package_name: 'kernel-uek', ecosystem: 'Oracle Linux:8', cve_id: 'CVE-2026-12345', severity: 'unknown', cvss_score: null, inventory_impact: 'unknown', fixed_versions: [], ranges: [], collection_status: 'stale' })],
    total: 3, page: 1, page_size: 50, severity_counts: { critical: 1, high: 1, medium: 0, low: 0, unknown: 1 },
    inventory: { dataset_id: 'test-inventory', snapshot_at: '2026-10-22T15:04:43+09:00', product_count: 1105, target_count: 1542, package_count: 900, runtime_verified: false },
    coverage: { total: 900, ready: 700, unmapped: 200, ok: 650, stale: 10, error: 20, pending: 20 }, ecosystems: ['Maven', 'PyPI', 'Oracle Linux:8'],
    initialized: true, refreshing: false, refreshed_at: '2026-10-28T00:00:00Z', next_refresh_at: null, retry_after_seconds: 0, refresh_interval_seconds: 7200, progress: { completed: 700, total: 700 }, error: null,
    ...overrides,
  }
}

export function packagePage(overrides = {}) {
  return { items: [{ id: 'needs-mapping', name: 'Custom library', ecosystem: 'Unknown', versions: ['버전 미확인'], product_names: ['Custom library'], categories: ['기타'], source: 'osv', mapping_status: 'unmapped', mapping_reason: '공식 패키지 식별자 확인 필요', status: 'unmapped', last_success_at: null, last_attempt_at: null, error: null, cve_count: 0 }], total: 1, page: 1, page_size: 20, ...overrides }
}
