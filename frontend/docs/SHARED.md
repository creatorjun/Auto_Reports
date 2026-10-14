# Presentation Shared Elements

기존 `src/shared` catch-all 레이어는 제거했습니다. 모든 레이어가 자유롭게 참조하는 Shared 폴더는 의존 방향을 우회하기 쉬우므로, 항목을 실제 소유 레이어에 배치합니다.

| 위치 | 책임 |
|------|------|
| `domain` | 여러 유스케이스가 공유하는 업무 모델 |
| `application/ports` | 외부 동작 계약 |
| `application/errors` | adapter 독립 오류 |
| `presentation/config/constants.ts` | 차트·테이블·SLA 표시 상수 |
| `presentation/config/designTokens.json` | 대시보드 기준 라이트·다크 팔레트, 글꼴·크기·굵기·행간, 차트 스타일, 모서리·콘텐츠 폭의 단일 원본 |
| `presentation/config/ui.ts` | Tailwind 표시 토큰 |
| `presentation/config/queryKeys.ts` | TanStack Query key |
| `presentation/utils/formatters.ts` | 날짜와 숫자 표시 formatter |

새 공용 코드는 사용처가 넓다는 이유만으로 별도 Shared에 두지 않고, 변경 이유와 책임을 기준으로 소유 레이어를 정합니다.

## 화면 스타일

`designTokens.json`을 수정하면 `tailwind.config.js`가 CSS 변수와 의미별 유틸리티를 생성합니다. 별도 생성 파일을 편집할 필요가 없습니다. 차트에서 숫자 속성이 필요할 때도 같은 JSON을 참조하며, 페이지별 팔레트 덮어쓰기는 사용하지 않습니다.

화면 글꼴 크기는 아래 세 단계로 제한합니다. `typography.size`의 의미별 클래스는 이 세 값만 사용하며, 화면 너비에 따라 다른 글꼴 크기로 바꾸지 않습니다.

| 단계 | 역할 / 클래스 | 크기 |
|------|----------------|------|
| 제목·핵심 지표 | `text-page-title`, `text-metric`, `text-metric-hero`, `text-metric-compact` | 24px |
| 본문·위젯 제목 | `text-body`, `text-label`, `text-section-title`, `text-section-label` | 16px |
| 보조 정보·컨트롤 | `text-caption`, `text-control`, `text-control-label`, 차트 축·범례·레이블 | 14px |

굵기는 `font-normal`(400), `font-medium`(500), `font-semibold`(600) 세 단계입니다. 일반 본문·설명은 400, 버튼·레이블 강조는 500, 제목·주요 숫자는 600을 사용합니다. `text-ui-*`와 `font-bold`는 기존 사용처를 위한 호환 이름이며 별도 크기나 굵기를 추가하지 않습니다. 제목·지표의 행간은 1.4, 본문·보조 정보는 1.5로 맞춥니다.

PDF는 기존 NanumGothic 글꼴과 인쇄용 조판을 유지하며, PDF 차트 글자는 14px입니다. 업로드 문서·스프레드시트 본문은 원래 서식을 보존합니다.
