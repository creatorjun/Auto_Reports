# backend/tests/test_translation_retry_policy.py
import unittest

from src.application.services.translation_retry_policy import translation_retry_decision


class TranslationRetryPolicyTest(unittest.TestCase):
    def test_quota_backoff_caps_at_one_day_and_restores_attempt_budget(self):
        for previous, expected in ((0, 3600), (1, 7200), (4, 57600), (5, 86400), (100, 86400)):
            with self.subTest(previous=previous):
                decision = translation_retry_decision("quota", previous)
                self.assertEqual(expected, decision.request_delay_seconds)
                self.assertEqual(expected, decision.item_delay_seconds(3))
                self.assertEqual(previous + 1, decision.quota_failures)
                self.assertTrue(decision.restore_attempts)

    def test_configuration_failures_wait_one_day_without_consuming_attempts(self):
        for reason in ("billing", "authorization"):
            with self.subTest(reason=reason):
                decision = translation_retry_decision(reason, 0)
                self.assertEqual(86400, decision.item_delay_seconds(1))
                self.assertTrue(decision.restore_attempts)

    def test_transient_failures_limit_requests_and_retry_each_item(self):
        decision = translation_retry_decision("provider", 2)
        self.assertEqual(300, decision.request_delay_seconds)
        self.assertTrue(decision.extend_request_delay)
        self.assertIsNone(decision.quota_failures)
        self.assertFalse(decision.restore_attempts)
        for count, delay in ((0, 150), (1, 300), (2, 600), (3, 1200), (9, 76800), (100, 76800)):
            self.assertEqual(delay, decision.item_delay_seconds(count))
        self.assertIsNone(translation_retry_decision("invalid", 2).request_delay_seconds)

    def test_success_resets_quota_history_without_changing_request_reservation(self):
        decision = translation_retry_decision(None, 10)
        self.assertEqual(0, decision.quota_failures)
        self.assertIsNone(decision.message)
        self.assertIsNone(decision.request_delay_seconds)
