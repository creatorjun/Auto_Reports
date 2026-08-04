# frontend/docs/DEPENDENCIES.md

# 외부 라이브러리

## Runtime Dependencies

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `react` | ^18.3.1 | UI 프레임워크 |
| `react-dom` | ^18.3.1 | DOM 렌더러 |
| `react-router-dom` | ^6.23.1 | 클라이언트 라우팅 |
| `@tanstack/react-query` | ^5.45.1 | 서버 상태 관리 (캐싱·페칭) |
| `zustand` | ^4.5.4 | 클라이언트 전역 상태 |
| `axios` | ^1.7.2 | HTTP 클라이언트 |
| `recharts` | ^2.12.7 | 차트 라이브러리 (SVG 기반) |
| `react-hook-form` | ^7.52.1 | 폼 상태 관리 |
| `@hookform/resolvers` | ^3.9.0 | zod 리졸버 연동 |
| `zod` | ^3.23.8 | 스키마 유효성 검사 |
| `date-fns` | ^3.6.0 | 날짜 유틸리티 |
| `clsx` | ^2.1.1 | 조건부 클래스명 결합 |
| `lucide-react` | ^0.400.0 | 아이콘 라이브러리 |
| `pdfjs-dist` | ^4.4.168 | PDF 렌더링 |
| `mammoth` | ^1.8.0 | Word(.docx) → HTML 변환 |
| `xlsx` | ^0.18.5 | Excel 파싱 |
| `marked` | ^13.0.0 | Markdown → HTML |
| `react-markdown` | ^9.0.1 | Markdown 렌더 컴포넌트 |
| `remark-gfm` | ^4.0.0 | GitHub Flavored Markdown |
| `rehype-highlight` | ^7.0.0 | 코드 블록 문법 강조 |
| `highlight.js` | ^11.10.0 | 코드 하이라이터 |

## Dev Dependencies

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `vite` | ^5.3.3 | 번들러/개발 서버 |
| `@vitejs/plugin-react` | ^4.3.1 | Vite React 플러그인 |
| `typescript` | ^5.5.3 | TypeScript 컴파일러 |
| `tailwindcss` | ^3.4.4 | 유틸리티 CSS 프레임워크 |
| `postcss` | ^8.4.39 | CSS 후처리 |
| `autoprefixer` | ^10.4.19 | 벤더 프리픽스 자동화 |
| `@types/react` | ^18.3.3 | React 타입 정의 |
| `@types/react-dom` | ^18.3.0 | ReactDOM 타입 정의 |
