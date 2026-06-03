import threading
import sqlite3
from tests.data.base import BaseDataTest
from data.bookmark_repo import BookmarkRepo
from data.folder_repo import FolderRepo
from data.history_repo import HistoryRepo


class TestIntegrationConcurrentReadWrite(BaseDataTest):
    def test_concurrent_read_write_does_not_throw(self):
        bid = BookmarkRepo.create('Concurrent', 'https://concurrent.com')
        exceptions = []

        def reader():
            try:
                for _ in range(20):
                    BookmarkRepo.get_all()
            except Exception as e:
                exceptions.append(e)

        def writer():
            try:
                for _ in range(20):
                    HistoryRepo.record(bid, opened_via='manual')
            except Exception as e:
                exceptions.append(e)

        t1 = threading.Thread(target=reader)
        t2 = threading.Thread(target=writer)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(exceptions), 0,
                         f'Concurrent access raised: {exceptions}')

    def test_ui_read_scheduler_write(self):
        bid = BookmarkRepo.create('UI Test', 'https://uitest.com')
        exceptions = []

        def ui_read():
            try:
                for _ in range(30):
                    results = BookmarkRepo.search('UI')
                    self.assertIsInstance(results, list)
            except Exception as e:
                exceptions.append(e)

        def scheduler_write():
            try:
                for _ in range(30):
                    HistoryRepo.record(bid, opened_via='schedule')
            except Exception as e:
                exceptions.append(e)

        t1 = threading.Thread(target=ui_read)
        t2 = threading.Thread(target=scheduler_write)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(exceptions), 0)


class TestIntegrationForeignKeyCascade(BaseDataTest):
    def test_delete_folder_sets_bookmark_folder_to_null(self):
        fid = FolderRepo.create('Temp Folder')
        bid = BookmarkRepo.create('Orphan', 'https://orphan.com', folder_id=fid)
        FolderRepo.delete(fid)
        result = BookmarkRepo.get_by_id(bid)
        self.assertIsNotNone(result, 'Bookmark should not be deleted')
        self.assertIsNone(result['folder_id'],
                          'folder_id should be NULL after folder delete')

    def test_delete_folder_cascades_to_subfolders(self):
        level1 = FolderRepo.create('L1')
        level2 = FolderRepo.create('L2', parent_id=level1)
        level3 = FolderRepo.create('L3', parent_id=level2)
        FolderRepo.delete(level1)
        self.assertIsNone(FolderRepo.get_by_id(level2))
        self.assertIsNone(FolderRepo.get_by_id(level3))

    def test_delete_bookmark_cascades_to_history(self):
        bid = BookmarkRepo.create('Cascade Test', 'https://cascade.com')
        HistoryRepo.record(bid)
        HistoryRepo.record(bid)
        self.assertEqual(len(HistoryRepo.get_recent(30)), 2)
        BookmarkRepo.delete(bid)
        results = HistoryRepo.get_recent(30)
        self.assertEqual(len(results), 0)

    def test_delete_bookmark_cascades_to_schedule_bookmarks(self):
        from data.schedule_repo import ScheduleRepo
        sid = ScheduleRepo.create('Cascade Sched', 9, 0, 'daily')
        bid = BookmarkRepo.create('Sched BM', 'https://schedbm.com')
        ScheduleRepo.add_bookmark(sid, bid)
        self.assertEqual(len(ScheduleRepo.get_bookmarks(sid)), 1)
        BookmarkRepo.delete(bid)
        self.assertEqual(len(ScheduleRepo.get_bookmarks(sid)), 0)

    def test_delete_bookmark_cascades_to_pool_bookmarks(self):
        from data.pool_repo import PoolRepo
        pid = PoolRepo.create('Cascade Pool')
        bid = BookmarkRepo.create('Pool BM', 'https://poolbm.com')
        PoolRepo.add_bookmark(pid, bid)
        self.assertEqual(len(PoolRepo.get_bookmarks(pid)), 1)
        BookmarkRepo.delete(bid)
        self.assertEqual(len(PoolRepo.get_bookmarks(pid)), 0)

    def test_delete_schedule_cascades_to_schedule_bookmarks(self):
        from data.schedule_repo import ScheduleRepo
        sid = ScheduleRepo.create('Del Sched', 10, 0, 'daily')
        bid = BookmarkRepo.create('Del Sched BM', 'https://delsched.com')
        ScheduleRepo.add_bookmark(sid, bid)
        ScheduleRepo.delete(sid)
        conn = self._make_connection()
        count = conn.execute(
            'SELECT COUNT(*) FROM schedule_bookmarks WHERE schedule_id = ?',
            (sid,)
        ).fetchone()[0]
        conn.close()
        self.assertEqual(count, 0)


class TestIntegrationTransactionRollback(BaseDataTest):
    def test_transaction_rollback_preserves_data(self):
        bid = BookmarkRepo.create('Before Error', 'https://before.com')
        original = BookmarkRepo.get_by_id(bid)
        try:
            conn = self._make_connection()
            conn.execute('BEGIN')
            conn.execute(
                'UPDATE bookmarks SET title = ? WHERE id = ?',
                ('After Error', bid)
            )
            conn.execute('INSERT INTO bookmarks (title, url) VALUES (?, ?)',
                         ('Bad', None))
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            conn.close()
        result = BookmarkRepo.get_by_id(bid)
        self.assertEqual(result['title'], original['title'])

    def test_sql_error_does_not_corrupt_data(self):
        bid1 = BookmarkRepo.create('Safe 1', 'https://safe1.com')
        bid2 = BookmarkRepo.create('Safe 2', 'https://safe2.com')
        try:
            conn = self._make_connection()
            conn.execute(
                'INSERT INTO bookmarks (id, title, url) VALUES (?, ?, ?)',
                (bid1, 'Duplicate PK', 'https://dup.com')
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()
        results = BookmarkRepo.get_all()
        self.assertEqual(len(results), 2)
        self.assertEqual(BookmarkRepo.get_by_id(bid1)['title'], 'Safe 1')
        self.assertEqual(BookmarkRepo.get_by_id(bid2)['title'], 'Safe 2')