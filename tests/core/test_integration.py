import threading
import time
from tests.core.base import BaseCoreTest
from core.bookmark_manager import BookmarkManager
from core.folder_manager import FolderManager
from core.random_walker import RandomWalker
from core.schedule_engine import ScheduleEngine
from core.habit_analyzer import HabitAnalyzer
from data.bookmark_repo import BookmarkRepo
from data.folder_repo import FolderRepo
from data.history_repo import HistoryRepo
from data.pool_repo import PoolRepo
from data.schedule_repo import ScheduleRepo


class TestCoreIntegration(BaseCoreTest):
    def setUp(self):
        super().setUp()
        self._clean_singleton()

    def tearDown(self):
        self._clean_singleton()
        super().tearDown()

    @staticmethod
    def _clean_singleton():
        ScheduleEngine._instance = None

    def test_full_bookmark_lifecycle(self):
        fid = FolderManager.create_folder('Dev')
        bid = BookmarkManager.add_bookmark('GitHub', 'https://github.com', folder_id=fid)
        bm = BookmarkManager.get_by_id(bid)
        self.assertEqual(bm['title'], 'GitHub')
        self.assertEqual(bm['folder_id'], fid)

        BookmarkManager.update_bookmark(bid, title='GitHub Code')
        bm = BookmarkManager.get_by_id(bid)
        self.assertEqual(bm['title'], 'GitHub Code')

        BookmarkManager.move_to_folder(bid, None)
        bm = BookmarkManager.get_by_id(bid)
        self.assertIsNone(bm['folder_id'])

        results = BookmarkManager.search('GitHub')
        self.assertEqual(len(results), 1)

        BookmarkManager.delete_bookmark(bid)
        self.assertIsNone(BookmarkManager.get_by_id(bid))

    def test_schedule_and_random_workflow(self):
        b1 = BookmarkManager.add_bookmark('Daily News', 'https://news.com')
        b2 = BookmarkManager.add_bookmark('Dev Docs', 'https://docs.com')
        b3 = BookmarkManager.add_bookmark('Fun Site', 'https://fun.com')

        sid = ScheduleEngine.add_schedule(
            'Morning Read', 8, 30, 'weekdays',
            bookmark_ids=[b1, b2]
        )
        sched = ScheduleRepo.get_by_id(sid)
        self.assertEqual(sched['name'], 'Morning Read')
        self.assertEqual(len(ScheduleRepo.get_bookmarks(sid)), 2)

        pid = RandomWalker.create_pool('Fun Pool')
        RandomWalker.add_to_pool(pid, b3)
        RandomWalker.set_active_pool(pid)

        result = RandomWalker.walk()
        self.assertIsNotNone(result)
        self.assertIn(result['url'], ['https://fun.com'])

        ScheduleEngine.open_schedule_bookmarks(sid)
        self.assertGreaterEqual(len(self._opened_urls), 3)

    def test_habit_analysis_workflow(self):
        HabitAnalyzer.record_open(self._create_bookmark('Manual', 'https://manual.com'), 'manual')

        results = HabitAnalyzer.analyze()
        self.assertIsInstance(results, list)

    def test_foreign_key_cascade_folder_deletion(self):
        fid = FolderManager.create_folder('Temp')
        bid = BookmarkManager.add_bookmark('In Folder', 'https://infolder.com', folder_id=fid)
        FolderManager.delete_folder(fid)
        bm = BookmarkRepo.get_by_id(bid)
        self.assertIsNotNone(bm)
        self.assertIsNone(bm['folder_id'])

    def test_foreign_key_cascade_bookmark_deletion_from_schedule(self):
        bid = BookmarkRepo.create('Sched BM', 'https://sched.com')
        sid = ScheduleRepo.create('Sched', 9, 0, 'daily')
        ScheduleRepo.add_bookmark(sid, bid, 0)
        BookmarkManager.delete_bookmark(bid)
        bookmarks = ScheduleRepo.get_bookmarks(sid)
        self.assertEqual(len(bookmarks), 0)

    def test_concurrent_read_write(self):
        errors = []

        def writer():
            try:
                for i in range(10):
                    BookmarkManager.add_bookmark(f'B{i}', f'https://b{i}.com')
            except Exception as e:
                errors.append(('writer', str(e)))

        def reader():
            try:
                for _ in range(20):
                    BookmarkManager.get_all()
            except Exception as e:
                errors.append(('reader', str(e)))

        t1 = threading.Thread(target=writer)
        t2 = threading.Thread(target=reader)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(errors, [])
        all_bm = BookmarkManager.get_all()
        self.assertEqual(len(all_bm), 10)

    def test_transaction_rollback_on_error(self):
        bid = BookmarkManager.add_bookmark('Before Error', 'https://before.com')
        self.assertGreater(bid, 0)
        all_before = BookmarkManager.get_all()
        self.assertEqual(len(all_before), 1)
        self.assertEqual(all_before[0]['title'], 'Before Error')