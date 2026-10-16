# Presentation Shared Elements

문서 기준: 2026-10-16.

기존 `src/shared` catch-all 레이어는 제거했습니다. 모든 레이어가 자유롭게 참조하는 Shared 폴더는 의존 방향을 우회하기 쉬우므로, 항목을 실제 소유 레이어에 배치합니다.

| 위치 | 책임 |
|------|------|
| `domain` | 여러 유스케이스가 공유하는 업무 모델 |
| `application/ports` | 외부 동작 계약 |
| `application/errors` | adapter 독립 오류 |
| `presentation/config/constants.ts` | 차트·테이블·SLA 표시 상수 |
| `presentation/config/designTokens.json` | 대시보드 기준 라이트·다크 팔레트, 글꼴·크기·굵기·행간, 차트 스타일, 모서리·콘텐츠 폭의 단일 원본 |
| `presentation/config/ui.ts` | Tailwind 표시 토큰 |
| `presentation/config/queryKeys.ts` | 기본 보고서·인증·설정 등의 Query key; 신규 기능 키는 해당 훅에서도 관리 |
| `presentation/config/issueBadgeColors.ts` | 유형·상태 이름의 정규화와 공통 색상 mapping |
| `presentation/components/common/BrandLogo.tsx` | 테마별 PNG 선택 |
| `presentation/hooks/useTablePreferences.ts` | 표 정렬·너비의 검증·저장·복원 |
| `presentation/utils/formatters.ts` | 날짜와 숫자 표시 formatter |

새 공용 코드는 사용처가 넓다는 이유만으로 별도 Shared에 두지 않고, 변경 이유와 책임을 기준으로 소유 레이어를 정합니다.

## 화면 스타일

`designTokens.json`을 수정하면 `tailwind.config.js`가 CSS 변수와 의미별 유틸리티를 생성합니다. 별도 생성 파일을 편집할 필요가 없습니다. 차트에서 숫자 속성이 필요할 때도 같은 JSON을 참조하며, 페이지별 팔레트 덮어쓰기는 사용하지 않습니다.

화면 글꼴 크기는 아래 세 단계로 제한합니다. 기존 14·16·24px에 각각 2pt를 더한 값이며 CSS 기준 1pt는 4/3px이므로 증가량은 8/3px입니다. 토큰에는 16.666667·18.666667·26.666667px로 저장합니다. `typography.size`의 의미별 클래스는 이 세 값만 사용하며, 화면 너비에 따라 다른 글꼴 크기로 바꾸지 않습니다.

| 단계 | 역할 / 클래스 | 크기 |
|------|----------------|------|
| 제목·핵심 지표 | `text-page-title`, `text-metric`, `text-metric-hero`, `text-metric-compact` | 약 26.67px |
| 본문·위젯 제목 | `text-body`, `text-label`, `text-section-title`, `text-section-label` | 약 18.67px |
| 보조 정보·컨트롤 | `text-caption`, `text-control`, `text-control-label`, 차트 축·범례·레이블 | 약 16.67px |

굵기는 `font-normal`(400), `font-medium`(500), `font-semibold`(600) 세 단계입니다. 일반 본문·설명은 400, 버튼·레이블 강조는 500, 제목·주요 숫자는 600을 사용합니다. `text-ui-*`와 `font-bold`는 기존 사용처를 위한 호환 이름이며 별도 크기나 굵기를 추가하지 않습니다. 제목·지표의 행간은 1.4, 본문·보조 정보는 1.5로 맞춥니다.

`typography.chart`의 축·범례·레이블·주석·내보내기 글자 크기도 약 16.67px입니다. Markdown 미리보기는 `typography.document.body`를 약 18.67px로 사용하고 기존 1.8 행간과 본문 대비 제목·코드·표의 상대 크기를 유지합니다. 앱 UI의 세 단계와 문서 콘텐츠의 원래 계층 구조를 구분합니다.

## 브랜드와 표시 규칙

`seculayer-wordmark-light.png`와 `seculayer-wordmark-dark.png`는 투명 배경의 글자가 포함된 이미지입니다. Header와 LoginPage는 BrandLogo를 사용하고 별도 SecuLayer 텍스트를 겹치지 않습니다. 헤더는 뷰포트 `left: 50%` 기준으로 배치해 사이드바 폭과 무관하게 가운데를 유지합니다. 기존 정사각형 `seculayer-logo.png`는 favicon 용도입니다.

업무 유형·상태 배지와 SLA 체류 막대는 같은 의미의 색상 mapping을 공유합니다. 닫힘 별칭과 띄어쓰기 차이는 같은 색상이며 미등록 값은 중립색입니다. 정적 집계 기간·자동 저장·자동 갱신 사용법 안내를 새 페이지마다 추가하지 않습니다. 실제 데이터·단위·로딩·오류·누락 경고는 상태에 맞게 표시합니다.

PDF는 기존 NanumGothic 글꼴과 별도의 인쇄용 본문·표 조판을 유지합니다. PDF에 포함되는 차트 글자는 중앙 차트 토큰에 따라 약 16.67px로 표시합니다. 업로드 문서·스프레드시트의 원본 서식은 바꾸지 않으며, Markdown 미리보기의 화면 본문 크기는 위의 문서 토큰을 사용합니다.
