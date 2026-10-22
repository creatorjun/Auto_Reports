# backend/src/infrastructure/persistence/audit_log_user_profiles.py
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from src.application.ports.audit_log_reader_port import AuditLogReadError
from src.application.ports.audit_log_user_profile_port import AuditLogUserProfilePort
from src.domain.entities.audit_log import AuditLogUserProfile
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.personal_data_models import PersonalDataAccountORM


class SqlAuditLogUserProfiles(AuditLogUserProfilePort):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def read_profiles(self) -> dict[str, AuditLogUserProfile]:
        try:
            async with self._database.session() as session:
                result = await session.execute(select(
                    PersonalDataAccountORM.account_id,
                    PersonalDataAccountORM.display_name,
                    PersonalDataAccountORM.email_address,
                ).where(PersonalDataAccountORM.status == "active"))
                return {
                    row.account_id: AuditLogUserProfile(
                        row.display_name.strip() or None if row.display_name else None,
                        row.email_address.strip() or None if row.email_address else None,
                    )
                    for row in result
                }
        except (SQLAlchemyError, OSError) as error:
            raise AuditLogReadError("감사 로그의 사용자 정보를 읽을 수 없습니다. 잠시 후 다시 조회해 주세요.") from error
