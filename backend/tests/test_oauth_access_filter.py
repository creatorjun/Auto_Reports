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
