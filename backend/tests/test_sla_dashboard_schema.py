# backend/tests/test_sla_dashboard_schema.py
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.domain.entities.sla_dashboard import (
    SlaDashboardComment,
    SlaDashboardCommentImage,
    SlaDashboardIssue,
)
from src.presentation.schemas.sla_dashboard_schema import (
    SlaDashboardCommentSchema,
    SlaDashboardIssueSchema,
)


class SlaDashboardSchemaTest(unittest.TestCase):
    def test_serializes_domain_issue(self) -> None:
        issue = SlaDashboardIssue(
            key="TACEA-4500",
            type="개선",
            summary="티켓 제목",
            created="2026-08-20 09:00",
            updated="2026-08-21 10:00",
            status="구현 중",
        )

        schema = SlaDashboardIssueSchema.model_validate(issue)

        self.assertEqual("TACEA-4500", schema.key)
        self.assertEqual("개선", schema.type)
        self.assertEqual("티켓 제목", schema.summary)
        self.assertEqual("2026-08-21 10:00", schema.updated)

    def test_serializes_domain_comment(self) -> None:
        comment = SlaDashboardComment(
            id="10001",
            author="작성자",
            body="댓글 본문",
            created="2026-08-21 10:00",
            updated="2026-08-21 10:30",
            images=(
                SlaDashboardCommentImage(
                    attachment_id="10017",
                    alt="화면 캡처",
                ),
            ),
        )

        schema = SlaDashboardCommentSchema.model_validate(comment)

        self.assertEqual("작성자", schema.author)
        self.assertEqual("댓글 본문", schema.body)
        self.assertEqual("10017", schema.images[0].attachment_id)
        self.assertEqual("화면 캡처", schema.images[0].alt)
