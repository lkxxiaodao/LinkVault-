import time
import threading
from unittest.mock import patch
from tests.core.base import BaseCoreTest
from core.schedule_engine import ScheduleEngine
from data.schedule_repo import ScheduleRepo
from data.bookmark_repo import BookmarkRepo


class TestScheduleEngine(BaseCoreTest):
    def setUp(self):
        super().setUp()
        self._clean_singleton()

    def tearDown(self):
        self._clean_singleton()
        super().tearDown()

    @staticmethod
    def _clean_singleton():
        ScheduleEngine._instance = None

    def test_singleton_same_instance(self):
        e1 = ScheduleEngine()
        e2 = ScheduleEngine()
        self.assertIs(e1, e2)

    def test_start_stop(self):
        engine = ScheduleEngine()
        engine.start()
        self.assertTrue(engine._running)
        self.assertIsNotNone(engine._thread)
        engine.stop()
        self.assertFalse(engine._running)

    def test_add_schedule(self):
        bid = BookmarkRepo.create('Test', 'https://test.com')
        sid = ScheduleEngine.add_schedule('Morning', 9, 0, 'daily', bookmark_ids=[bid])
        self.assertGreater(sid, 0)
        sched = ScheduleRepo.get_by_id(sid)
        self.assertEqual(sched['name'], 'Morning')
        self.assertEqual(sched['hour'], 9)

    def test_add_schedule_bookmarks(self):
        b1 = BookmarkRepo.create('B1', 'https://b1.com')
        b2 = BookmarkRepo.create('B2', 'https://b2.com')
        sid = ScheduleEngine.add_schedule('Test', 10, 30, 'daily', bookmark_ids=[b1, b2])
        bookmarks = ScheduleRepo.get_bookmarks(sid)
        self.assertEqual(len(bookmarks), 2)

    def test_update_schedule(self):
        sid = ScheduleEngine.add_schedule('Old', 8, 0, 'daily')
        ScheduleEngine.update_schedule(sid, name='New', hour=10)
        sched = ScheduleRepo.get_by_id(sid)
        self.assertEqual(sched['name'], 'New')
        self.assertEqual(sched['hour'], 10)

    def test_delete_schedule(self):
        sid = ScheduleEngine.add_schedule('Delete Me', 8, 0, 'daily')
        ScheduleEngine.delete_schedule(sid)
        self.assertIsNone(ScheduleRepo.get_by_id(sid))

    def test_toggle_schedule(self):
        sid = ScheduleEngine.add_schedule('Toggle', 8, 0, 'daily')
        ScheduleEngine.toggle_schedule(sid, False)
        sched = ScheduleRepo.get_by_id(sid)
        self.assertEqual(sched['is_active'], 0)

        ScheduleEngine.toggle_schedule(sid, True)
        sched = ScheduleRepo.get_by_id(sid)
        self.assertEqual(sched['is_active'], 1)

    def test_reload_clears_and_reloads(self):
        engine = ScheduleEngine()
        engine.start()
        ScheduleEngine.add_schedule('ReloadTest', 12, 0, 'daily')
        engine.reload()
        engine.stop()

    def test_should_trigger_today_daily(self):
        engine = ScheduleEngine()
        sched = {'repeat_type': 'daily'}
        self.assertTrue(engine._should_trigger_today(sched))

    def test_should_trigger_today_once(self):
        engine = ScheduleEngine()
        sched = {'repeat_type': 'once'}
        self.assertTrue(engine._should_trigger_today(sched))

    def test_should_trigger_today_weekdays(self):
        engine = ScheduleEngine()
        sched = {'repeat_type': 'weekdays'}
        import datetime
        today = datetime.date.today()
        is_weekday = today.weekday() < 5
        self.assertEqual(engine._should_trigger_today(sched), is_weekday)

    def test_should_trigger_today_weekly(self):
        engine = ScheduleEngine()
        import datetime
        import json
        today = datetime.date.today()
        current_weekday = today.weekday()
        days = json.dumps([current_weekday])
        sched = {'repeat_type': 'weekly', 'repeat_days': days}
        self.assertTrue(engine._should_trigger_today(sched))

        other_day = (current_weekday + 1) % 7
        sched = {'repeat_type': 'weekly', 'repeat_days': json.dumps([other_day])}
        self.assertFalse(engine._should_trigger_today(sched))

    def test_should_trigger_today_custom(self):
        engine = ScheduleEngine()
        import datetime
        import json
        today = datetime.date.today()
        current_weekday = today.weekday()
        days = json.dumps([current_weekday])
        sched = {'repeat_type': 'custom', 'repeat_days': days}
        self.assertTrue(engine._should_trigger_today(sched))

    def test_trigger_inactive_schedule(self):
        bid = BookmarkRepo.create('Test', 'https://test.com')
        sid = ScheduleEngine.add_schedule('Inactive', 9, 0, 'daily', bookmark_ids=[bid])
        ScheduleEngine.toggle_schedule(sid, False)
        engine = ScheduleEngine()
        engine._trigger(sid)
        self.assertEqual(len(self._schedule_notifications), 0)

    def test_trigger_active_schedule(self):
        bid = BookmarkRepo.create('Test', 'https://test.com')
        sid = ScheduleEngine.add_schedule('Active', 9, 0, 'daily', bookmark_ids=[bid])
        engine = ScheduleEngine()
        engine._trigger(sid)
        self.assertEqual(len(self._schedule_notifications), 1)
        self.assertEqual(self._schedule_notifications[0]['schedule_name'], 'Active')
        self.assertEqual(self._schedule_notifications[0]['urls'], ['https://test.com'])

    def test_open_schedule_bookmarks(self):
        b1 = BookmarkRepo.create('B1', 'https://b1.com')
        b2 = BookmarkRepo.create('B2', 'https://b2.com')
        sid = ScheduleEngine.add_schedule('OpenTest', 10, 0, 'daily', bookmark_ids=[b1, b2])
        ScheduleEngine.open_schedule_bookmarks(sid)
        self.assertEqual(len(self._opened_urls), 2)
        self.assertIn('https://b1.com', [u['url'] for u in self._opened_urls])
        self.assertIn('https://b2.com', [u['url'] for u in self._opened_urls])

    def test_open_schedule_bookmarks_records_history(self):
        from data.history_repo import HistoryRepo
        b1 = BookmarkRepo.create('HistoryBM', 'https://historybm.com')
        sid = ScheduleEngine.add_schedule('HistorySched', 10, 0, 'daily', bookmark_ids=[b1])
        ScheduleEngine.open_schedule_bookmarks(sid)
        records = HistoryRepo.get_by_bookmark(b1)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['opened_via'], 'schedule')