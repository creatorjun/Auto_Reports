# backend/src/infrastructure/persistence/jira_login_repository.py
import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert

from src.application.ports.jira_login_port import JiraLoginLeasePort, JiraLoginRecord, JiraLoginRepositoryPort
from src.application.ports.jira_oauth_port import JiraLoginDenied
from src.application.ports.jira_user_grant_port import JiraUserGrant
from src.domain.entities.auth_identity import AuthIdentity
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.jira_login_models import JiraLoginAuthorizationORM, JiraLoginDeviceORM, JiraLoginUserORM
from src.infrastructure.persistence.personal_data_models import PersonalDataAccountORM
from src.infrastructure.persistence.personal_data_suppression import lock_personal_data_writes
from src.infrastructure.security.jira_login_cipher import JiraLoginCipher


async def _commit(session) -> None:
    task = asyncio.create_task(session.commit())
    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            await task
        except Exception:
            pass
        raise


def _identity(user, profile, device) -> AuthIdentity:
    return AuthIdentity(
        f"jira:{user.cloud_id}:{user.account_id}", profile.display_name or "", "jira",
        int(device.session_expires_at.timestamp()) if device.session_expires_at is not None else None,
        profile.profile_version, device.session_id, profile.email_address,
    )


class _Lease(JiraLoginLeasePort):
    def __init__(self, session, cipher: JiraLoginCipher, record: JiraLoginRecord) -> None:
        self._session = session
        self._cipher = cipher
        self.record = record

    async def save_grant(self, grant: JiraUserGrant, now: datetime) -> None:
        if (grant.cloud_id, grant.account_id) != (self.record.grant.cloud_id, self.record.grant.account_id):
            raise JiraLoginDenied("Jira authorization identity does not match")
        await self._session.execute(update(JiraLoginAuthorizationORM).where(
            JiraLoginAuthorizationORM.user_id == self.record.user_id,
        ).values(
            access_token_encrypted=self._cipher.encrypt(grant.access_token),
            refresh_token_encrypted=self._cipher.encrypt(grant.refresh_token),
            expires_at=grant.expires_at, updated_at=now,
        ))
        await _commit(self._session)
        self.record = replace(self.record, grant=grant)

    async def revoke_authorization(self) -> None:
        await self._session.execute(delete(JiraLoginUserORM).where(JiraLoginUserORM.id == self.record.user_id))
        await _commit(self._session)


