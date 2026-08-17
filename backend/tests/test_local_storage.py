# backend/tests/test_local_storage.py
import os
import pathlib
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.infrastructure.storage.local_storage import LocalStorageAdapter


class LocalStorageMoveTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = LocalStorageAdapter(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_file(self, folder: str, name: str, content: bytes) -> str:
        path = self.storage.resolve_path(folder, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as file:
            file.write(content)
        return path

    def test_moves_file_without_changing_content(self) -> None:
        source = self.write_file("", "report.pdf", b"report-content")
        self.storage.create_folder("", "archive")

        self.storage.move_entry("", "report.pdf", "archive")

        destination = self.storage.resolve_path("archive", "report.pdf")
        self.assertFalse(os.path.exists(source))
        with open(destination, "rb") as file:
            self.assertEqual(b"report-content", file.read())

    def test_moves_folder_with_nested_files(self) -> None:
        self.storage.create_folder("", "customer")
        self.storage.create_folder("", "archive")
        self.write_file("customer", "report.txt", b"nested")

        self.storage.move_entry("", "customer", "archive")

        self.assertFalse(os.path.exists(self.storage.resolve_path("", "customer")))
        with open(self.storage.resolve_path("archive/customer", "report.txt"), "rb") as file:
            self.assertEqual(b"nested", file.read())

    def test_rejects_existing_destination_without_overwrite(self) -> None:
        source = self.write_file("", "report.txt", b"source")
        self.storage.create_folder("", "archive")
        destination = self.write_file("archive", "report.txt", b"destination")

        with self.assertRaises(FileExistsError):
            self.storage.move_entry("", "report.txt", "archive")

        self.assertTrue(os.path.exists(source))
        with open(destination, "rb") as file:
            self.assertEqual(b"destination", file.read())

    def test_rejects_folder_move_into_own_descendant(self) -> None:
        self.storage.create_folder("", "customer")
        self.storage.create_folder("customer", "reports")

        with self.assertRaises(ValueError):
            self.storage.move_entry("", "customer", "customer/reports")

        self.assertTrue(os.path.isdir(self.storage.resolve_path("", "customer")))

    def test_rejects_same_location_and_unsafe_names(self) -> None:
        self.write_file("", "report.txt", b"source")

        with self.assertRaises(ValueError):
            self.storage.move_entry("", "report.txt", "")
        with self.assertRaises(ValueError):
            self.storage.move_entry("", "..", "")

    def test_rejects_missing_source_or_destination(self) -> None:
        self.write_file("", "report.txt", b"source")

        with self.assertRaises(FileNotFoundError):
            self.storage.move_entry("", "missing.txt", "")
        with self.assertRaises(FileNotFoundError):
            self.storage.move_entry("", "report.txt", "missing-folder")

    def test_creates_archive_for_selected_file_and_folder(self) -> None:
        self.write_file("", "summary.txt", b"summary")
        self.storage.create_folder("", "reports")
        self.write_file("reports", "daily.txt", b"daily")

        archive_path = self.storage.create_archive("", ["summary.txt", "reports"])

        with zipfile.ZipFile(archive_path) as archive:
            self.assertEqual(
                {"reports/", "reports/daily.txt", "summary.txt"},
                set(archive.namelist()),
            )
            self.assertEqual(b"summary", archive.read("summary.txt"))
            self.assertEqual(b"daily", archive.read("reports/daily.txt"))
        self.storage.delete_archive(archive_path)
        self.assertFalse(os.path.exists(archive_path))

    def test_deletes_selected_files_and_folders(self) -> None:
        self.write_file("", "summary.txt", b"summary")
        self.storage.create_folder("", "reports")
        self.write_file("reports", "daily.txt", b"daily")

        self.storage.delete_entries("", ["summary.txt", "reports"])

        self.assertFalse(os.path.exists(self.storage.resolve_path("", "summary.txt")))
        self.assertFalse(os.path.exists(self.storage.resolve_path("", "reports")))

    def test_bulk_delete_validates_every_entry_before_deleting(self) -> None:
        source = self.write_file("", "summary.txt", b"summary")

        with self.assertRaises(FileNotFoundError):
            self.storage.delete_entries("", ["summary.txt", "missing.txt"])

        self.assertTrue(os.path.exists(source))
