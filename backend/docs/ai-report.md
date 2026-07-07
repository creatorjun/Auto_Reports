# AI 분석 보고서 명세

> 최종 수정: 2026-07-07  
> 기준 파일: `src/application/services/ai_analyzer.py`, `src/infrastructure/external/gemini_client.py`

---

## 개요

보고서 생성 시 `AiAnalyzer.analyze(report)`가 호출되어 Gemini 2.0 Flash 모델에 운영 데이터를 전송하고,  
구조화된 JSON 응답(`AiAnalysis`)을 받아 프론트엔드에 렌더링됩니다.

**활성화 조건**: 환경변수 `AI_ENABLED=true` (기본값 true)

---

## AI Context 구조

`ai_analyzer.py`가 `report` 객체에서 추출해 Gemini에 전달하는 데이터:

| 키 | 출처 위젯 | 설명 |
|---|---|---|
| `week_start` | report | 보고서 시작일 |
| `week_end` | report | 보고서 종료일 |
| `created` | w14.breakdown["생성"] | 이번 주 생성 건수 |
| `resolved` | w14.breakdown["해결"] | 이번 주 해결 건수 |
| `sla_overdue` | w1.total | SLA 초과 미해결 총 건수 |
| `issue_review` | w2.total | 이슈 리뷰 중 지연 건수 |
| `data_request` | w3.total | 자료 요청 중 지연 건수 |
| `result_pending` | w13.total | 결과 대기 중 지연 건수 |
| `lab_unassigned` | w4.total | 연구소 대기 담당자 미지정 건수 |
| `sla_met` | w12.breakdown["SLA 만족"] | SLA 만족 건수 |
| `sla_violated` | w12.breakdown["SLA 위반"] | SLA 위반 건수 |
| `avg_resolution_days` | w11.breakdown["avg_resolution_days"] | 평균 해결 소요일 |
| `yearly_created` | w8.total | 연간 누적 생성 |
| `yearly_resolved` | w9.total | 연간 누적 해결 |
| `delay_reasons` | w7.breakdown (str) | SLA 지연 사유 dict 문자열 |
| `overdue_issue_list` | w1.breakdown["issue_details"][:10] | SLA 초과 이슈 상세 (최대 10건) |

### overdue_issue_list 포맷 예시

```
  - TACEA-4345 [인시던트] [한전원자력연료] eyeCloud SIM 제품 로그... / 생성: 2026-01-15 10:30 / 상태: 진행 중 / 초과: +988.6h
  - TACEA-4167 [서비스 요청] [동아대학교] 파티션별 인덱싱 파일... / 생성: 2025-11-20 14:00 / 상태: 진행 중 / 초과: +850.4h
```

---

## Gemini 응답 스키마 (AiAnalysis)

```json
{
  "summary": "핵심 운영 현황 요약 (2~3문장, 한국어)",
  "risks": ["리스크 1", "리스크 2"],
  "recommendations": ["권고사항 1", "권고사항 2"],
  "sentiment": "good | warning | critical"
}
```

### sentiment 판단 기준

| 값 | 조건 |
|---|---|
| `good` | SLA 위반율 20% 미만, 미해결 감소 추세 |
| `warning` | SLA 위반율 20~50%, 또는 미해결 증가 |
| `critical` | SLA 위반율 50% 이상, 또는 SLA 초과 30건 이상 |

---

## 처리 흐름

```
ReportCollector.collect()
  └─▶ AiAnalyzer.analyze(report)
        └─▶ context 딕셔너리 구성
              └─▶ GeminiClient.analyze(context)
                    └─▶ PROMPT_TEMPLATE.format(**context)
                          └─▶ Gemini 2.0 Flash API 호출
                                └─▶ JSON 파싱 → AiAnalysis 반환
```

---

## 모델 설정

| 항목 | 값 |
|---|---|
| 모델 | `gemini-2.0-flash` |
| temperature | `0.3` |
| response_mime_type | `application/json` |
| API 키 환경변수 | `GEMINI_API_KEY` |
