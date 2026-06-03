import datetime
from unittest.mock import patch
from tests.core.base import BaseCoreTest
from core.habit_analyzer import HabitAnalyzer, HabitSuggestion
from data.history_repo import HistoryRepo
from data.bookmark_repo import BookmarkRepo
from data.schedule_repo import ScheduleRepo
from infra.config import HABIT_ANALYSIS_DAYS, HABIT_CONSECUTIVE_DAYS, HABIT_TIME_SLOT_HOURS


class TestHabitAnalyzer(BaseCoreTest):
    def test_record_open(self):
        bid = BookmarkRepo.create('Test', 'https://test.com')
        HabitAnalyzer.record_open(bid, 'manual')
        records = HistoryRepo.get_by_bookmark(bid)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['opened_via'], 'manual')

    def test_record_open_default_via(self):
        bid = BookmarkRepo.create('Test', 'https://test.com')
        HabitAnalyzer.record_open(bid)
        records = HistoryRepo.get_by_bookmark(bid)
        self.assertEqual(records[0]['opened_via'], 'manual')

    def test_is_enabled_true(self):
        self.assertTrue(HabitAnalyzer.is_enabled())

    def test_is_enabled_false(self):
        conn = self._make_connection()
        conn.execute("UPDATE settings SET value = '0' WHERE key = 'habit_analysis_enabled'")
        conn.commit()
        conn.close()
        self.assertFalse(HabitAnalyzer.is_enabled())

    def test_analyze_disabled_returns_empty(self):
        conn = self._make_connection()
        conn.execute("UPDATE settings SET value = '0' WHERE key = 'habit_analysis_enabled'")
        conn.commit()
        conn.close()
        results = HabitAnalyzer.analyze()
        self.assertEqual(results, [])

    def test_analyze_no_history_returns_empty(self):
        results = HabitAnalyzer.analyze()
        self.assertEqual(results, [])

    def test_analyze_not_enough_consecutive_days(self):
        bid = BookmarkRepo.create('Test', 'https://test.com')
        today = datetime.datetime.now()
        for i in range(2):
            dt = today - datetime.timedelta(days=i)
            HistoryRepo.record(bid, 'manual')
            conn = self._make_connection()
            conn.execute(
                'UPDATE open_history SET opened_at = ? WHERE id = (SELECT MAX(id) FROM open_history)',
                (dt.strftime('%Y-%m-%d 09:30:00'),)
            )
            conn.commit()
            conn.close()
        results = HabitAnalyzer.analyze()
        self.assertEqual(results, [])

    def test_analyze_detects_habit(self):
        bid = BookmarkRepo.create('Daily Read', 'https://daily.com')
        today = datetime.datetime.now()
        for i in range(HABIT_CONSECUTIVE_DAYS):
            dt = today - datetime.timedelta(days=i)
            HistoryRepo.record(bid, 'manual')
            conn = self._make_connection()
            conn.execute(
                'UPDATE open_history SET opened_at = ? WHERE id = (SELECT MAX(id) FROM open_history)',
                (dt.strftime('%Y-%m-%d 09:30:00'),)
            )
            conn.commit()
            conn.close()
        results = HabitAnalyzer.analyze()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].bookmark['title'], 'Daily Read')
        self.assertEqual(results[0].suggestion_time, '08:00')

    def test_analyze_different_time_slots(self):
        bid = BookmarkRepo.create('Morning Read', 'https://morning.com')
        today = datetime.datetime.now()
        for i in range(HABIT_CONSECUTIVE_DAYS):
            dt = today - datetime.timedelta(days=i)
            HistoryRepo.record(bid, 'manual')
            conn = self._make_connection()
            conn.execute(
                'UPDATE open_history SET opened_at = ? WHERE id = (SELECT MAX(id) FROM open_history)',
                (dt.strftime('%Y-%m-%d 09:30:00'),)
            )
            conn.commit()
            conn.close()
            HistoryRepo.record(bid, 'manual')
            conn = self._make_connection()
            conn.execute(
                'UPDATE open_history SET opened_at = ? WHERE id = (SELECT MAX(id) FROM open_history)',
                (dt.strftime('%Y-%m-%d 15:30:00'),)
            )
            conn.commit()
            conn.close()
        results = HabitAnalyzer.analyze()
        self.assertEqual(len(results), 2)

    def test_analyze_skips_with_existing_schedule(self):
        bid = BookmarkRepo.create('Scheduled Read', 'https://scheduled.com')
        today = datetime.datetime.now()
        for i in range(HABIT_CONSECUTIVE_DAYS):
            dt = today - datetime.timedelta(days=i)
            HistoryRepo.record(bid, 'manual')
            conn = self._make_connection()
            conn.execute(
                'UPDATE open_history SET opened_at = ? WHERE id = (SELECT MAX(id) FROM open_history)',
                (dt.strftime('%Y-%m-%d 09:30:00'),)
            )
            conn.commit()
            conn.close()
        sid = ScheduleRepo.create('Existing Sched', 8, 0, 'daily')
        ScheduleRepo.add_bookmark(sid, bid, 0)
        results = HabitAnalyzer.analyze()
        self.assertEqual(results, [])

    def test_habit_suggestion_attributes(self):
        bookmark = {'id': 1, 'title': 'Test', 'url': 'https://test.com'}
        suggestion = HabitSuggestion(bookmark, (8, 10), 5, '08:00')
        self.assertEqual(suggestion.bookmark, bookmark)
        self.assertEqual(suggestion.hour_range, (8, 10))
        self.assertEqual(suggestion.consecutive_days, 5)
        self.assertEqual(suggestion.suggestion_time, '08:00')

    def test_analyze_handles_deleted_bookmark(self):
        bid = BookmarkRepo.create('Will Delete', 'https://delete.com')
        today = datetime.datetime.now()
        for i in range(HABIT_CONSECUTIVE_DAYS):
            dt = today - datetime.timedelta(days=i)
            HistoryRepo.record(bid, 'manual')
            conn = self._make_connection()
            conn.execute(
                'UPDATE open_history SET opened_at = ? WHERE id = (SELECT MAX(id) FROM open_history)',
                (dt.strftime('%Y-%m-%d 09:30:00'),)
            )
            conn.commit()
            conn.close()
        BookmarkRepo.delete(bid)
        results = HabitAnalyzer.analyze()
        self.assertEqual(results, [])