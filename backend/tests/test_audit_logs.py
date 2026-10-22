# backend/tests/test_audit_logs.py
import json
import logging
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.application.ports.audit_log_reader_port import AuditLogReadError
from src.application.use_cases.audit_logs import AuditLogsUseCase
from src.domain.entities.audit_log import AuditLogPage, AuditLogQuery, AuditLogUserProfile
from src.infrastructure.logging.audit_log_reader import FileAuditLogReader
from src.infrastructure.logging.audit_logger import AuditLogger


def legacy(timestamp: str, event: str, fields: str = "") -> str:
    return f"{timestamp} [AUDIT] {event}{' | ' + fields if fields else ''}\n"


def structured(timestamp: str, event: str, **fields: object) -> str:
    return f"2026-10-13 00:00:00 [AUDIT] {json.dumps({'timestamp': timestamp, 'event': event, 'fields': fields})}\n"


class AuditLogReaderTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)
        self.reader = FileAuditLogReader(self.directory.name)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def write(self, content: str, name: str = "audit.log") -> None:
        (self.path / name).write_text(content, encoding="utf-8")

    async def test_old_and_rotated_records_are_paginated_by_timestamp(self) -> None:
        self.write(legacy("2026-10-11 23:59:59", "REPORT_DELETE", "report_id=1"), "audit.log.2026-10-11")
        self.write(legacy("2026-10-12 12:00:00", "REPORT_DELETE", "username=admin | report_id=2") + structured("2026-10-13T09:00:00+09:00", "LOGIN_SUCCESS", username="root", ip="127.0.0.1"))
        self.write(legacy("2026-10-14 00:00:00", "IGNORED"), "application.log")
        page = await self.reader.read(AuditLogQuery(limit=1, offset=1))
        self.assertEqual(3, page.total)
        self.assertEqual(["LOGIN_SUCCESS", "REPORT_DELETE"], page.events)
        self.assertEqual("2", page.items[0].details["report_id"])
        self.assertEqual("admin", page.items[0].username)
        self.assertIsNone(page.items[0].ip)
        last = await self.reader.read(AuditLogQuery(limit=1, offset=2))
        self.assertIsNone(last.items[0].username)
        self.assertTrue(any("사용자 정보" in warning for warning in last.warnings))

    async def test_dates_use_kst_inclusive_day_boundaries(self) -> None:
        self.write(structured("2026-10-12T14:59:59+00:00", "BEFORE") + structured("2026-10-12T15:00:00+00:00", "START") + structured("2026-10-13T14:59:59+00:00", "END") + structured("2026-10-13T15:00:00+00:00", "AFTER"))
        page = await self.reader.read(AuditLogQuery(start_date=date(2026, 10, 13), end_date=date(2026, 10, 13)))
        self.assertEqual(["END", "START"], [entry.event for entry in page.items])
        self.assertTrue(all(entry.timestamp.endswith("+09:00") for entry in page.items))

    async def test_filters_combine_and_do_not_search_redacted_secrets(self) -> None:
        self.write(legacy("2026-10-13 09:00:00", "FILE_DELETE", "username=admin | ip=192.168.1.20 | path=report/계획.xlsx | password=HIDDEN") + structured("2026-10-13T10:00:00+09:00", "FILE_DELETE", username="root", ip="127.0.0.1", path="other.xlsx"))
        page = await self.reader.read(AuditLogQuery(event="file_delete", username="ADM", ip="168.1", search="계획"))
        self.assertEqual(1, page.total)
        self.assertEqual("[REDACTED]", page.items[0].details["password"])
        self.assertEqual(0, (await self.reader.read(AuditLogQuery(search="HIDDEN"))).total)

    async def test_incomplete_or_invalid_records_are_visible_as_warnings(self) -> None:
        self.write("invalid\n" + legacy("2026-10-13 10:00:00", "GOOD") + "2026-10-13 10:00:01 [AUDIT] PARTIAL")
        page = await self.reader.read(AuditLogQuery())
        self.assertEqual(1, page.total)
        self.assertEqual("GOOD", page.items[0].event)
        self.assertTrue(any("형식" in warning for warning in page.warnings))
        self.assertTrue(any("마지막 줄" in warning for warning in page.warnings))
        with (self.path / "audit.log").open("a", encoding="utf-8") as stream:
            stream.write("\n")
        self.assertEqual(2, (await self.reader.read(AuditLogQuery())).total)

    async def test_same_second_order_is_stable_across_current_and_rotated_files(self) -> None:
        self.write(legacy("2026-10-13 00:00:00", "OLD"), "audit.log.2026-10-12")
        self.write(legacy("2026-10-13 00:00:00", "FIRST") + legacy("2026-10-13 00:00:00", "SECOND"))
        page = await self.reader.read(AuditLogQuery())
        self.assertEqual(["SECOND", "FIRST", "OLD"], [entry.event for entry in page.items])

    async def test_missing_logs_are_distinct_from_unreadable_logs(self) -> None:
        self.assertEqual(0, (await self.reader.read(AuditLogQuery())).total)
        with patch.object(Path, "iterdir", side_effect=PermissionError("secret server location")):
            with self.assertRaises(AuditLogReadError) as context:
                await self.reader.read(AuditLogQuery())
        self.assertNotIn("secret server location", str(context.exception))
        self.write(legacy("2026-10-13 10:00:00", "EVENT"))
        with patch.object(Path, "open", side_effect=PermissionError("denied")):
            with self.assertRaises(AuditLogReadError):
                await self.reader.read(AuditLogQuery())

    async def test_rotation_race_retries_with_a_new_file_inventory(self) -> None:
        self.write(legacy("2026-10-13 10:00:00", "EVENT"))
        original = self.reader._scan
        calls = 0

        def scan(query: AuditLogQuery, profiles=None) -> AuditLogPage:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise FileNotFoundError()
            return original(query, profiles)

        with patch.object(self.reader, "_scan", side_effect=scan):
            self.assertEqual(1, (await self.reader.read(AuditLogQuery())).total)
        self.assertEqual(2, calls)

    async def test_rotation_between_file_inventory_and_open_preserves_both_files(self) -> None:
        self.write(legacy("2026-10-12 23:59:59", "OLD"))
        original_open = Path.open
        rotated = False

        def open_file(path: Path, *args: object, **kwargs: object):
            nonlocal rotated
            if path == self.path / "audit.log" and not rotated:
                rotated = True
                path.rename(self.path / "audit.log.2026-10-12")
                with original_open(path, "w", encoding="utf-8") as stream:
                    stream.write(legacy("2026-10-13 00:00:00", "NEW"))
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", open_file):
            page = await self.reader.read(AuditLogQuery())
        self.assertEqual(["NEW", "OLD"], [entry.event for entry in page.items])

    async def test_invalid_utf8_and_oversized_lines_do_not_hide_later_records(self) -> None:
        (self.path / "audit.log").write_bytes(b"\xff\n" + b"x" * 300000 + b"\n" + legacy("2026-10-13 10:00:00", "GOOD").encode())
        page = await self.reader.read(AuditLogQuery())
        self.assertEqual(["GOOD"], [entry.event for entry in page.items])
        self.assertTrue(any("길이 제한" in warning for warning in page.warnings))

    async def test_jira_profiles_resolve_old_and_new_records_without_rewriting_logs(self) -> None:
        old = legacy("2026-10-12 09:00:00", "REPORT_DELETE", "username=jira:site:account:123 | report_id=1")
        current = structured("2026-10-13T10:00:00+09:00", "FILE_DELETE", username="jira:site:account:123", path="report.xlsx")
        self.write(old, "audit.log.2026-10-12")
        self.write(current)
        profiles = {"account:123": AuditLogUserProfile("홍길동", "hong@example.com")}
        page = await self.reader.read(AuditLogQuery(), profiles)
        self.assertEqual(2, page.total)
        for entry in page.items:
            self.assertEqual("jira:site:account:123", entry.username)
            self.assertEqual("홍길동", entry.display_name)
            self.assertEqual("hong@example.com", entry.email_address)
        self.assertEqual(old, (self.path / "audit.log.2026-10-12").read_text(encoding="utf-8"))
        self.assertEqual(current, (self.path / "audit.log").read_text(encoding="utf-8"))

    async def test_user_name_email_and_original_identity_filter_before_pagination(self) -> None:
        self.write("".join(structured(
            f"2026-10-13T{hour}:00:00+09:00", "FILE_DELETE", username=f"jira:site:{account}", path=str(hour),
        ) for hour, account in (("09", "known"), ("10", "other"), ("11", "known"))))
        profiles = {"known": AuditLogUserProfile("홍길동", "Hong@example.com")}
        for field in ("username", "search"):
            for value in ("홍길동", "HONG@EXAMPLE.COM", "홍길동 / Hong@example.com", "jira:site:known"):
                with self.subTest(field=field, value=value):
                    page = await self.reader.read(AuditLogQuery(**{field: value}, limit=1, offset=1), profiles)
                    self.assertEqual(2, page.total)
                    self.assertEqual(["09"], [entry.details["path"] for entry in page.items])

    async def test_missing_profiles_and_local_users_do_not_inherit_jira_names(self) -> None:
        self.write("".join(structured("2026-10-13T10:00:00+09:00", "LOGIN_SUCCESS", username=value) for value in (
            "root", "jira:site:unknown", "jira::known", "jira:known", "jira:site:email-only",
        )))
        profiles = {
            "root": AuditLogUserProfile("다른 사용자", "other@example.com"),
            "known": AuditLogUserProfile("확인된 사용자", "known@example.com"),
            "email-only": AuditLogUserProfile(email_address="email@example.com"),
        }
        page = await self.reader.read(AuditLogQuery(), profiles)
        for entry in page.items:
            self.assertIsNone(entry.display_name)
            self.assertEqual("email@example.com" if entry.username.endswith("email-only") else None, entry.email_address)

    async def test_profile_removal_hides_previously_resolved_personal_data(self) -> None:
        self.write(structured("2026-10-13T10:00:00+09:00", "REPORT_DELETE", username="jira:site:known"))
        profiles = {"known": AuditLogUserProfile("홍길동", "hong@example.com")}
        self.assertEqual(1, (await self.reader.read(AuditLogQuery(search="hong@example.com"), profiles)).total)
        self.assertEqual(0, (await self.reader.read(AuditLogQuery(search="hong@example.com"), {})).total)
        entry = (await self.reader.read(AuditLogQuery(), {})).items[0]
        self.assertIsNone(entry.display_name)
        self.assertIsNone(entry.email_address)

    async def test_failed_login_input_is_not_attributed_to_an_authenticated_jira_user(self) -> None:
        self.write("".join(structured("2026-10-13T10:00:00+09:00", event, username="jira:site:known") for event in ("LOGIN_FAILED", "LOGIN_FAIL")))
        profiles = {"known": AuditLogUserProfile("홍길동", "hong@example.com")}
        page = await self.reader.read(AuditLogQuery(), profiles)
        self.assertEqual(2, page.total)
        for entry in page.items:
            self.assertEqual("jira:site:known", entry.username)
            self.assertIsNone(entry.display_name)
            self.assertIsNone(entry.email_address)
        self.assertEqual(0, (await self.reader.read(AuditLogQuery(username="홍길동"), profiles)).total)
        self.assertEqual(0, (await self.reader.read(AuditLogQuery(search="hong@example.com"), profiles)).total)

    async def test_account_id_fallback_is_not_exposed_as_a_display_name(self) -> None:
        self.write(structured("2026-10-13T10:00:00+09:00", "LOGIN_SUCCESS", username="jira:site:known"))
        profiles = {"known": AuditLogUserProfile("known", "hong@example.com")}
        entry = (await self.reader.read(AuditLogQuery(), profiles)).items[0]
        self.assertIsNone(entry.display_name)
        self.assertEqual("hong@example.com", entry.email_address)


