# backend/src/shared/constants.py
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

JIRA_MAX_RESULTS_DEFAULT  = 200
JIRA_MAX_RESULTS_LARGE    = 500
JIRA_RECENT_PAGE_SIZE     = 50

SUMMARY_TRUNCATE_LEN       = 60
SUMMARY_TRUNCATE_SHORT_LEN = 30

STATUS_ORDER: list[str] = [
    "할 일",
    "이슈 리뷰 중",
    "연구소 대기 중",
    "연구소 검토 중",
    "구현 중",
    "배포 파일 검토 중",
    "자료 요청 중",
    "결과 대기 중",
    "보류 중",
    "영업본부 검토중",
]

STAGE_MAP: dict[str, int] = {
    "할 일":            0,
    "재오픈":           0,
    "자료 요청 중":    1,
    "이슈 리뷰 중":    2,
    "연구소 대기 중":  3,
    "연구소 검토 중":  3,
    "구현 중":         4,
    "배포 파일 검토 중": 5,
    "결과 대기 중":    6,
}

AI_OVERDUE_DETAIL_LIMIT = 10