class JiraLoginRepository(JiraLoginRepositoryPort):
    def __init__(self, database: Database, server_secret: str) -> None:
        self._database = database
        self._cipher = JiraLoginCipher(server_secret)

    async def _record(self, session, *, now: datetime, device_hash: str | None, identity: AuthIdentity | None):
        if identity is not None and (identity.auth_provider != "jira" or not identity.jira_grant_id):
            return None
        predicate = JiraLoginDeviceORM.token_hash == device_hash if device_hash is not None else JiraLoginDeviceORM.session_id == identity.jira_grant_id
        found = (await session.execute(select(JiraLoginUserORM.id, JiraLoginUserORM.account_id, JiraLoginDeviceORM.token_hash).join(
            JiraLoginDeviceORM, JiraLoginDeviceORM.user_id == JiraLoginUserORM.id,
        ).where(predicate))).first()
        if found is None:
            return None
        profile = await session.get(PersonalDataAccountORM, found.account_id, with_for_update=True)
        user = await session.get(JiraLoginUserORM, found.id, with_for_update=True)
        if user is None:
            return None
        if profile is None or profile.status in {"closed", "pending_closed"}:
            await session.execute(delete(JiraLoginUserORM).where(JiraLoginUserORM.id == user.id))
            return None
        authorization = await session.get(JiraLoginAuthorizationORM, user.id, with_for_update=True)
        device = await session.get(JiraLoginDeviceORM, found.token_hash, with_for_update=True)
        if authorization is None or device is None or device.user_id != user.id:
            return None
        if device.expires_at <= now:
            await session.delete(device)
            return None
        if profile.status != "active" or device.profile_version != profile.profile_version:
            if device.session_id is not None:
                device.session_id = None
                device.session_expires_at = None
                device.generation += 1
        current = _identity(user, profile, device)
        if identity is not None and (
            current.username != identity.username or device.session_id != identity.jira_grant_id
            or device.session_expires_at is None or device.session_expires_at <= now
            or profile.status != "active" or not profile.display_name
            or profile.profile_version != identity.profile_version
            or current.session_expires_at != identity.session_expires_at
        ):
            return None
        try:
            grant = JiraUserGrant(
                user.cloud_id, user.account_id, self._cipher.decrypt(authorization.access_token_encrypted),
                authorization.expires_at, self._cipher.decrypt(authorization.refresh_token_encrypted),
            )
        except ValueError:
            await session.execute(delete(JiraLoginUserORM).where(JiraLoginUserORM.id == user.id))
            return None
        return JiraLoginRecord(user.id, device.token_hash, device.generation, current, grant)

    @asynccontextmanager
    async def lease_authorization(self, *, now: datetime, device_hash: str | None = None, identity: AuthIdentity | None = None):
        if (device_hash is None) == (identity is None):
            raise ValueError("Exactly one Jira login credential is required")
        async with self._database.session() as session:
            record = await self._record(session, now=now, device_hash=device_hash, identity=identity)
            yield _Lease(session, self._cipher, record) if record is not None else None

    async def _profile(self, session, grant: JiraUserGrant, identity: AuthIdentity):
        if identity.auth_provider != "jira" or identity.username != f"jira:{grant.cloud_id}:{grant.account_id}":
            raise JiraLoginDenied("Jira authorization identity does not match")
        await lock_personal_data_writes(session)
        profile = await session.get(PersonalDataAccountORM, grant.account_id, with_for_update=True)
        if profile is None or profile.status != "active" or not profile.display_name or profile.profile_version != identity.profile_version:
            raise JiraLoginDenied("Jira profile is unavailable")
        return profile

    async def finish_login(self, grant, identity, *, device_hash, previous_device_hash, session_id, now, session_expires_at, device_expires_at):
        async with self._database.session() as session:
            profile = await self._profile(session, grant, identity)
            await session.execute(insert(JiraLoginUserORM).values(
                cloud_id=grant.cloud_id, account_id=grant.account_id, created_at=now, last_login_at=now,
            ).on_conflict_do_nothing(constraint="uq_jira_login_user_identity"))
            user = (await session.execute(select(JiraLoginUserORM).where(
                JiraLoginUserORM.cloud_id == grant.cloud_id, JiraLoginUserORM.account_id == grant.account_id,
            ).with_for_update())).scalar_one()
            user.last_login_at = now
            authorization = await session.get(JiraLoginAuthorizationORM, user.id, with_for_update=True)
            values = dict(
                access_token_encrypted=self._cipher.encrypt(grant.access_token),
                refresh_token_encrypted=self._cipher.encrypt(grant.refresh_token),
                expires_at=grant.expires_at, updated_at=now,
            )
            if authorization is None:
                session.add(JiraLoginAuthorizationORM(user_id=user.id, **values))
            else:
                for key, value in values.items():
                    setattr(authorization, key, value)
            if previous_device_hash is not None:
                await session.execute(delete(JiraLoginDeviceORM).where(JiraLoginDeviceORM.token_hash == previous_device_hash))
            device = JiraLoginDeviceORM(
                token_hash=device_hash, user_id=user.id, expires_at=device_expires_at, last_used_at=now,
                session_id=session_id, session_expires_at=session_expires_at, profile_version=profile.profile_version,
                generation=1,
            )
            session.add(device)
            result = _identity(user, profile, device)
            await _commit(session)
            return result

    async def issue_session(self, record, identity, *, session_id, now, session_expires_at, device_expires_at):
        async with self._database.session() as session:
            profile = await self._profile(session, record.grant, identity)
            user = await session.get(JiraLoginUserORM, record.user_id, with_for_update=True)
            authorization = await session.get(JiraLoginAuthorizationORM, record.user_id, with_for_update=True)
            device = await session.get(JiraLoginDeviceORM, record.device_hash, with_for_update=True)
            if user is None or authorization is None or device is None or device.user_id != record.user_id or device.generation != record.generation or device.expires_at <= now or identity.profile_version != record.identity.profile_version:
                raise JiraLoginDenied("Remembered Jira login is no longer available")
            device.session_id = session_id
            device.session_expires_at = session_expires_at
            device.profile_version = profile.profile_version
            device.expires_at = device_expires_at
            device.last_used_at = now
            device.generation += 1
            user.last_login_at = now
            return _identity(user, profile, device)

    async def resolve(self, identity: AuthIdentity, now: datetime) -> AuthIdentity | None:
        if identity.auth_provider != "jira" or not identity.jira_grant_id:
            return None
        async with self._database.session() as session:
            row = (await session.execute(select(JiraLoginUserORM, PersonalDataAccountORM, JiraLoginDeviceORM).join(
                PersonalDataAccountORM, PersonalDataAccountORM.account_id == JiraLoginUserORM.account_id,
            ).join(JiraLoginAuthorizationORM, JiraLoginAuthorizationORM.user_id == JiraLoginUserORM.id).join(
                JiraLoginDeviceORM, JiraLoginDeviceORM.user_id == JiraLoginUserORM.id,
            ).where(
                JiraLoginDeviceORM.session_id == identity.jira_grant_id,
                JiraLoginDeviceORM.expires_at > now, JiraLoginDeviceORM.session_expires_at > now,
                PersonalDataAccountORM.status == "active", PersonalDataAccountORM.display_name.is_not(None),
                PersonalDataAccountORM.display_name != "",
                PersonalDataAccountORM.profile_version == identity.profile_version,
                JiraLoginDeviceORM.profile_version == PersonalDataAccountORM.profile_version,
            ))).first()
            if row is None:
                return None
            current = _identity(*row)
            return current if current.username == identity.username and current.session_expires_at == identity.session_expires_at else None

    async def has_device(self, device_hash: str, now: datetime) -> bool:
        async with self._database.session() as session:
            row = (await session.execute(select(JiraLoginDeviceORM.token_hash).join(
                JiraLoginUserORM, JiraLoginUserORM.id == JiraLoginDeviceORM.user_id,
            ).join(PersonalDataAccountORM, PersonalDataAccountORM.account_id == JiraLoginUserORM.account_id).join(
                JiraLoginAuthorizationORM, JiraLoginAuthorizationORM.user_id == JiraLoginUserORM.id,
            ).where(
                JiraLoginDeviceORM.token_hash == device_hash, JiraLoginDeviceORM.expires_at > now,
                PersonalDataAccountORM.status.not_in(("closed", "pending_closed")),
            ))).first()
            return row is not None

    async def revoke_session(self, identity: AuthIdentity) -> None:
        if identity.auth_provider != "jira" or not identity.jira_grant_id:
            return
        async with self._database.session() as session:
            owners = select(JiraLoginUserORM.id).where(
                ("jira:" + JiraLoginUserORM.cloud_id + ":" + JiraLoginUserORM.account_id) == identity.username,
            )
            await session.execute(update(JiraLoginDeviceORM).where(
                JiraLoginDeviceORM.user_id.in_(owners), JiraLoginDeviceORM.session_id == identity.jira_grant_id,
            ).values(session_id=None, session_expires_at=None, generation=JiraLoginDeviceORM.generation + 1))

    async def forget_device(self, device_hash: str) -> None:
        async with self._database.session() as session:
            await session.execute(delete(JiraLoginDeviceORM).where(JiraLoginDeviceORM.token_hash == device_hash))

    async def revoke_authorization(self, user_id: int, expected_grant: JiraUserGrant) -> None:
        async with self._database.session() as session:
            await session.get(PersonalDataAccountORM, expected_grant.account_id, with_for_update=True)
            user = await session.get(JiraLoginUserORM, user_id, with_for_update=True)
            authorization = await session.get(JiraLoginAuthorizationORM, user_id, with_for_update=True)
            if user is not None and authorization is not None and (
                user.cloud_id == expected_grant.cloud_id and user.account_id == expected_grant.account_id
                and self._cipher.decrypt(authorization.refresh_token_encrypted) == expected_grant.refresh_token
            ):
                await session.delete(user)

    async def reconcile_privacy(self) -> None:
        async with self._database.session() as session:
            await lock_personal_data_writes(session)
            profiles = (await session.execute(select(PersonalDataAccountORM).where(
                PersonalDataAccountORM.account_id.in_(select(JiraLoginUserORM.account_id)),
            ).order_by(PersonalDataAccountORM.account_id).with_for_update())).scalars().all()
            for profile in profiles:
                owners = select(JiraLoginUserORM.id).where(JiraLoginUserORM.account_id == profile.account_id)
                if profile.status in {"closed", "pending_closed"}:
                    await session.execute(delete(JiraLoginUserORM).where(JiraLoginUserORM.account_id == profile.account_id))
                else:
                    conditions = [JiraLoginDeviceORM.user_id.in_(owners), JiraLoginDeviceORM.session_id.is_not(None)]
                    if profile.status == "active":
                        conditions.append(JiraLoginDeviceORM.profile_version != profile.profile_version)
                    await session.execute(update(JiraLoginDeviceORM).where(*conditions).values(
                        session_id=None, session_expires_at=None, generation=JiraLoginDeviceORM.generation + 1,
                    ))

    async def clear(self) -> None:
        async with self._database.session() as session:
            await session.execute(delete(JiraLoginUserORM))
