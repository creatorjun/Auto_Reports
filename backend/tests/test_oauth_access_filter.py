# backend/tests/test_oauth_access_filter.py
import logging
import unittest

from src.infrastructure.logging.oauth_access_filter import OAuthAccessFilter


class OAuthAccessFilterTest(unittest.TestCase):
    def test_callback_query_is_removed_from_access_log(self):
        record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0,
                                   '%s - "%s %s HTTP/%s" %d',
                                   ("127.0.0.1", "GET", "/api/v1/auth/jira/callback?code=secret&state=private", "1.1", 303), None)
        self.assertTrue(OAuthAccessFilter().filter(record))
        self.assertEqual('127.0.0.1 - "GET /api/v1/auth/jira/callback HTTP/1.1" 303', record.getMessage())

    def test_other_logs_remain_usable(self):
        record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0,
                                   '%s - "%s %s HTTP/%s" %d',
                                   ("127.0.0.1", "GET", "/api/health", "1.1", 200), None)
        original = record.getMessage()
        self.assertTrue(OAuthAccessFilter().filter(record))
        self.assertEqual(original, record.getMessage())
        record = logging.LogRecord("app", logging.INFO, "", 0, "unchanged", (), None)
        self.assertTrue(OAuthAccessFilter().filter(record))
        self.assertEqual("unchanged", record.getMessage())

    def test_api_queries_are_removed_without_losing_route_method_or_status(self):
        for target in (
            "/api/v1/storage/preview?name=sample.txt&_t=private-token",
            "/api/v1/storage/download?_t=private-token&name=sample.txt",
            "/api/v1/jobs/test/stream?token=private-token",
            "/api/v1/storage/preview?%5Ft=private-token",
            "/api/v1/jobs/test/stream?%74oken=private-token",
            "/api/v1/search?q=private-query&page=2",
            "/api?token=private-token",
        ):
            with self.subTest(target=target):
                original = ("127.0.0.1", "GET", target, "1.1", 401)
                record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0,
                                           '%s - "%s %s HTTP/%s" %d', original, None)
                self.assertTrue(OAuthAccessFilter().filter(record))
                self.assertEqual(f'127.0.0.1 - "GET {target.split("?", 1)[0]} HTTP/1.1" 401', record.getMessage())
                self.assertNotIn("private", record.getMessage())
                self.assertEqual(target, original[2])

    def test_non_api_and_unrelated_log_arguments_are_preserved(self):
        for args in (
            ("127.0.0.1", "GET", "/assets/app.js?v=123", "1.1", 200),
            ("127.0.0.1", "GET", "/api-documentation?section=auth", "1.1", 200),
            ("127.0.0.1", "GET", None, "1.1", 200),
            ("one", "two"),
        ):
            with self.subTest(args=args):
                record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, "log", args, None)
                self.assertTrue(OAuthAccessFilter().filter(record))
                self.assertEqual(args, record.args)
