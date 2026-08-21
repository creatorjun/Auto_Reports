# backend/tests/test_sla_dashboard_schema.py
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.domain.entities.sla_dashboard import SlaDashboardComment, SlaDashboardIssue
from src.presentation.schemas.sla_dashboard_schema import (
    SlaDashboardCommentSchema,
    SlaDashboardIssueSchema,
)


class SlaDashboardSchemaTest(unittest.TestCase):
    def test_serializes_domain_issue(self) -> None:
        issue = SlaDashboardIssue(
            key="TACEA-4500",
            created="2026-08-20 09:00",
            updated="2026-08-21 10:00",
            status="구현 중",
        )

        schema = SlaDashboardIssueSchema.model_validate(issue)

        self.assertEqual("TACEA-4500", schema.key)
        self.assertEqual("2026-08-21 10:00", schema.updated)

    def test_serializes_domain_comment(self) -> None:
        comment = SlaDashboardComment(
            id="10001",
            author="작성자",
            body="댓글 본문",
            created="2026-08-21 10:00",
            updated="2026-08-21 10:30",
        )

        schema = SlaDashboardCommentSchema.model_validate(comment)

        self.assertEqual("작성자", schema.author)
        self.assertEqual("댓글 본문", schema.body)
