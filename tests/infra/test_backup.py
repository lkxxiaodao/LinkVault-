import os
import tempfile
import unittest
from unittest.mock import patch

from tests.data.base import BaseDataTest
from infra.backup import BackupManager
from data.bookmark_repo import BookmarkRepo
from data.folder_repo import FolderRepo
from data.schedule_repo import ScheduleRepo
from data.pool_repo import PoolRepo


class TestBackupManager(BaseDataTest):
    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.mkdtemp()
        self._backup_patcher = patch(
            'infra.backup.get_connection', side_effect=self._make_connection
        )
        self._backup_patcher.start()

    def tearDown(self):
        self._backup_patcher.stop()
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        super().tearDown()

    def _seed_data(self):
        fid = FolderRepo.create('TestFolder')
        bid1 = BookmarkRepo.create('Bookmark1', 'https://example1.com', folder_id=fid)
        bid2 = BookmarkRepo.create('Bookmark2', 'https://example2.com', folder_id=fid)
        sid = ScheduleRepo.create('TestSchedule', 9, 0, 'weekdays')
        ScheduleRepo.add_bookmark(sid, bid1)
        pid = PoolRepo.create('TestPool')
        PoolRepo.add_bookmark(pid, bid2)
        return fid, bid1, bid2, sid, pid

    def test_export_linkvault_creates_file(self):
        self._seed_data()
        filepath = os.path.join(self.temp_dir, 'test_backup.linkvault')
        BackupManager.export_linkvault(filepath, 'backup_test_password')
        self.assertTrue(os.path.exists(filepath))
        self.assertGreater(os.path.getsize(filepath), 4)

    def test_export_linkvault_file_not_empty(self):
        self._seed_data()
        filepath = os.path.join(self.temp_dir, 'test_backup.linkvault')
        BackupManager.export_linkvault(filepath, 'backup_test_password')
        with open(filepath, 'rb') as f:
            content = f.read()
        self.assertGreater(len(content), 20)

    def test_import_linkvault_restores_data(self):
        self._seed_data()
        filepath = os.path.join(self.temp_dir, 'test_backup.linkvault')
        BackupManager.export_linkvault(filepath, 'backup_test_password')

        original_bookmarks = BookmarkRepo.get_all()
        original_folders = FolderRepo.get_all()
        original_schedules = ScheduleRepo.get_all()
        original_pools = PoolRepo.get_all()

        BackupManager.import_linkvault(filepath, 'backup_test_password')

        restored_bookmarks = BookmarkRepo.get_all()
        restored_folders = FolderRepo.get_all()
        restored_schedules = ScheduleRepo.get_all()
        restored_pools = PoolRepo.get_all()

        self.assertGreaterEqual(len(restored_bookmarks), len(original_bookmarks))
        self.assertGreaterEqual(len(restored_folders), len(original_folders))
        self.assertGreaterEqual(len(restored_schedules), len(original_schedules))
        self.assertGreaterEqual(len(restored_pools), len(original_pools))

    def test_export_import_roundtrip_preserves_bookmark_data(self):
        fid = FolderRepo.create('RoundtripFolder')
        bid = BookmarkRepo.create('RoundtripBookmark', 'https://roundtrip.com', folder_id=fid)

        filepath = os.path.join(self.temp_dir, 'roundtrip.linkvault')
        BackupManager.export_linkvault(filepath, 'backup_test_password')

        BookmarkRepo.delete(bid)
        FolderRepo.delete(fid)

        BackupManager.import_linkvault(filepath, 'backup_test_password')

        restored = BookmarkRepo.find_by_url('https://roundtrip.com')
        self.assertIsNotNone(restored)
        self.assertEqual(restored['title'], 'RoundtripBookmark')

    def test_export_html_creates_valid_file(self):
        self._seed_data()
        filepath = os.path.join(self.temp_dir, 'test_export.html')
        BackupManager.export_html(filepath)

        self.assertTrue(os.path.exists(filepath))
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('<!DOCTYPE NETSCAPE-Bookmark-file-1>', content)
        self.assertIn('<TITLE>LinkVault Bookmarks</TITLE>', content)

    def test_export_html_contains_bookmark_urls(self):
        fid = FolderRepo.create('HTMLFolder')
        BookmarkRepo.create('HTMLBookmark', 'https://html-test.com', folder_id=fid)

        filepath = os.path.join(self.temp_dir, 'test_html_export.html')
        BackupManager.export_html(filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('https://html-test.com', content)
        self.assertIn('HTMLBookmark', content)

    def test_import_wrong_password_raises(self):
        self._seed_data()
        filepath = os.path.join(self.temp_dir, 'test_wrong_pw.linkvault')
        BackupManager.export_linkvault(filepath, 'backup_test_password')

        with self.assertRaises(Exception):
            BackupManager.import_linkvault(filepath, 'wrong_password')

    def test_export_empty_database(self):
        filepath = os.path.join(self.temp_dir, 'empty_backup.linkvault')
        BackupManager.export_linkvault(filepath, 'backup_test_password')
        self.assertTrue(os.path.exists(filepath))

    def test_import_preserves_schedule_bookmarks(self):
        fid = FolderRepo.create('SchedFolder')
        bid = BookmarkRepo.create('SchedBookmark', 'https://sched.com', folder_id=fid)
        sid = ScheduleRepo.create('SchedTest', 10, 30, 'daily')
        ScheduleRepo.add_bookmark(sid, bid)

        filepath = os.path.join(self.temp_dir, 'sched_backup.linkvault')
        BackupManager.export_linkvault(filepath, 'backup_test_password')

        sched_bookmarks_before = ScheduleRepo.get_bookmarks(sid)
        self.assertEqual(len(sched_bookmarks_before), 1)

        BackupManager.import_linkvault(filepath, 'backup_test_password')

        sched_bookmarks_after = ScheduleRepo.get_bookmarks(sid)
        self.assertGreaterEqual(len(sched_bookmarks_after), 1)

    def test_import_preserves_pool_bookmarks(self):
        fid = FolderRepo.create('PoolFolder')
        bid = BookmarkRepo.create('PoolBookmark', 'https://pool.com', folder_id=fid)
        pid = PoolRepo.create('PoolTest')
        PoolRepo.add_bookmark(pid, bid)

        filepath = os.path.join(self.temp_dir, 'pool_backup.linkvault')
        BackupManager.export_linkvault(filepath, 'backup_test_password')

        pool_bookmarks_before = PoolRepo.get_bookmarks(pid)
        self.assertEqual(len(pool_bookmarks_before), 1)

        BackupManager.import_linkvault(filepath, 'backup_test_password')

        pool_bookmarks_after = PoolRepo.get_bookmarks(pid)
        self.assertGreaterEqual(len(pool_bookmarks_after), 1)