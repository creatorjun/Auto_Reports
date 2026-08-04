# frontend/docs/SHARED.md

# Shared 레이어

모든 레이어에서 자유롭게 참조 가능한 횡단 관심사 모음입니다.

---

## constants.ts

### SLA 관련

| 상수 | 값 | 설명 |
|------|----|------|
| `SLA_TARGET_RATE` | `80` | SLA 목표 달성률 (%) |
| `SLA_COLOR_MAP` | object | green/yellow/red 컬러 토큰 |
| `SLA_RING_RADIUS` | `32` | 도넛 링 반지름 |

### 차트 관련

| 상수 | 값 |
|------|---------|
| `CHART_HEIGHT` | `360` |
| `CHART_TICK_FONT_SIZE` | `11` |
| `CHART_LEGEND_ICON_SIZE` | `7` |
| `CHART_LEGEND_COLOR` | `'#86868b'` |
| `CHART_STROKE_WIDTH` | `2.5` |
| `CHART_DOT_RADIUS` | `4` |
| `CHART_ACTIVE_DOT_RADIUS` | `6` |
| `CHART_GRADIENT_STOP_START` | `0.25` |
| `CHART_GRADIENT_STOP_END` | `0.03` |
| `PIE_COLORS` | `['#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6']` |
| `MONTHS_BACK` | `6` |
| `MONTHLY_COUNT_COLORS` | `{ created: '#3b82f6', resolved: '#22c55e' }` |
| `SLA_MONTHLY_COLORS` | `{ initial: '#3b82f6', resolution: '#22c55e' }` |

### 테이블 관련

| 상수 | 값 |
|------|---------|
| `TABLE_PAGE_SIZE` | `50` |
| `TABLE_MIN_COL_FRAC` | `0.05` |

### 기타

| 상수 | 값 |
|------|---------|
| `DEFAULT_JIRA_BASE_URL` | `'https://seculayer.atlassian.net'` |

---

## ui.ts

### STATUS_STYLE

이슈 상태명 → Tailwind 클래스 매핑:

| 상태 | bg 클래스 |
|------|----------|
| 할 일 / 재오픈 | `bg-status-todo` |
| 자료 요청 중 | `bg-status-data` |
| 이슈 리뷰 중 | `bg-status-review` |
| 연구소 대기/검토 중 | `bg-status-lab` |
| 구현 중 | `bg-status-impl` |
| 배포 파일 검토 중 | `bg-status-deploy` |
| 결과 대기 중 | `bg-status-pending` |

### STAGE_MAP

이슈 상태 → 스테이지 인덱스 (0~6) 매핑. 프로그레스 바 시각화에 사용.

### MODAL_CLS

모달 공통 Tailwind 클래스 토큰 객체:

```ts
MODAL_CLS.overlay       // fixed inset-0 z-50 ...
MODAL_CLS.containerBase // bg-white rounded-2xl ...
MODAL_CLS.header
MODAL_CLS.title
MODAL_CLS.subtitle
MODAL_CLS.closeBtn
MODAL_CLS.body
MODAL_CLS.footer
MODAL_CLS.closeText
MODAL_CLS.thCell
MODAL_CLS.keyCell
MODAL_CLS.bodyCell
MODAL_CLS.metaCell
MODAL_CLS.elapsedCell
```

---

## utils/formatters.ts

```ts
formatDate(dateStr: string): string      // 'YYYY-MM-DD' → 'YYYY년 MM월 DD일'
formatNumber(n: number): string          // 숫자 → 천단위 쉼표
```
