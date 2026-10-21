# backend/tests/test_jira_login_service.py
import asyncio
import hashlib
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

from src.application.ports.jira_login_port import JiraLoginRecord, JiraLoginRepositoryPort
from src.application.ports.jira_oauth_port import JiraLoginDenied, JiraLoginUnavailable, JiraOAuthPort
from src.application.ports.jira_user_grant_port import JiraUserGrant
from src.application.ports.personal_data_port import PersonalDataProfilePort
from src.application.services.jira_login_service import JiraLoginService
from src.domain.entities.auth_identity import AuthIdentity
from src.infrastructure.security.jira_login_cipher import JiraLoginCipher
from src.infrastructure.security.personal_data_cipher import PersonalDataCipher


class JiraLoginServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime(2026, 10, 22, tzinfo=timezone.utc)
        self.cookie = "d" * 43
        self.identity = AuthIdentity("jira:site:account", "사용자", "jira", int((self.now + timedelta(days=7)).timestamp()), 1, "s" * 43, "verified@example.com")
        self.grant = JiraUserGrant("site", "account", "access-secret", self.now + timedelta(hours=1), "refresh-secret")
        self.repository = AsyncMock(spec=JiraLoginRepositoryPort)
        self.oauth = AsyncMock(spec=JiraOAuthPort)
        self.profiles = AsyncMock(spec=PersonalDataProfilePort)
        self.lease = Mock()
        self.lease.record = JiraLoginRecord(1, hashlib.sha256(self.cookie.encode()).hexdigest(), 1, self.identity, self.grant)
        self.lease.save_grant = AsyncMock(side_effect=self.save_grant)
        self.lease.revoke_authorization = AsyncMock()
        self.repository.lease_authorization.return_value.__aenter__.return_value = self.lease
        self.repository.resolve.return_value = self.identity
        self.repository.issue_session.return_value = self.identity
        self.repository.finish_login.return_value = self.identity
        self.repository.has_device.return_value = True
        self.oauth.validate_user_grant.return_value = self.identity
        self.profiles.register_identity.return_value = self.identity
        self.service = JiraLoginService(self.repository, self.oauth, self.profiles, clock=lambda: self.now)
        self.addAsyncCleanup(self.service.aclose)

    async def save_grant(self, grant, now):
        self.lease.record = replace(self.lease.record, grant=grant)

    async def test_finish_login_stores_only_cookie_hash_and_independent_opaque_session(self):
        identity, cookie = await self.service.finish_login(self.grant, self.identity, self.cookie)
        self.assertEqual(self.identity, identity)
        arguments = self.repository.finish_login.await_args.kwargs
        self.assertEqual(hashlib.sha256(cookie.encode()).hexdigest(), arguments["device_hash"])
        self.assertEqual(hashlib.sha256(self.cookie.encode()).hexdigest(), arguments["previous_device_hash"])
        self.assertEqual(43, len(arguments["session_id"]))
        self.assertNotEqual(cookie, arguments["session_id"])
        self.assertEqual(self.now + timedelta(days=7), arguments["session_expires_at"])
        self.assertEqual(self.now + timedelta(days=90), arguments["device_expires_at"])
        self.oauth.validate_user_grant.assert_not_awaited()

    async def test_resume_checks_provider_profile_every_time_and_extends_device_inactivity(self):
        self.assertEqual(self.identity, await self.service.resume(self.cookie))
        self.oauth.validate_user_grant.assert_awaited_once_with(self.grant)
        self.profiles.register_identity.assert_awaited_once_with(self.identity)
        self.oauth.refresh_user_grant.assert_not_awaited()
        self.assertEqual(self.now + timedelta(days=90), self.repository.issue_session.await_args.kwargs["device_expires_at"])

    async def test_expired_grant_is_saved_before_provider_validation(self):
        old = replace(self.grant, expires_at=self.now)
        self.lease.record = replace(self.lease.record, grant=old)
        self.oauth.refresh_user_grant.return_value = self.grant

        async def validate(grant):
            self.lease.save_grant.assert_awaited_once_with(self.grant, self.now)
            return self.identity

        self.oauth.validate_user_grant.side_effect = validate
        await self.service.resume(self.cookie)
        self.oauth.refresh_user_grant.assert_awaited_once_with(old)

    async def test_transient_refresh_failure_preserves_authorization_and_device(self):
        self.lease.record = replace(self.lease.record, grant=replace(self.grant, expires_at=self.now))
        self.oauth.refresh_user_grant.side_effect = JiraLoginUnavailable("temporarily unavailable")
        with self.assertRaises(JiraLoginUnavailable):
            await self.service.resume(self.cookie)
        self.lease.revoke_authorization.assert_not_awaited()
        self.repository.revoke_authorization.assert_not_awaited()
        self.repository.forget_device.assert_not_awaited()

    async def test_invalid_grant_revokes_authorization_and_cannot_resume(self):
        self.lease.record = replace(self.lease.record, grant=replace(self.grant, expires_at=self.now))
        self.oauth.refresh_user_grant.side_effect = JiraLoginDenied("invalid grant")
        with self.assertRaises(JiraLoginDenied):
            await self.service.resume(self.cookie)
        self.lease.revoke_authorization.assert_awaited_once()
        self.oauth.validate_user_grant.assert_not_awaited()

    async def test_profile_denial_revokes_only_matching_authorization(self):
        self.oauth.validate_user_grant.side_effect = JiraLoginDenied("account inactive")
        with self.assertRaises(JiraLoginDenied):
            await self.service.resume(self.cookie)
        self.repository.revoke_authorization.assert_awaited_once_with(1, self.grant)
        self.repository.issue_session.assert_not_awaited()

    async def test_other_provider_identity_cannot_be_attached_to_remembered_device(self):
        self.oauth.validate_user_grant.return_value = replace(self.identity, username="jira:site:other")
        with self.assertRaises(JiraLoginDenied):
            await self.service.resume(self.cookie)
        self.profiles.register_identity.assert_not_awaited()
        self.repository.issue_session.assert_not_awaited()

    async def test_failed_profile_registration_preserves_rotated_token_but_does_not_issue_session(self):
        self.profiles.register_identity.side_effect = ValueError("unavailable")
        with self.assertRaises(JiraLoginDenied):
            await self.service.resume(self.cookie)
        self.repository.issue_session.assert_not_awaited()
        self.repository.revoke_authorization.assert_not_awaited()

    async def test_cancellation_after_refresh_waits_for_token_save(self):
        self.lease.record = replace(self.lease.record, grant=replace(self.grant, expires_at=self.now))
        self.oauth.refresh_user_grant.return_value = self.grant
        entered, release = asyncio.Event(), asyncio.Event()

        async def save(grant, now):
            entered.set()
            await release.wait()
            await self.save_grant(grant, now)

        self.lease.save_grant.side_effect = save
        task = asyncio.create_task(self.service.resume(self.cookie))
        await entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.grant, self.lease.record.grant)
        self.oauth.validate_user_grant.assert_not_awaited()

    async def test_notification_grant_rechecks_session_after_token_lookup(self):
        self.assertEqual(self.grant, await self.service.get(self.identity.jira_grant_id, self.identity))
        self.repository.resolve.return_value = None
        self.assertIsNone(await self.service.get(self.identity.jira_grant_id, self.identity))
        self.assertIsNone(await self.service.get("different", self.identity))
        self.assertIsNone(await self.service.get(self.identity.jira_grant_id, replace(self.identity, auth_provider="local")))

    async def test_logout_only_revokes_current_owned_session(self):
        await self.service.revoke("different", self.identity)
        self.repository.revoke_session.assert_not_awaited()
        await self.service.revoke(self.identity.jira_grant_id, self.identity)
        self.repository.revoke_session.assert_awaited_once_with(self.identity)
        self.repository.clear.assert_not_awaited()
        self.repository.forget_device.assert_not_awaited()

    async def test_invalid_cookie_never_queries_storage_or_provider(self):
        for cookie in ("", "invalid", "x" * 4096, " " * 43, None):
            self.assertFalse(await self.service.has_device(cookie))
            await self.service.forget(cookie)
            with self.assertRaises(JiraLoginDenied):
                await self.service.resume(cookie)
        self.repository.has_device.assert_not_awaited()
        self.repository.lease_authorization.assert_not_called()
        self.repository.forget_device.assert_not_awaited()

    async def test_unregistered_or_legacy_session_cannot_resolve(self):
        self.repository.resolve.return_value = None
        with self.assertRaises(JiraLoginDenied):
            await self.service.resolve(self.identity)
        with self.assertRaises(ValueError):
            await self.service.put(self.grant, self.identity)

    async def test_close_preserves_database_while_explicit_clear_deletes(self):
        await self.service.aclose()
        self.repository.clear.assert_not_awaited()
        self.assertFalse(await self.service.has_device(self.cookie))
        self.assertIsNone(await self.service.get(self.identity.jira_grant_id, self.identity))
        await self.service.clear()
        self.repository.clear.assert_awaited_once()


class JiraLoginCipherTest(unittest.TestCase):
    def test_session_lifetime_has_no_new_upper_limit_and_device_limit_is_ninety_days(self):
        JiraLoginService(Mock(), Mock(), Mock(), session_days=365, device_days=90)
        for kwargs in ({"session_days": 0}, {"session_days": True}, {"device_days": 91}, {"device_days": 0}):
            with self.assertRaises(ValueError):
                JiraLoginService(Mock(), Mock(), Mock(), **kwargs)

    def test_credentials_are_encrypted_and_isolated_from_owner_reporting_cipher(self):
        secret = "jira-login-test-only-server-secret-32-characters"
        cipher = JiraLoginCipher(secret)
        encrypted = cipher.encrypt("refresh-secret")
        self.assertNotIn("refresh-secret", encrypted)
        self.assertEqual("refresh-secret", cipher.decrypt(encrypted))
        with self.assertRaises(ValueError):
            PersonalDataCipher(secret).decrypt(encrypted)
        with self.assertRaises(ValueError):
            JiraLoginCipher(secret + "different").decrypt(encrypted)
        with self.assertRaises(ValueError):
            JiraLoginCipher("short")
