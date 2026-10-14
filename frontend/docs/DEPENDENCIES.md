# 의존성과 검증 명령

문서 기준: 2026-10-14 · 구현 커밋 `e280b75`.

원본은 [package.json](../package.json), 정확한 해석 버전은 [pnpm-lock.yaml](../pnpm-lock.yaml)입니다. 아래 버전은 설치 결과가 아닌 선언 범위입니다. 현재 Docker 빌드는 Node 22, 패키지 관리자는 `pnpm@11.16.0`을 사용합니다. `marked`는 현재 의존성이 아닙니다.

## Runtime

| 패키지 | 선언 버전 | 용도 |
|---|---|---|
| `react` | `^18.3.1` | UI |
| `react-dom` | `^18.3.1` | DOM 렌더링 |
| `react-router-dom` | `^6.23.1` | 라우팅 |
| `recharts` | `^2.12.7` | SVG 차트 |
| `@tanstack/react-query` | `^5.45.1` | 서버 상태·캐시 |
| `axios` | `^1.7.2` | HTTP |
| `zustand` | `^4.5.4` | 클라이언트 상태 |
| `clsx` | `^2.1.1` | 조건부 클래스 |
| `date-fns` | `^3.6.0` | 날짜 처리 |
| `xlsx` | `^0.18.5` | Excel 파싱·내보내기 |
| `mammoth` | `^1.8.0` | Word 파싱 |
| `react-markdown` | `^9.0.1` | Markdown 렌더링 |
| `remark-gfm` | `^4.0.0` | GFM |
| `rehype-highlight` | `^7.0.0` | 코드 강조 |
| `highlight.js` | `^11.10.0` | 구문 강조 |
| `pdfjs-dist` | `^4.4.168` | PDF 미리보기 |
| `react-hook-form` | `^7.52.1` | 폼 |
| `@hookform/resolvers` | `^3.9.0` | 폼 검증 연결 |
| `zod` | `^3.23.8` | 스키마 검증 |
| `lucide-react` | `^0.400.0` | 아이콘 |
| `pdfmake` | `0.3.11` | PDF 생성 |

## Development

| 패키지 | 선언 버전 | 용도 |
|---|---|---|
| `@types/react` | `^18.3.3` | React 타입 |
| `@types/react-dom` | `^18.3.0` | React DOM 타입 |
| `@vitejs/plugin-react` | `^4.3.1` | Vite React 변환 |
| `autoprefixer` | `^10.4.19` | CSS prefix |
| `postcss` | `^8.4.39` | CSS 처리 |
| `tailwindcss` | `^3.4.4` | 스타일 유틸리티 |
| `typescript` | `^5.5.3` | 타입 검사 |
| `vite` | `^5.3.3` | 개발 서버·번들 |
| `@types/pdfmake` | `0.3.3` | PDF 생성 타입 |
| `react-test-renderer` | `18.3.1` | React 회귀 검사 |

## 검증 명령

frontend 디렉터리에서 실행합니다. `pnpm build`는 `tsc && vite build`입니다. 전체 테스트 스크립트 이름 `test`는 없으므로 `node --test tests/*.test.mjs`로 전체를 실행합니다.

| 범위 | 명령 |
|---|---|
| architecture | `pnpm test:architecture` |
| pdf | `pnpm test:pdf` |
| excel | `pnpm test:excel` |
| storage | `pnpm test:storage` |
| dashboard | `pnpm test:dashboard` |
| partner | `pnpm test:partner` |
| issues | `pnpm test:issues` |
| audit | `pnpm test:audit` |
| sla-violations | `pnpm test:sla-violations` |
| report-generation | `pnpm test:report-generation` |
| 재배포 | `node --test tests/redeployments.test.mjs` |

```bash
pnpm install --frozen-lockfile
node --test tests/*.test.mjs
pnpm build
```

`pnpm dev`의 기본 프록시는 `http://backend:8000`입니다. 호스트 개발 환경에서는 [Infrastructure](INFRASTRUCTURE.md)의 주소 설정을 확인합니다. Docker production은 [운영 가이드](../../backend/docs/10_operations.md)를 따릅니다.

## 지연 로딩과 글꼴

xlsx·mammoth 파서는 Infrastructure에서 필요할 때 로드하며, PDF·Excel exporter도 다운로드 시 로드합니다. PDF에는 `src/assets/fonts`의 NanumGothic Regular·Bold를 포함합니다. 외부 CDN이나 사용자 PC 글꼴에 의존하지 않으며 [OFL.txt](../src/assets/fonts/OFL.txt)를 함께 보존합니다. 앱 화면 글꼴과 인쇄용 PDF 글꼴·조판은 구분합니다.
