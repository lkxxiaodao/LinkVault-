import os
import tempfile
import unittest
from unittest.mock import patch

from tests.data.base import BaseDataTest
from data.bookmark_repo import BookmarkRepo
from data.folder_repo import FolderRepo
from data.schedule_repo import ScheduleRepo
from data.pool_repo import PoolRepo
from data.history_repo import HistoryRepo
from infra.encryption import decrypt_data


class TestM2M1Integration(BaseDataTest):
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

    def _seed_complete_data(self):
        fid1 = FolderRepo.create('DevTools')
        fid2 = FolderRepo.create('News', parent_id=fid1)
        FolderRepo.create('Music')

        bid1 = BookmarkRepo.create('GitHub', 'https://github.com', folder_id=fid1)
        bid2 = BookmarkRepo.create('HackerNews', 'https://news.ycombinator.com', folder_id=fid2)
        bid3 = BookmarkRepo.create('Spotify', 'https://spotify.com', folder_id=None)

        sid = ScheduleRepo.create('MorningRead', 9, 0, 'weekdays')
        ScheduleRepo.add_bookmark(sid, bid2)
        ScheduleRepo.add_bookmark(sid, bid1)

        pid = PoolRepo.create('Inspiration')
        PoolRepo.add_bookmark(pid, bid1)
        PoolRepo.add_bookmark(pid, bid3)
        PoolRepo.set_active(pid)

        HistoryRepo.record(bid1, 'manual')
        HistoryRepo.record(bid2, 'schedule')
        HistoryRepo.record(bid3, 'random')

        return fid1, fid2, bid1, bid2, bid3, sid, pid

    def test_full_backup_roundtrip_all_data_types(self):
        self._seed_complete_data()

        folders_before = FolderRepo.get_all()
        bookmarks_before = BookmarkRepo.get_all()
        schedules_before = ScheduleRepo.get_all()
        pools_before = PoolRepo.get_all()

        from infra.backup import BackupManager
        filepath = os.path.join(self.temp_dir, 'full_backup.linkvault')
        BackupManager.export_linkvault(filepath, 'integration_test_pw')
        self.assertTrue(os.path.exists(filepath))

        with open(filepath, 'rb') as f:
            raw = f.read()
        data = decrypt_data(raw, 'integration_test_pw')

        self.assertIn('folders', data)
        self.assertIn('bookmarks', data)
        self.assertIn('schedules', data)
        self.assertIn('schedule_bookmarks', data)
        self.assertIn('random_pools', data)
        self.assertIn('pool_bookmarks', data)
        self.assertIn('settings', data)

        self.assertEqual(len(data['folders']), len(folders_before))
        self.assertEqual(len(data['bookmarks']), len(bookmarks_before))
        self.assertEqual(len(data['schedules']), len(schedules_before))
        self.assertEqual(len(data['random_pools']), len(pools_before))

    def test_backup_encryption_is_aes_gcm(self):
        self._seed_complete_data()
        from infra.backup import BackupManager
        filepath = os.path.join(self.temp_dir, 'enc_check.linkvault')
        BackupManager.export_linkvault(filepath, 'test_pw')

        with open(filepath, 'rb') as f:
            raw = f.read()

        self.assertTrue(raw.startswith(b'LVLT'))
        self.assertGreater(len(raw), 28)

    def test_history_not_in_backup(self):
        fid = FolderRepo.create('HistFolder')
        bid = BookmarkRepo.create('HistBookmark', 'https://history.com', folder_id=fid)
        HistoryRepo.record(bid, 'manual')

        from infra.backup import BackupManager
        filepath = os.path.join(self.temp_dir, 'hist_backup.linkvault')
        BackupManager.export_linkvault(filepath, 'test_pw')

        with open(filepath, 'rb') as f:
            raw = f.read()
        data = decrypt_data(raw, 'test_pw')

        self.assertNotIn('open_history', data)

    def test_html_export_nested_folders(self):
        fid1 = FolderRepo.create('Parent')
        fid2 = FolderRepo.create('Child', parent_id=fid1)
        BookmarkRepo.create('ParentBM', 'https://parent.com', folder_id=fid1)
        BookmarkRepo.create('ChildBM', 'https://child.com', folder_id=fid2)

        from infra.backup import BackupManager
        filepath = os.path.join(self.temp_dir, 'nested_export.html')
        BackupManager.export_html(filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('Parent', content)
        self.assertIn('Child', content)
        self.assertIn('https://parent.com', content)
        self.assertIn('https://child.com', content)
        self.assertIn('<DL><p>', content)

    def test_browser_launcher_with_bookmark(self):
        from infra.browser_launcher import BrowserLauncher

        folder_id = FolderRepo.create('BrowserTest')
        bookmark_id = BookmarkRepo.create('BrowserBM', 'https://browser-test.com', folder_id=folder_id)

        bookmark = BookmarkRepo.get_by_id(bookmark_id)
        self.assertIsNotNone(bookmark)

        with patch('infra.browser_launcher.webbrowser.open') as mock_open:
            BrowserLauncher.open_url(bookmark['url'])
            mock_open.assert_called_once_with('https://browser-test.com')

    def test_config_paths_usable_with_data_layer(self):
        from infra.config import DB_PATH, DATA_DIR, FAVICON_DIR

        self.assertTrue(DB_PATH.endswith('.db'))
        self.assertTrue(FAVICON_DIR.endswith('favicons'))
        self.assertIn('LinkVault', DATA_DIR)

    def test_schedule_repo_bookmark_relation(self):
        fid = FolderRepo.create('SchedFolder')
        bid1 = BookmarkRepo.create('SchedBM1', 'https://sched1.com', folder_id=fid)
        bid2 = BookmarkRepo.create('SchedBM2', 'https://sched2.com', folder_id=fid)
        sid = ScheduleRepo.create('RelTest', 14, 30, 'daily')

        ScheduleRepo.add_bookmark(sid, bid1, sort_order=0)
        ScheduleRepo.add_bookmark(sid, bid2, sort_order=1)

        bookmarks = ScheduleRepo.get_bookmarks(sid)
        self.assertEqual(len(bookmarks), 2)

        ScheduleRepo.remove_bookmark(sid, bid1)
        bookmarks = ScheduleRepo.get_bookmarks(sid)
        self.assertEqual(len(bookmarks), 1)

    def test_pool_active_switching(self):
        pid1 = PoolRepo.create('PoolA')
        pid2 = PoolRepo.create('PoolB')

        PoolRepo.set_active(pid1)
        active = PoolRepo.get_active()
        self.assertIsNotNone(active)
        self.assertEqual(active['id'], pid1)

        PoolRepo.set_active(pid2)
        active = PoolRepo.get_active()
        self.assertIsNotNone(active)
        self.assertEqual(active['id'], pid2)

        PoolRepo.set_active(None)
        active = PoolRepo.get_active()
        self.assertIsNone(active)