# 인벤토리 CVE 조회

`CveResponsePage`는 `/cve-response` 경로를 유지하며 일반 보안 뉴스와 독립된 인벤토리 API를 사용한다. 기본 요청은 모든 위험도·모든 생태계·모든 파일 버전 영향 상태, 1페이지·50개·위험도순이다. 날짜 제한이나 설치 버전 필터를 암묵적으로 추가하지 않는다.

## 계층

- `domain/CveInventory.ts`: 조회, 패키지별 CVE, 범위, 수집 상태 계약
- `application/services/cveInventory.ts`: 기본 조회 조건, 상태 이름, 안전한 근거 링크
- `application/ports/ApplicationServices.ts`: `CveInventoryGateway`
- `infrastructure/api/cveInventoryApi.ts`: 인증된 HTTP 클라이언트를 통한 조회·갱신
- `presentation/hooks/useCveInventory.ts`: 세션별 React Query 캐시, 갱신 중 폴링과 중복 요청 방지
- `presentation/components/cve`: 위험도 카드, CVE 표·모바일 카드, 범위 상세, 수집 현황
- `main.tsx`: gateway 조립 및 로그아웃 시 인벤토리 캐시 제거

## API

`GET /api/v1/cve-inventory`에 `severity`, `search`, `ecosystem`, `impact`, `page`, `page_size`, `sort`를 전달한다. 응답 `total`은 현재 필터의 패키지·CVE 조합 수이며 `severity_counts`는 전체 범위의 조합 수다. 같은 CVE가 서로 다른 패키지에 해당하면 별개 행이다. 범위별 수정 정보는 행을 늘리지 않고 상세에서 보여준다.

`POST /api/v1/cve-inventory/refresh`가 반환한 기본 페이지를 현재 필터 결과로 덮어쓰지 않는다. 갱신 진행 메타데이터만 반영하고 현재 쿼리를 다시 조회한다. 이전 로그인 세션의 늦은 응답은 새 세션에 반영하지 않는다.

`GET /api/v1/cve-inventory/packages`는 수집 현황을 펼칠 때 조회한다. `status`, `search`, `page`, `page_size`를 전달하며 매핑 필요·조회 실패·대기 상태는 조회 완료 후 CVE 0건과 구분한다. 패키지 수집 현황은 CVE 결과보다 위에 배치해 수집 범위의 한계를 바로 확인할 수 있다.

## 검증

`pnpm test:security-news`, `pnpm test:architecture`, `pnpm build`로 기본 범위, 위험도 미평가, 서버 필터·페이지 전달, 안전한 출처, 실패 상태, 로그인 전환과 기존 뉴스 기능을 확인한다. 시각 검증은 데스크톱·모바일 및 라이트·다크 모드 각각 수행한다. `tests/helpers/cveInventoryFixtures.mjs`는 테스트용 가상 응답이며 운영 데이터가 아니다.
