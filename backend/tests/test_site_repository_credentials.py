# backend/tests/test_site_repository_credentials.py
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.infrastructure.persistence.site_models import AccessCredentialsORM
from src.infrastructure.persistence.site_repository_impl import SiteRepositoryImpl
from src.presentation.mappers.site_mapper import creds_from_schema, creds_to_schema
from src.presentation.schemas.site_schema import AccessCredentialsSchema


class SiteRepositoryCredentialsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = SiteRepositoryImpl(None)

    def test_restores_each_connection_type_when_any_field_is_present(self) -> None:
        orm = AccessCredentialsORM(
            cli_username="admin",
            cli_password="secret",
            web_port="443",
            db_ip="10.0.0.20",
            db_port="5432",
            vpn_password="vpn-secret",
        )

        credentials = self.repository._creds_to_domain(orm)

        self.assertEqual("admin", credentials.cli.username)
        self.assertEqual("secret", credentials.cli.password)
        self.assertEqual("443", credentials.web.port)
        self.assertEqual("10.0.0.20", credentials.db.ip)
        self.assertEqual("5432", credentials.db.port)
        self.assertEqual("vpn-secret", credentials.vpn.password)

    def test_omits_connection_type_only_when_all_fields_are_empty(self) -> None:
        orm = AccessCredentialsORM(cli_username="admin", cli_password="secret")

        credentials = self.repository._creds_to_domain(orm)

        self.assertIsNotNone(credentials.cli)
        self.assertIsNone(credentials.web)
        self.assertIsNone(credentials.db)
        self.assertIsNone(credentials.vpn)

    def test_partial_connection_type_is_valid_api_data(self) -> None:
        request = AccessCredentialsSchema.model_validate(
            {"db": {"ip": "db.internal", "port": "5432"}}
        )

        response = creds_to_schema(creds_from_schema(request))

        self.assertIsNotNone(response.db)
        self.assertIsNone(response.db.username)
        self.assertIsNone(response.db.password)
        self.assertEqual("db.internal", response.db.ip)
        self.assertEqual("5432", response.db.port)


if __name__ == "__main__":
    unittest.main()
