# backend/tests/test_jira_login_repository.py
import asyncio
import hashlib
import os
import unittest
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from sqlalchemy import delete, select, update

from src.application.ports.jira_oauth_port import JiraLoginDenied, JiraLoginUnavailable, JiraOAuthPort
from src.application.ports.jira_user_grant_port import JiraUserGrant
from src.application.services.jira_login_service import JiraLoginService
from src.domain.entities.auth_identity import AuthIdentity
from src.domain.entities.personal_data import PersonalDataAction
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.jira_login_models import JiraLoginAuthorizationORM, JiraLoginDeviceORM, JiraLoginUserORM
from src.infrastructure.persistence.jira_login_repository import JiraLoginRepository
from src.infrastructure.persistence.personal_data_models import PersonalDataAccountORM
from src.infrastructure.persistence.personal_data_repository import PersonalDataRepository

DATABASE_URL = os.environ.get("JIRA_LOGIN_TEST_DATABASE_URL")
SECRET = "jira-login-database-test-only-secret-32-characters"


@unittest.skipUnless(DATABASE_URL, "Requires isolated PostgreSQL JIRA_LOGIN_TEST_DATABASE_URL")
class JiraLoginRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.database = Database(DATABASE_URL)
        self.profiles = PersonalDataRepository(self.database, SECRET, "login-test-owner")
        self.repository = JiraLoginRepository(self.database, SECRET)
        self.oauth = AsyncMock(spec=JiraOAuthPort)
        self.account_ids = []
        self.identity, self.grant = await self.account()
        self.oauth.validate_user_grant.side_effect = lambda grant: AuthIdentity(f"jira:{grant.cloud_id}:{grant.account_id}", "최신 이름", "jira", email_address="verified@example.com")
        self.oauth.refresh_user_grant.side_effect = lambda grant: replace(grant, access_token="rotated-access", refresh_token="rotated-refresh", expires_at=self.now + timedelta(hours=1))
        self.service = JiraLoginService(self.repository, self.oauth, self.profiles, clock=lambda: self.now)
        self.session, self.cookie = await self.service.finish_login(self.grant, self.identity)

    async def asyncTearDown(self):
        await self.service.aclose()
        async with self.database.session() as session:
            await session.execute(delete(PersonalDataAccountORM).where(PersonalDataAccountORM.account_id.in_(self.account_ids)))
        await self.database.aclose()

    async def account(self):
        account_id = "login-test-" + uuid.uuid4().hex
        self.account_ids.append(account_id)
        identity = await self.profiles.register_identity(AuthIdentity(f"jira:site:{account_id}", "사용자", "jira", email_address="initial@example.com"))
        return identity, JiraUserGrant("site", account_id, "original-access", self.now + timedelta(hours=1), "original-refresh")

    async def stored(self):
        async with self.database.session() as session:
            user = (await session.execute(select(JiraLoginUserORM).where(JiraLoginUserORM.account_id == self.grant.account_id))).scalar_one_or_none()
            if user is None:
                return None, None, []
            authorization = await session.get(JiraLoginAuthorizationORM, user.id)
            devices = (await session.execute(select(JiraLoginDeviceORM).where(JiraLoginDeviceORM.user_id == user.id))).scalars().all()
            return user, authorization, devices

    async def test_storage_contains_ciphertext_and_hashed_cookie_only(self):
        user, authorization, devices = await self.stored()
        self.assertEqual(self.grant.account_id, user.account_id)
        self.assertNotIn(self.grant.access_token, authorization.access_token_encrypted)
        self.assertNotIn(self.grant.refresh_token, authorization.refresh_token_encrypted)
        self.assertEqual(self.grant.refresh_token, self.repository._cipher.decrypt(authorization.refresh_token_encrypted))
        self.assertEqual(hashlib.sha256(self.cookie.encode()).hexdigest(), devices[0].token_hash)
        self.assertNotEqual(self.cookie, devices[0].session_id)
        self.assertEqual(1, len(devices))

    async def test_service_restart_preserves_connection_and_app_session(self):
        await self.service.aclose()
        self.service = JiraLoginService(JiraLoginRepository(self.database, SECRET), self.oauth, self.profiles, clock=lambda: self.now)
        self.assertEqual(self.session, await self.service.resolve(self.session))
        self.assertTrue(await self.service.has_device(self.cookie))
        self.assertEqual(self.grant, await self.service.get(self.session.jira_grant_id, self.session))

    async def test_logout_retains_connection_but_old_jwt_session_cannot_resolve(self):
        await self.service.revoke(self.session.jira_grant_id, self.session)
        self.assertTrue(await self.service.has_device(self.cookie))
        self.assertIsNone(await self.service.get(self.session.jira_grant_id, self.session))
        with self.assertRaises(JiraLoginDenied):
            await self.service.resolve(self.session)
        resumed = await self.service.resume(self.cookie)
        self.assertNotEqual(self.session.jira_grant_id, resumed.jira_grant_id)
        self.assertEqual("최신 이름", resumed.display_name)
        self.assertEqual("verified@example.com", resumed.email_address)
        self.assertEqual(resumed, await self.service.resolve(resumed))

    async def test_session_expiry_requires_verified_resume_and_extends_device_inactivity(self):
        self.now += timedelta(days=8)
        with self.assertRaises(JiraLoginDenied):
            await self.service.resolve(self.session)
        self.assertTrue(await self.service.has_device(self.cookie))
        resumed = await self.service.resume(self.cookie)
        self.assertEqual(int((self.now + timedelta(days=7)).timestamp()), resumed.session_expires_at)
        _, _, devices = await self.stored()
        self.assertEqual(self.now + timedelta(days=90), devices[0].expires_at)
        self.oauth.validate_user_grant.assert_awaited_once()

    async def test_device_expiry_prevents_token_refresh_and_resume(self):
        self.now += timedelta(days=90)
        self.assertFalse(await self.service.has_device(self.cookie))
        with self.assertRaises(JiraLoginDenied):
            await self.service.resume(self.cookie)
        self.oauth.refresh_user_grant.assert_not_awaited()
        self.oauth.validate_user_grant.assert_not_awaited()

    async def test_cross_user_and_cross_site_identity_cannot_use_session(self):
        for username in ("jira:site:another", f"jira:other-site:{self.grant.account_id}"):
            forged = replace(self.session, username=username)
            self.assertIsNone(await self.service.get(self.session.jira_grant_id, forged))
            await self.service.revoke(self.session.jira_grant_id, forged)
        self.assertEqual(self.grant, await self.service.get(self.session.jira_grant_id, self.session))

    async def test_empty_canonical_profile_name_cannot_resolve_app_session(self):
        async with self.database.session() as session:
            await session.execute(update(PersonalDataAccountORM).where(
                PersonalDataAccountORM.account_id == self.grant.account_id,
            ).values(display_name=""))
        with self.assertRaises(JiraLoginDenied):
            await self.service.resolve(self.session)

    async def test_two_expired_grant_requests_refresh_once_under_database_lock(self):
        self.now += timedelta(hours=1)
        entered, release = asyncio.Event(), asyncio.Event()
        rotated = replace(self.grant, access_token="rotated", refresh_token="rotated-refresh", expires_at=self.now + timedelta(hours=1))

        async def refresh(grant):
            entered.set()
            await release.wait()
            return rotated

        self.oauth.refresh_user_grant.side_effect = refresh
        first = asyncio.create_task(self.service.get(self.session.jira_grant_id, self.session))
        await entered.wait()
        second = asyncio.create_task(self.service.get(self.session.jira_grant_id, self.session))
        await asyncio.sleep(0)
        release.set()
        self.assertEqual([rotated, rotated], await asyncio.wait_for(asyncio.gather(first, second), 5))
        self.oauth.refresh_user_grant.assert_awaited_once()

    async def test_normal_session_resolution_does_not_wait_for_network_token_refresh(self):
        self.now += timedelta(hours=1)
        entered, release = asyncio.Event(), asyncio.Event()

        async def refresh(grant):
            entered.set()
            await release.wait()
            return replace(grant, access_token="rotated", refresh_token="new-refresh", expires_at=self.now + timedelta(hours=1))

        self.oauth.refresh_user_grant.side_effect = refresh
        task = asyncio.create_task(self.service.get(self.session.jira_grant_id, self.session))
        await entered.wait()
        try:
            self.assertEqual(self.session, await asyncio.wait_for(self.service.resolve(self.session), 1))
            self.assertTrue(await asyncio.wait_for(self.service.has_device(self.cookie), 1))
        finally:
            release.set()
            await asyncio.wait_for(task, 5)

    async def test_rotated_token_is_committed_even_when_later_validation_fails(self):
        self.now += timedelta(hours=1)
        self.oauth.validate_user_grant.side_effect = JiraLoginUnavailable("temporary failure")
        with self.assertRaises(JiraLoginUnavailable):
            await self.service.resume(self.cookie)
        _, authorization, devices = await self.stored()
        self.assertEqual("rotated-refresh", self.repository._cipher.decrypt(authorization.refresh_token_encrypted))
        self.assertEqual(self.session.jira_grant_id, devices[0].session_id)
        self.oauth.validate_user_grant.side_effect = lambda grant: self.identity
        await self.service.resume(self.cookie)
        self.oauth.refresh_user_grant.assert_awaited_once()

    async def test_invalid_refresh_revokes_credentials_and_devices_but_keeps_privacy_account(self):
        self.now += timedelta(hours=1)
        self.oauth.refresh_user_grant.side_effect = JiraLoginDenied("invalid grant")
        self.assertIsNone(await self.service.get(self.session.jira_grant_id, self.session))
        self.assertEqual((None, None, []), await self.stored())
        async with self.database.session() as session:
            self.assertIsNotNone(await session.get(PersonalDataAccountORM, self.grant.account_id))

    async def test_transient_refresh_failure_keeps_original_authorization(self):
        self.now += timedelta(hours=1)
        self.oauth.refresh_user_grant.side_effect = JiraLoginUnavailable("temporary failure")
        with self.assertRaises(JiraLoginUnavailable):
            await self.service.get(self.session.jira_grant_id, self.session)
        _, authorization, devices = await self.stored()
        self.assertEqual(self.grant.refresh_token, self.repository._cipher.decrypt(authorization.refresh_token_encrypted))
        self.assertEqual(self.session.jira_grant_id, devices[0].session_id)

    async def _resume_race(self, operation):
        entered, release = asyncio.Event(), asyncio.Event()

        async def validate(grant):
            entered.set()
            await release.wait()
            return self.identity

        self.oauth.validate_user_grant.side_effect = validate
        task = asyncio.create_task(self.service.resume(self.cookie))
        await entered.wait()
        try:
            await operation()
        finally:
            release.set()
        with self.assertRaises(JiraLoginDenied):
            await asyncio.wait_for(task, 5)

    async def test_logout_during_resume_cannot_be_undone_by_late_session_issue(self):
        await self._resume_race(lambda: self.service.revoke(self.session.jira_grant_id, self.session))
        self.assertIsNone(await self.service.get(self.session.jira_grant_id, self.session))
        self.assertTrue(await self.service.has_device(self.cookie))

    async def test_forget_during_resume_cannot_recreate_device(self):
        await self._resume_race(lambda: self.service.forget(self.cookie))
        self.assertFalse(await self.service.has_device(self.cookie))

    async def test_privacy_version_change_during_resume_is_rejected_without_callback(self):
        async def change():
            async with self.database.session() as session:
                await session.execute(update(PersonalDataAccountORM).where(PersonalDataAccountORM.account_id == self.grant.account_id).values(profile_version=2))

        await self._resume_race(change)

    async def test_updated_profile_revokes_session_but_keeps_verified_resume_available(self):
        action = PersonalDataAction(self.grant.account_id, "updated")
        await self.profiles.stage_actions((action,))
        await self.profiles.finish_actions((action,))
        await self.service.reconcile_privacy()
        self.assertIsNone(await self.service.get(self.session.jira_grant_id, self.session))
        self.assertTrue(await self.service.has_device(self.cookie))
        resumed = await self.service.resume(self.cookie)
        self.assertEqual(2, resumed.profile_version)
        self.assertEqual("최신 이름", resumed.display_name)

    async def test_pending_closed_is_rejected_even_before_cleanup_callback(self):
        await self.profiles.stage_actions((PersonalDataAction(self.grant.account_id, "closed"),))
        self.assertIsNone(await self.service.get(self.session.jira_grant_id, self.session))
        self.assertFalse(await self.service.has_device(self.cookie))
        self.assertEqual((None, None, []), await self.stored())
        self.oauth.refresh_user_grant.assert_not_awaited()

    async def test_closed_profile_reconcile_removes_all_login_records(self):
        await self.profiles.stage_actions((PersonalDataAction(self.grant.account_id, "closed"),))
        await self.service.reconcile_privacy()
        self.assertEqual((None, None, []), await self.stored())

    async def test_account_switch_replaces_previous_device_only(self):
        identity, grant = await self.account()
        new_session, new_cookie = await self.service.finish_login(grant, identity, self.cookie)
        self.assertFalse(await self.service.has_device(self.cookie))
        self.assertTrue(await self.service.has_device(new_cookie))
        self.assertIsNone(await self.service.get(self.session.jira_grant_id, self.session))
        self.assertEqual(grant, await self.service.get(new_session.jira_grant_id, new_session))

    async def test_stale_provider_denial_does_not_revoke_new_oauth_authorization(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def deny(grant):
            entered.set()
            await release.wait()
            raise JiraLoginDenied("old authorization denied")

        self.oauth.validate_user_grant.side_effect = deny
        task = asyncio.create_task(self.service.resume(self.cookie))
        await entered.wait()
        updated = replace(self.grant, access_token="new-access", refresh_token="new-consent-refresh")
        new_session, new_cookie = await self.service.finish_login(updated, self.identity)
        release.set()
        with self.assertRaises(JiraLoginDenied):
            await task
        self.assertTrue(await self.service.has_device(new_cookie))
        self.assertEqual(updated, await self.service.get(new_session.jira_grant_id, new_session))