class AuditLoggerTest(unittest.IsolatedAsyncioTestCase):
    async def test_new_records_round_trip_without_secrets_or_newline_injection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            isolated_logger = logging.Logger("isolated-audit-test")
            with patch("src.infrastructure.logging.audit_logger.logging.getLogger", return_value=isolated_logger):
                logger = AuditLogger(directory)
                logger.record("LOGIN_FAILURE", username="root\nforged", ip="127.0.0.1", password="DO_NOT_LOG", api_token="ALSO_SECRET", nested=[{"password": "NESTED_SECRET"}], path="/download?token=QUERY_SECRET", authorization="Bearer BEARER_SECRET")
                logger.close()
            text = (Path(directory) / "audit.log").read_text(encoding="utf-8")
            self.assertEqual(1, len(text.splitlines()))
            for secret in ("DO_NOT_LOG", "ALSO_SECRET", "NESTED_SECRET", "QUERY_SECRET", "BEARER_SECRET"):
                self.assertNotIn(secret, text)
            page = await FileAuditLogReader(directory).read(AuditLogQuery())
            self.assertEqual(1, page.total)
            self.assertEqual("root\\nforged", page.items[0].username)
            self.assertEqual("LOGIN_FAILURE", page.items[0].event)


class AuditLogsUseCaseTest(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_window_and_page_bounds_never_read_files(self) -> None:
        reader = AsyncMock()
        use_case = AuditLogsUseCase(reader)
        for query in (AuditLogQuery(start_date=date(2026, 10, 13), end_date=date(2026, 10, 12)), AuditLogQuery(limit=101), AuditLogQuery(limit=50, offset=5000), AuditLogQuery(search="x" * 201)):
            with self.assertRaises(ValueError):
                await use_case.execute(query)
        reader.read.assert_not_awaited()

    async def test_valid_maximum_page_is_forwarded(self) -> None:
        reader = AsyncMock()
        query = AuditLogQuery(limit=100, offset=9900)
        await AuditLogsUseCase(reader).execute(query)
        reader.read.assert_awaited_once_with(query)

    async def test_profiles_are_read_once_and_passed_before_log_filtering(self) -> None:
        reader = AsyncMock()
        profiles = AsyncMock()
        profiles.read_profiles.return_value = {"known": AuditLogUserProfile("홍길동", "hong@example.com")}
        query = AuditLogQuery(username="홍길동")
        await AuditLogsUseCase(reader, profiles).execute(query)
        profiles.read_profiles.assert_awaited_once_with()
        reader.read.assert_awaited_once_with(query, profiles.read_profiles.return_value)

    async def test_invalid_query_never_reads_profiles(self) -> None:
        reader = AsyncMock()
        profiles = AsyncMock()
        with self.assertRaises(ValueError):
            await AuditLogsUseCase(reader, profiles).execute(AuditLogQuery(limit=0))
        profiles.read_profiles.assert_not_awaited()
        reader.read.assert_not_awaited()

    async def test_profile_failure_does_not_silently_return_unresolved_logs(self) -> None:
        reader = AsyncMock()
        profiles = AsyncMock()
        profiles.read_profiles.side_effect = AuditLogReadError("사용자 정보를 읽을 수 없습니다.")
        with self.assertRaises(AuditLogReadError):
            await AuditLogsUseCase(reader, profiles).execute(AuditLogQuery())
        reader.read.assert_not_awaited()
