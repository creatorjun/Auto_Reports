# Presentation Shared Elements

기존 `src/shared` catch-all 레이어는 제거했습니다. 모든 레이어가 자유롭게 참조하는 Shared 폴더는 의존 방향을 우회하기 쉬우므로, 항목을 실제 소유 레이어에 배치합니다.

| 위치 | 책임 |
|------|------|
| `domain` | 여러 유스케이스가 공유하는 업무 모델 |
| `application/ports` | 외부 동작 계약 |
| `application/errors` | adapter 독립 오류 |
| `presentation/config/constants.ts` | 차트·테이블·SLA 표시 상수 |
| `presentation/config/ui.ts` | Tailwind 표시 토큰 |
| `presentation/config/queryKeys.ts` | TanStack Query key |
| `presentation/utils/formatters.ts` | 날짜와 숫자 표시 formatter |

새 공용 코드는 사용처가 넓다는 이유만으로 별도 Shared에 두지 않고, 변경 이유와 책임을 기준으로 소유 레이어를 정합니다.
